"""
prop_tracking.py — pitcher-strikeout + batter-walk projections (TRACKING ONLY)

Phase 1 of the player-prop expansion. This module **does not fire bets**.
It only projects per-game prop totals from the data we already collect and
emits them so we can verify daily that:

  1. Pitcher K data is fresh (recent starts populated, K count plausible)
  2. Batter walk data is fresh (BB% from season, sample size adequate)
  3. The projections are stable day-over-day for the same pitcher/batter

Once we've watched these projections track cleanly for a few days, Phase 2
adds Odds API prop fetches + card factories with strict edge/confidence
filters.

Outputs (per game):
  tracked_props = {
    "pitchers": [
      {"name": ..., "id": ..., "side": "home"|"away",
       "starts_in_window": N, "k_per_start": x.x, "k_per_bf": x.xxx,
       "projected_k": x.x, "data_quality": "ok|stale|missing",
       "notes": [...]},
      ...
    ],
    "batters": [
      {"name": ..., "id": ..., "side": "home"|"away", "order": 1..n,
       "bb_pct": x.xx, "pa_sample": N, "projected_walks": x.xx,
       "data_quality": "ok|small_sample|missing"},
      ...
    ],
  }
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Tunables — calibrate from historical when we add the betting layer
# ---------------------------------------------------------------------------

# Typical starter goes ~5.5 innings, ~22 batters faced. We project K count as
# rate_per_BF * expected_BF, with a small park/umpire adjustment.
DEFAULT_BF_PER_START = 22

# --- Empirical-Bayes calibration -------------------------------------------
# Forward paper-trading (prop_paper_log.csv) showed the old projection was
# both noisy (RMSE ≈ raw Poisson SD, i.e. ~no skill over the mean) and biased:
# it UNDER-projected strikeouts by ~0.36/start, worst when it projected LOW
# counts (actual/proj ≈ 1.24 in the 0-4 bucket) — a textbook regression-to-the-
# mean failure that fed losing UNDER bets. Two fixes below:
#
#   1. Shrink the pitcher's per-BF rate toward the league mean, weighted by his
#      batters-faced sample. A 30-day sample (~90 BF) is small, so a raw rate
#      overfits; pulling it toward league removes the low-end bias.
#   2. Project EXPECTED batters faced from the pitcher's own recent workload
#      (regressed toward the league starter), not a flat 22 — the biggest
#      single driver of a per-start prop total.
#
# League K-per-BF baseline. 0.23 matches the observed K/start (~5.08 over ~22
# BF) in our own settled paper sample, so shrinking toward it keeps the slate
# projection mean ~unbiased while pulling individual low-sample rates in.
LEAGUE_K_PER_BF  = 0.23
# NOTE: we deliberately do NOT shrink the WALK rate. The true league BB/PA
# (~8%) sits ABOVE the walk rates actually realised by the starters that get
# prop markets, so shrinking toward it INFLATED walk projections the wrong way
# (offline mean 1.51 -> 1.83 vs ~1.26 actual). Walks keep their own rate until
# a population-appropriate anchor can be validated forward.
LEAGUE_BB_PER_BF = None
# Prior strength in batters-faced. ~100 BF (≈ a 30-day month of starts) is
# pulled ~halfway toward league: enough to kill the low-end over-fit that fed
# losing UNDER bets, while leaving genuine high-K arms mostly intact. Validated
# offline against a saved slate to keep the projection mean ~unbiased (≈ league
# 5.1 K/start) while lifting the previously-too-low projections.
RATE_PRIOR_BF = 100.0
# Expected-BF: a GENTLE regression of the pitcher's own recent workload toward
# the league starter. The 30-day BF/start is noisy (short outings drag it down)
# so we keep a strong prior and a tight band — true workhorses register a small
# bump, but it can never crater a projection. Workload scaling stays modest on
# purpose; a richer model is deferred until it can be validated forward.
LEAGUE_BF_PER_START = 22.0
BF_PRIOR_STARTS     = 10.0
BF_PER_START_BOUNDS = (20.0, 25.0)

# Per-batter PA per game ~ 4.0 for top-of-order, ~3.5 for middle, ~3.0 for bottom
TYPICAL_PA_BY_ORDER = {1: 4.4, 2: 4.3, 3: 4.2, 4: 4.0, 5: 3.9, 6: 3.7,
                       7: 3.5, 8: 3.3, 9: 3.1}

# Minimum sample sizes for "ok" data quality
MIN_PITCHER_STARTS = 3
MIN_BATTER_PA = 60


def _shrink_rate(total: float | None, bf_total: float | None,
                 league_rate: float) -> float | None:
    """Empirical-Bayes per-BF rate: pull the observed rate toward the league
    mean with weight RATE_PRIOR_BF (expressed in batters faced)."""
    if not bf_total:
        return None
    return (total + league_rate * RATE_PRIOR_BF) / (bf_total + RATE_PRIOR_BF)


def _expected_bf(profile: dict) -> float:
    """Expected batters faced next start: the pitcher's own BF/start regressed
    toward the league starter workload, clamped to a sane range."""
    bf_total = profile.get("bf_total_window")
    n = profile.get("k_starts_window") or 0
    if not bf_total or not n:
        return LEAGUE_BF_PER_START
    exp = (bf_total + LEAGUE_BF_PER_START * BF_PRIOR_STARTS) / (n + BF_PRIOR_STARTS)
    lo, hi = BF_PER_START_BOUNDS
    return round(max(lo, min(hi, exp)), 2)


def _data_quality_pitcher(starts: int, k_per_bf: float | None) -> str:
    if k_per_bf is None or starts == 0: return "missing"
    if starts < MIN_PITCHER_STARTS: return "stale"
    return "ok"


def _data_quality_batter(pa: int, bb_pct: float | None) -> str:
    if bb_pct is None: return "missing"
    if pa < MIN_BATTER_PA: return "small_sample"
    return "ok"


def project_pitcher_ks(pitcher_profile: dict, opposing_lineup_k_pct: float | None,
                       ump_run_delta: float = 0.0) -> dict:
    """Project K count for a pitcher in their next start.

    Method:
      base = K_per_BF * expected_BF
      adjust toward opposing lineup's K susceptibility (avg_k_pct from top of order)
      tiny umpire bump (high-K ump = +0.3 K, low-K ump = -0.3 K)
    """
    if not pitcher_profile or not pitcher_profile.get("available"):
        return {"available": False, "data_quality": "missing"}
    raw_k_per_bf = pitcher_profile.get("k_per_bf")
    starts = pitcher_profile.get("k_starts_window", 0)
    if raw_k_per_bf is None:
        return {"available": False, "data_quality": "missing"}

    # Empirical-Bayes rate: shrink toward league mean by BF sample (falls back
    # to the raw rate only if batter-faced totals are unavailable).
    k_rate = _shrink_rate(pitcher_profile.get("k_total_window"),
                          pitcher_profile.get("bf_total_window"),
                          LEAGUE_K_PER_BF)
    if k_rate is None:
        k_rate = raw_k_per_bf
    expected_bf = _expected_bf(pitcher_profile)

    # Tilt toward opposing K%: if their top batters strike out 25% vs league
    # average 22%, that's a +14% relative bump to pitcher's K projection.
    league_avg_k_pct = 0.22
    adjustment = 1.0
    if opposing_lineup_k_pct is not None and opposing_lineup_k_pct > 0:
        adjustment = (opposing_lineup_k_pct / league_avg_k_pct)
        adjustment = max(0.85, min(1.15, adjustment))   # cap at ±15%

    # Umpire: K-friendly ump (negative run_delta) → more Ks; cap effect small.
    ump_k_bump = -ump_run_delta * 0.4   # ~0.4 K per run-delta unit

    proj = k_rate * adjustment * expected_bf + ump_k_bump
    return {
        "available": True,
        "data_quality": _data_quality_pitcher(starts, raw_k_per_bf),
        "starts_in_window": starts,
        "k_per_start_avg":  pitcher_profile.get("k_per_start"),
        "k_per_bf":         raw_k_per_bf,
        "k_per_bf_shrunk":  round(k_rate, 3),
        "expected_bf":      expected_bf,
        "opp_lineup_k_pct": opposing_lineup_k_pct,
        "lineup_adjustment": round(adjustment, 3),
        "ump_k_bump":       round(ump_k_bump, 2),
        "projected_k":      round(proj, 2),
    }


def project_pitcher_walks(pitcher_profile: dict,
                          opposing_lineup_bb_pct: float | None,
                          ump_run_delta: float = 0.0) -> dict:
    """Project walks ALLOWED by a pitcher in their next start.

    Method:
      base = BB_per_BF * expected_BF
      tilt toward opposing lineup's BB rate (patient lineups draw more walks)
      tiny umpire bump (tight zone = more walks, slightly negative for K-friendly umps)
    """
    if not pitcher_profile or not pitcher_profile.get("available"):
        return {"available": False, "data_quality": "missing"}
    raw_bb_per_bf = pitcher_profile.get("bb_per_bf")
    starts = pitcher_profile.get("k_starts_window", 0)
    if raw_bb_per_bf is None:
        return {"available": False, "data_quality": "missing"}

    # Walks keep their own observed rate (see LEAGUE_BB_PER_BF note): shrinking
    # toward the league BB rate inflated projections for the low-walk starters
    # that get prop markets. NegBin in the grader still de-biases the tails.
    bb_rate = raw_bb_per_bf
    if LEAGUE_BB_PER_BF is not None:
        shrunk = _shrink_rate(pitcher_profile.get("bb_total_window"),
                              pitcher_profile.get("bf_total_window"),
                              LEAGUE_BB_PER_BF)
        if shrunk is not None:
            bb_rate = shrunk
    expected_bf = _expected_bf(pitcher_profile)

    # Opposing lineup BB%: if top of order walks at 11% vs league 8.5%,
    # bump walks projection by ~30%.
    league_avg_bb_pct = 0.085
    adjustment = 1.0
    if opposing_lineup_bb_pct is not None and opposing_lineup_bb_pct > 0:
        adjustment = (opposing_lineup_bb_pct / league_avg_bb_pct)
        adjustment = max(0.80, min(1.25, adjustment))   # cap at ±25%

    # Umpire: contact-friendly ump (positive run_delta) tends to call a
    # tighter zone in some cases. Effect on walks is real but small.
    ump_bb_bump = ump_run_delta * 0.15   # ~0.15 BB per run-delta unit

    proj = bb_rate * adjustment * expected_bf + ump_bb_bump
    return {
        "available": True,
        "data_quality": _data_quality_pitcher(starts, raw_bb_per_bf),
        "starts_in_window":  starts,
        "bb_per_start_avg":  pitcher_profile.get("bb_per_start"),
        "bb_per_bf":         raw_bb_per_bf,
        "bb_per_bf_shrunk":  round(bb_rate, 3),
        "expected_bf":       expected_bf,
        "opp_lineup_bb_pct": opposing_lineup_bb_pct,
        "lineup_adjustment": round(adjustment, 3),
        "ump_bb_bump":       round(ump_bb_bump, 2),
        "projected_walks":   round(proj, 2),
    }


def project_batter_walks(batter: dict, pitcher_bb_rate: float | None,
                         order: int = 1) -> dict:
    """Project walk count for one batter in one game.

    Method: expected_walks = BB_pct * expected_PA, with mild adjustment toward
    pitcher's walk-rate tendency.
    """
    bb_pct = batter.get("bb_pct")
    pa = batter.get("pa", 0)
    if bb_pct is None:
        return {"available": False, "data_quality": "missing"}
    expected_pa = TYPICAL_PA_BY_ORDER.get(order, 3.8)

    # Pitcher walk-rate tilt: league avg ~8%. Tilt batter projection toward
    # pitcher's tendency if known.
    league_pitcher_bb = 0.085
    adj = 1.0
    if pitcher_bb_rate is not None and pitcher_bb_rate > 0:
        adj = (pitcher_bb_rate / league_pitcher_bb)
        adj = max(0.75, min(1.25, adj))

    proj = bb_pct * expected_pa * adj
    return {
        "available": True,
        "data_quality": _data_quality_batter(pa, bb_pct),
        "id":          batter.get("id"),
        "name":        batter.get("name"),
        "bb_pct":      bb_pct,
        "pa_sample":   pa,
        "expected_pa": expected_pa,
        "pitcher_bb_adj": round(adj, 3),
        "projected_walks": round(proj, 3),
    }


def build_tracked_props(game: dict, ump_run_delta: float = 0.0) -> dict:
    """Build the full tracked-props block for one game.

    Markets tracked (Phase 1, no bets fired):
      * Pitcher strikeouts (over/under K count, per starter)
      * Pitcher walks (over/under BB allowed, per starter)
      * Batter walks (over/under per batter, top 5 per side)
    """
    out = {"pitcher_ks": [], "pitcher_walks": [], "batter_walks": []}

    # Catcher framing adjustment — applies to the pitcher's OWN catcher.
    # Elite framer steals ~0.5-0.8 K per game; poor framer costs the same.
    cf = game.get("catcher_framing") or {}
    framing_k_bump = {"home": 0.0, "away": 0.0}
    if cf.get("available"):
        for s in ("home", "away"):
            runs = (cf.get(s) or {}).get("season_runs", 0.0) or 0.0
            # Empirical: +10 framing runs ≈ +0.6 K per start
            framing_k_bump[s] = runs * 0.06

    for side in ("home", "away"):
        opp = "away" if side == "home" else "home"
        prof = game.get(side, {}).get("pitcher_profile") or {}
        opp_too = game.get(opp, {}).get("top_of_order") or {}
        opp_k = opp_too.get("avg_k_pct")
        opp_bb = opp_too.get("avg_bb_pct")

        k_proj = project_pitcher_ks(prof, opp_k, ump_run_delta=ump_run_delta)
        if k_proj.get("available"):
            k_proj["side"] = side
            k_proj["name"] = game.get(side, {}).get("probable_pitcher_name")
            k_proj["id"]   = game.get(side, {}).get("probable_pitcher_id")
            # Apply catcher-framing bump to projected K count
            bump = framing_k_bump.get(side, 0.0)
            if abs(bump) >= 0.1 and k_proj.get("projected_k") is not None:
                k_proj["projected_k"] = round(k_proj["projected_k"] + bump, 2)
                k_proj["catcher_framing_bump"] = round(bump, 2)
            out["pitcher_ks"].append(k_proj)

        bb_proj = project_pitcher_walks(prof, opp_bb, ump_run_delta=ump_run_delta)
        if bb_proj.get("available"):
            bb_proj["side"] = side
            bb_proj["name"] = game.get(side, {}).get("probable_pitcher_name")
            bb_proj["id"]   = game.get(side, {}).get("probable_pitcher_id")
            out["pitcher_walks"].append(bb_proj)

    # Batter walks — project top 5 batters per side, using opposing pitcher's
    # actual BB-rate when available (instead of league average fallback).
    for side in ("home", "away"):
        opp = "away" if side == "home" else "home"
        too = game.get(side, {}).get("top_of_order") or {}
        opp_prof = game.get(opp, {}).get("pitcher_profile") or {}
        pitcher_bb_rate = opp_prof.get("bb_per_bf") if opp_prof.get("available") else None
        for order, b in enumerate(too.get("batters", []), start=1):
            proj = project_batter_walks(b, pitcher_bb_rate, order=order)
            if proj.get("available"):
                proj["side"] = side
                proj["order"] = order
                out["batter_walks"].append(proj)

    # Summary counts so the daily report can flag data quality at a glance.
    def _q(lst, q):
        return sum(1 for x in lst if x["data_quality"] == q)
    out["summary"] = {
        "n_pitcher_ks":           len(out["pitcher_ks"]),
        "n_pitcher_walks":        len(out["pitcher_walks"]),
        "n_batter_walks":         len(out["batter_walks"]),
        "n_pitcher_ks_ok":        _q(out["pitcher_ks"], "ok"),
        "n_pitcher_walks_ok":     _q(out["pitcher_walks"], "ok"),
        "n_batter_walks_ok":      _q(out["batter_walks"], "ok"),
        "n_pitcher_ks_stale":     _q(out["pitcher_ks"], "stale"),
        "n_pitcher_walks_stale":  _q(out["pitcher_walks"], "stale"),
        "n_batter_walks_small":   _q(out["batter_walks"], "small_sample"),
        "n_pitcher_ks_missing":   _q(out["pitcher_ks"], "missing"),
        "n_pitcher_walks_missing": _q(out["pitcher_walks"], "missing"),
        "n_batter_walks_missing": _q(out["batter_walks"], "missing"),
    }
    return out


def render_markdown(grades: list[dict], date_iso: str) -> str:
    """Render a daily tracking report. PAPER ONLY — no bets fired."""
    lines: list[str] = []
    lines.append(f"# Prop Tracking — {date_iso}\n")
    lines.append("_Paper / data-quality tracking only. No bets fired from these markets yet._\n")
    lines.append("_Goal: verify pitcher K/BB rates and batter walk rates are populating "
                 "cleanly day-over-day before we add the betting layer._\n")

    # Slate totals
    tot = {"pk": 0, "pw": 0, "bw": 0, "pk_ok": 0, "pw_ok": 0, "bw_ok": 0}
    for g in grades:
        s = (g.get("tracked_props") or {}).get("summary") or {}
        tot["pk"]    += s.get("n_pitcher_ks", 0)
        tot["pw"]    += s.get("n_pitcher_walks", 0)
        tot["bw"]    += s.get("n_batter_walks", 0)
        tot["pk_ok"] += s.get("n_pitcher_ks_ok", 0)
        tot["pw_ok"] += s.get("n_pitcher_walks_ok", 0)
        tot["bw_ok"] += s.get("n_batter_walks_ok", 0)
    lines.append(
        f"**Slate-wide data quality:** "
        f"pitcher Ks {tot['pk_ok']}/{tot['pk']} OK · "
        f"pitcher walks {tot['pw_ok']}/{tot['pw']} OK · "
        f"batter walks {tot['bw_ok']}/{tot['bw']} OK\n"
    )

    for g in grades:
        tp = g.get("tracked_props") or {}
        if not (tp.get("pitcher_ks") or tp.get("pitcher_walks") or tp.get("batter_walks")):
            continue
        lines.append(f"\n### {g['matchup']}")

        if tp.get("pitcher_ks"):
            lines.append("\n**Pitcher K projections**")
            lines.append("| Side | Pitcher | Starts | K/start | K/BF | Opp K% | Proj K | Quality |")
            lines.append("|---|---|---:|---:|---:|---:|---:|---|")
            for p in tp["pitcher_ks"]:
                opp_k = f"{(p.get('opp_lineup_k_pct') or 0)*100:.1f}%" if p.get("opp_lineup_k_pct") else "—"
                lines.append(
                    f"| {p.get('side','?').upper()} | {p.get('name','?')} | "
                    f"{p.get('starts_in_window',0)} | "
                    f"{p.get('k_per_start_avg','—')} | {p.get('k_per_bf','—')} | "
                    f"{opp_k} | **{p.get('projected_k','—')}** | {p.get('data_quality','?')} |"
                )

        if tp.get("pitcher_walks"):
            lines.append("\n**Pitcher walks projections**")
            lines.append("| Side | Pitcher | Starts | BB/start | BB/BF | Opp BB% | Proj BB | Quality |")
            lines.append("|---|---|---:|---:|---:|---:|---:|---|")
            for p in tp["pitcher_walks"]:
                opp_bb = f"{(p.get('opp_lineup_bb_pct') or 0)*100:.1f}%" if p.get("opp_lineup_bb_pct") else "—"
                lines.append(
                    f"| {p.get('side','?').upper()} | {p.get('name','?')} | "
                    f"{p.get('starts_in_window',0)} | "
                    f"{p.get('bb_per_start_avg','—')} | {p.get('bb_per_bf','—')} | "
                    f"{opp_bb} | **{p.get('projected_walks','—')}** | {p.get('data_quality','?')} |"
                )

        if tp.get("batter_walks"):
            lines.append("\n**Top batter walk projections**")
            lines.append("| Side | Order | Batter | BB% | PA | Proj BB | Quality |")
            lines.append("|---|---:|---|---:|---:|---:|---|")
            for b in tp["batter_walks"][:10]:
                lines.append(
                    f"| {b.get('side','?').upper()} | {b.get('order','?')} | "
                    f"{b.get('name','?')} | "
                    f"{b.get('bb_pct',0)*100:.1f}% | {b.get('pa_sample',0)} | "
                    f"**{b.get('projected_walks','—')}** | {b.get('data_quality','?')} |"
                )
    return "\n".join(lines)
