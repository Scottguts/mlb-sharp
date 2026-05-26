"""
paper_props.py — Phase 2 paper trading for player-prop markets

Loads model projections from `tracked_props` (built by prop_tracking.py) and
combines them with market lines from prop_odds.json. For each (player, market,
line) the model computes its own fair probability via Poisson, derives an
edge against the best book price, and writes "would-have-bet" rows to a
separate paper log so we don't pollute the real bet_log.csv.

A second daily pass settles paper bets by pulling actual K / BB counts from
MLB Stats API box scores. A daily P/L report shows ROI by market so we can
compare prop edges to the existing ML / total ROI.

NOTHING in this file fires a real bet. Discord output is clearly labeled
"PAPER TRADING."
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from mlb_data_scraper import (
    TARGET_BOOKS, SHARP_ANCHORS, american_to_prob, devig_two_way, edge_pct,
)


# ---------------------------------------------------------------------------
# Paper-log schema
# ---------------------------------------------------------------------------

PAPER_LOG_FILENAME = "prop_paper_log.csv"

PAPER_FIELDS = [
    "bet_id", "recommended_at", "date", "gamePk", "event_id", "matchup",
    "first_pitch",
    "market",                # pitcher_strikeouts | pitcher_walks | batter_walks
    "player_name", "player_id",
    "side",                  # over | under
    "line",
    "book", "price",
    "model_projection",      # our raw mean estimate (Ks or BB)
    "fair_prob",             # Poisson-derived P(model side wins)
    "fair_american",
    "edge_pred",
    "data_quality",
    "status",                # pending | won | lost | push | void
    "units_risked",
    "units_pl",
    "actual_result",         # actual K count, BB count, etc.
    "settled_at",
    "notes",
]

# Per-market gates — tighter than the main betting layer because props are
# higher-variance and the model is less mature.
PAPER_MIN_EDGE = {
    "pitcher_strikeouts": 0.035,
    "pitcher_walks":      0.045,
    "batter_walks":       0.060,   # high-variance, need bigger gap
}
PAPER_MAX_EDGE      = 0.15   # match the calibration philosophy of the main
                              # betting layer (12% there + small prop-volatility
                              # buffer). Anything above ⇒ calibration bug, skip.
PAPER_MIN_DATA_Q    = {"ok", "stale"}   # skip "missing" / "small_sample"
PAPER_UNIT_SIZE     = 0.5    # flat 0.5u per paper bet


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def _ensure_paper_log(data_root: Path) -> Path:
    data_root.mkdir(parents=True, exist_ok=True)
    log = data_root / PAPER_LOG_FILENAME
    if not log.exists():
        with log.open("w", newline="") as f:
            csv.DictWriter(f, fieldnames=PAPER_FIELDS).writeheader()
    return log


def _read_paper_log(log: Path) -> list[dict]:
    if not log.exists(): return []
    with log.open() as f:
        return list(csv.DictReader(f))


def _write_paper_log(log: Path, rows: list[dict]) -> None:
    with log.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PAPER_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in PAPER_FIELDS})


def _next_id(rows: list[dict]) -> int:
    if not rows: return 1
    return max(int(r["bet_id"]) for r in rows if r.get("bet_id")) + 1


def _f(x, default=None):
    if x is None or x == "": return default
    try: return float(x)
    except (ValueError, TypeError): return default


def _i(x, default=None):
    if x is None or x == "": return default
    try: return int(x)
    except (ValueError, TypeError): return default


def _payout_units(price: int, units: float) -> float:
    return units * (price / 100.0) if price > 0 else units * (100.0 / -price)


# ---------------------------------------------------------------------------
# Probability — Poisson tail for K/BB counts
# ---------------------------------------------------------------------------

def _poisson_cdf(k: int, lam: float) -> float:
    """P(X <= k) for X ~ Poisson(lam). Iterative to avoid math.factorial overflow."""
    if lam <= 0: return 1.0 if k >= 0 else 0.0
    if k < 0: return 0.0
    s = 0.0
    term = math.exp(-lam)
    s += term
    for i in range(1, k + 1):
        term *= lam / i
        s += term
    return min(1.0, s)


def poisson_over_prob(line: float, lam: float) -> float:
    """P(X > line) where X ~ Poisson(lam). Lines are typically .5 (no push)."""
    # over wins if X >= ceil(line + 0.5) = floor(line) + 1 (for .5 lines)
    # Use k = floor(line); over = 1 - P(X <= k)
    k = int(math.floor(line))
    return 1.0 - _poisson_cdf(k, lam)


def poisson_under_prob(line: float, lam: float) -> float:
    """P(X < line). For .5 lines no push possible; for integer lines push = P(X==line)."""
    k = int(math.floor(line))
    if abs(line - k) < 0.01:        # integer line — under is X <= k-1
        return _poisson_cdf(k - 1, lam)
    return _poisson_cdf(k, lam)     # .5 line — under is X <= floor(line)


# ---------------------------------------------------------------------------
# Odds parsing helpers
# ---------------------------------------------------------------------------

def _book_outcomes(event_payload: dict, market_key: str, books: tuple[str, ...]):
    """Yield (book_key, outcome) for every matching outcome at the target books."""
    for b in event_payload.get("bookmakers", []):
        bk = b.get("key", "").lower()
        if bk not in books: continue
        market = next((m for m in b.get("markets", []) if m.get("key") == market_key), None)
        if not market: continue
        for o in market.get("outcomes", []):
            yield bk, o


def _devig_player_total(event_payload: dict, market_key: str,
                        player_desc: str, line: float) -> float | None:
    """Devigged P(over) for one player's prop at a specific line.

    Prefers Pinnacle when available. Falls back to the MEDIAN of per-book
    devigged probabilities across the user-facing books — most prop markets
    are not carried by Pinnacle, so this fallback is essential for paper
    bets to be anchored to a market consensus instead of raw Poisson.
    """
    candidates: list[float] = []
    for b in event_payload.get("bookmakers", []):
        bk = b.get("key", "").lower()
        if bk not in (TARGET_BOOKS + SHARP_ANCHORS): continue
        market = next((m for m in b.get("markets", []) if m.get("key") == market_key), None)
        if not market: continue
        over = under = None
        for o in market.get("outcomes", []):
            if (o.get("description") or "").lower() != player_desc.lower(): continue
            if abs(float(o.get("point", 0) or 0) - line) > 0.001: continue
            name = (o.get("name") or "").lower()
            if name == "over": over = int(o["price"])
            elif name == "under": under = int(o["price"])
        if over is None or under is None: continue
        ov, _ = devig_two_way(over, under)
        if bk in SHARP_ANCHORS:
            # Pinnacle takes priority — return immediately
            return ov
        candidates.append(ov)
    if not candidates: return None
    candidates.sort()
    return candidates[len(candidates)//2]   # median


def _best_player_total(event_payload: dict, market_key: str, player_desc: str,
                       side: str, line: float) -> tuple[int | None, str]:
    """Best price at the same exact line at the user-facing books."""
    best, best_book = None, ""
    for bk, o in _book_outcomes(event_payload, market_key, TARGET_BOOKS):
        if (o.get("description") or "").lower() != player_desc.lower(): continue
        if (o.get("name") or "").lower() != side: continue
        if abs(float(o.get("point", 0) or 0) - line) > 0.001: continue
        p = int(o["price"])
        if best is None or p > best:
            best, best_book = p, bk
    return best, best_book


def _consensus_line(event_payload: dict, market_key: str, player_desc: str) -> float | None:
    """Pick the line posted at the most books for this player (mode line)."""
    lines: list[float] = []
    for b in event_payload.get("bookmakers", []):
        market = next((m for m in b.get("markets", []) if m.get("key") == market_key), None)
        if not market: continue
        seen_for_this_book = set()
        for o in market.get("outcomes", []):
            if (o.get("description") or "").lower() != player_desc.lower(): continue
            pt = o.get("point")
            if pt is None: continue
            seen_for_this_book.add(float(pt))
        for pt in seen_for_this_book:
            lines.append(pt)
    if not lines: return None
    # Mode (most-common line)
    counts: dict[float, int] = {}
    for x in lines: counts[x] = counts.get(x, 0) + 1
    return max(counts.items(), key=lambda kv: (kv[1], -kv[0]))[0]


# ---------------------------------------------------------------------------
# Card generation
# ---------------------------------------------------------------------------

@dataclass
class PaperCard:
    market: str
    player_name: str
    player_id: int | None
    side: str          # over | under
    line: float
    book: str
    price: int
    projection: float
    fair_prob: float
    fair_american: int
    edge: float
    data_quality: str


def _eval_player_prop(event_payload: dict, market_key: str, player_desc: str,
                      player_id: int | None, projection: float,
                      data_quality: str) -> list[PaperCard]:
    """Return any paper cards that clear thresholds for one player's prop."""
    out: list[PaperCard] = []
    if data_quality not in PAPER_MIN_DATA_Q:
        return out
    line = _consensus_line(event_payload, market_key, player_desc)
    if line is None: return out
    # Plausibility guards
    if market_key == "pitcher_strikeouts" and not (2.5 <= line <= 12.5): return out
    if market_key == "pitcher_walks"      and not (0.5 <= line <= 4.5):  return out
    if market_key == "batter_walks"       and not (0.5 <= line <= 2.5):  return out

    for side in ("over", "under"):
        price, book = _best_player_total(event_payload, market_key, player_desc, side, line)
        if price is None: continue
        prob = poisson_over_prob(line, projection) if side == "over" \
               else poisson_under_prob(line, projection)
        # Anchor to market (Pinnacle devigged when available, otherwise the
        # median devigged prob across the user books). Model nudge capped at
        # +/-6pp so paper edges stay in the realistic 2-8% range — matches
        # what's defensible for the main betting layer.
        market_over = _devig_player_total(event_payload, market_key, player_desc, line)
        if market_over is not None:
            market_prior = market_over if side == "over" else (1.0 - market_over)
            shift = max(-0.06, min(0.06, prob - 0.50))
            prob = max(0.05, min(0.95, market_prior + shift))
        else:
            # No market anchor at all — extremely rare since the fallback
            # already covers the user books. Skip rather than fire a
            # raw-Poisson estimate that has no calibration relationship to
            # what the books are pricing.
            continue
        edge = edge_pct(prob, price)
        if edge < PAPER_MIN_EDGE.get(market_key, 0.05): continue
        if edge > PAPER_MAX_EDGE: continue
        from mlb_data_scraper import prob_to_american
        out.append(PaperCard(
            market=market_key, player_name=player_desc, player_id=player_id,
            side=side, line=line, book=book, price=price,
            projection=projection, fair_prob=prob,
            fair_american=prob_to_american(prob), edge=edge,
            data_quality=data_quality,
        ))
    return out


def generate_paper_cards(graded_games: list[dict], prop_odds: dict) -> list[dict]:
    """For every graded game with prop projections + market lines, compute
    paper cards. Returns flat list of (game, card_dict) suitable for logging."""
    events = (prop_odds or {}).get("events", {})
    cards_out: list[dict] = []
    for game in graded_games:
        # Match prop_odds event by team names — the event_id is keyed in prop_odds
        away = game["matchup"].split(" @ ")[0]
        home = game["matchup"].split(" @ ")[1]
        event_payload = None
        event_id = None
        for eid, ev in events.items():
            if ev.get("home_team") == home and ev.get("away_team") == away:
                event_payload = ev; event_id = eid
                break
        if not event_payload: continue
        tp = game.get("tracked_props") or {}

        # Pitcher strikeouts
        for p in tp.get("pitcher_ks", []):
            cards = _eval_player_prop(
                event_payload, "pitcher_strikeouts",
                p.get("name", ""), p.get("id"),
                projection=p.get("projected_k", 0.0),
                data_quality=p.get("data_quality", "missing"),
            )
            for c in cards:
                cards_out.append({"game": game, "event_id": event_id, "card": c})

        # Pitcher walks
        for p in tp.get("pitcher_walks", []):
            cards = _eval_player_prop(
                event_payload, "pitcher_walks",
                p.get("name", ""), p.get("id"),
                projection=p.get("projected_walks", 0.0),
                data_quality=p.get("data_quality", "missing"),
            )
            for c in cards:
                cards_out.append({"game": game, "event_id": event_id, "card": c})

        # Batter walks
        for b in tp.get("batter_walks", []):
            cards = _eval_player_prop(
                event_payload, "batter_walks",
                b.get("name", ""), b.get("id"),
                projection=b.get("projected_walks", 0.0),
                data_quality=b.get("data_quality", "missing"),
            )
            for c in cards:
                cards_out.append({"game": game, "event_id": event_id, "card": c})

    return cards_out


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def append_paper_log(data_root: Path, target_date: str,
                     paper_cards: list[dict]) -> int:
    """Append all paper cards for a date to prop_paper_log.csv.
    Dedups on (date, gamePk, market, player_name, side, line, book)."""
    log = _ensure_paper_log(data_root)
    rows = _read_paper_log(log)
    existing = {(r["date"], r["gamePk"], r["market"], r["player_name"],
                 r["side"], r["line"], r["book"]) for r in rows}
    next_id = _next_id(rows)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    added = 0
    for entry in paper_cards:
        game = entry["game"]
        c: PaperCard = entry["card"]
        key = (target_date, str(game["gamePk"]), c.market, c.player_name,
               c.side, str(c.line), c.book)
        if key in existing: continue
        rows.append({
            "bet_id": str(next_id),
            "recommended_at": now,
            "date": target_date,
            "gamePk": str(game["gamePk"]),
            "event_id": entry["event_id"],
            "matchup": game["matchup"],
            "first_pitch": game.get("gameDate", ""),
            "market": c.market,
            "player_name": c.player_name,
            "player_id": str(c.player_id) if c.player_id is not None else "",
            "side": c.side, "line": str(c.line),
            "book": c.book, "price": str(c.price),
            "model_projection": f"{c.projection:.3f}",
            "fair_prob": f"{c.fair_prob:.4f}",
            "fair_american": str(c.fair_american),
            "edge_pred": f"{c.edge:.4f}",
            "data_quality": c.data_quality,
            "status": "pending",
            "units_risked": str(PAPER_UNIT_SIZE),
            "units_pl": "", "actual_result": "",
            "settled_at": "", "notes": "",
        })
        next_id += 1
        added += 1
    _write_paper_log(log, rows)
    return added


# ---------------------------------------------------------------------------
# Settlement
# ---------------------------------------------------------------------------

MLB_API = "https://statsapi.mlb.com/api/v1.1"


def _fetch_boxscore_player_stats(game_pk: int) -> dict | None:
    """Returns the full live-feed boxscore.players dict — keyed by side
    then by 'ID<player_id>'. Returns None if game isn't Final."""
    try:
        url = f"{MLB_API}/game/{game_pk}/feed/live"
        data = requests.get(url, timeout=20).json()
    except Exception:
        return None
    state = (data.get("gameData", {}).get("status", {}).get("abstractGameState"))
    if state != "Final": return None
    return data.get("liveData", {}).get("boxscore", {}).get("teams", {})


def _player_stat(box_teams: dict, player_id: int, group: str, stat: str) -> int | None:
    """Pull `stat` from `group` (e.g. 'pitching' / 'batting') for a player.
    Returns None if player not found."""
    if not box_teams: return None
    for side in ("home", "away"):
        players = box_teams.get(side, {}).get("players", {})
        p = players.get(f"ID{player_id}")
        if not p: continue
        grp = p.get("stats", {}).get(group, {})
        if not grp: return None
        val = grp.get(stat)
        try: return int(val) if val is not None else None
        except (ValueError, TypeError): return None
    return None


def _settle_one_paper(row: dict, box_teams: dict | None) -> tuple[str, float, str, int | None]:
    """Returns (status, units_pl, notes, actual)."""
    market = row["market"]
    side   = row["side"]
    line   = _f(row["line"])
    price  = _i(row["price"])
    risk   = _f(row["units_risked"], 0.0)
    pid    = _i(row.get("player_id"))
    if pid is None or line is None or price is None:
        return ("void", 0.0, "missing fields", None)
    if box_teams is None:
        return ("pending", 0.0, "", None)
    if market == "pitcher_strikeouts":
        actual = _player_stat(box_teams, pid, "pitching", "strikeOuts")
    elif market == "pitcher_walks":
        actual = _player_stat(box_teams, pid, "pitching", "baseOnBalls")
    elif market == "batter_walks":
        actual = _player_stat(box_teams, pid, "batting", "baseOnBalls")
    else:
        return ("void", 0.0, f"unknown market {market}", None)
    if actual is None:
        return ("void", 0.0, "player did not appear", actual)
    win = (actual > line) if side == "over" else (actual < line)
    push = (abs(actual - line) < 0.001)
    if push: return ("push", 0.0, "push", actual)
    if win:  return ("won", round(_payout_units(price, risk), 4), "", actual)
    return ("lost", -round(risk, 4), "", actual)


def settle_paper_props(data_root: Path) -> int:
    log = _ensure_paper_log(data_root)
    rows = _read_paper_log(log)
    pending = [r for r in rows if r["status"] == "pending"]
    if not pending:
        return 0
    cache: dict[int, dict | None] = {}
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    now_dt = datetime.now(timezone.utc)
    settled = 0
    for r in pending:
        pk = _i(r["gamePk"])
        if pk is None: continue
        if pk not in cache:
            cache[pk] = _fetch_boxscore_player_stats(pk)
        box = cache[pk]
        status, units_pl, notes, actual = _settle_one_paper(r, box)
        if status == "pending":
            # Auto-void stale (game never reached Final after 3 days)
            fp = r.get("first_pitch")
            if fp:
                try:
                    ts = datetime.fromisoformat(fp.replace("Z", "+00:00"))
                    if (now_dt - ts).days >= 3:
                        r["status"] = "void"; r["units_pl"] = "0.0000"
                        r["settled_at"] = now
                        r["notes"] = "auto-void: postponed/stale"
                        settled += 1
                except Exception:
                    pass
            continue
        r["status"] = status
        r["units_pl"] = f"{units_pl:.4f}"
        r["actual_result"] = "" if actual is None else str(actual)
        r["settled_at"] = now
        if notes: r["notes"] = notes
        settled += 1
    _write_paper_log(log, rows)
    return settled


# ---------------------------------------------------------------------------
# P/L report
# ---------------------------------------------------------------------------

@dataclass
class PaperBucket:
    market: str
    bets: int = 0
    won: int = 0
    lost: int = 0
    push: int = 0
    void: int = 0
    pending: int = 0
    units_risked: float = 0.0
    units_pl: float = 0.0

    def add(self, row: dict) -> None:
        self.bets += 1
        st = row["status"]
        if st == "pending": self.pending += 1; return
        if st == "void":    self.void += 1;    return
        self.units_risked += _f(row.get("units_risked"), 0.0)
        self.units_pl     += _f(row.get("units_pl"), 0.0)
        if st == "won":  self.won += 1
        elif st == "lost": self.lost += 1
        elif st == "push": self.push += 1

    @property
    def settled(self) -> int: return self.won + self.lost + self.push
    @property
    def win_pct(self) -> float:
        decided = self.won + self.lost
        return self.won / decided if decided else 0.0
    @property
    def roi(self) -> float:
        return (self.units_pl / self.units_risked) if self.units_risked else 0.0


def paper_pnl_summary(data_root: Path, window_days: int = 7) -> dict:
    """Build a per-market P/L summary over the last N days.

    Includes a `compare_real` block from bet_log.csv aggregated over the same
    window so the user can see whether prop edges look more profitable than
    the ML/total markets we're already firing on.
    """
    from datetime import date, timedelta
    log = _ensure_paper_log(data_root)
    rows = _read_paper_log(log)
    today = date.today()
    cutoff = today - timedelta(days=window_days)
    filtered = []
    for r in rows:
        try:
            d = date.fromisoformat(r.get("date", ""))
        except Exception: continue
        if d < cutoff: continue
        filtered.append(r)
    buckets: dict[str, PaperBucket] = {}
    for r in filtered:
        m = r["market"]
        buckets.setdefault(m, PaperBucket(market=m)).add(r)

    # Real (live) bets P/L for comparison
    real = {"all": PaperBucket(market="ALL"), "moneyline": PaperBucket(market="moneyline"),
            "total": PaperBucket(market="total"), "runline": PaperBucket(market="runline"),
            "f5_total": PaperBucket(market="f5_total"), "nrfi": PaperBucket(market="nrfi")}
    real_log = data_root / "bet_log.csv"
    if real_log.exists():
        with real_log.open() as f:
            for r in csv.DictReader(f):
                try:
                    d = date.fromisoformat(r.get("date", ""))
                except Exception: continue
                if d < cutoff: continue
                real["all"].add(r)
                if r.get("market") in real:
                    real[r["market"]].add(r)

    return {
        "window_days": window_days,
        "window_start": cutoff.isoformat(),
        "paper": {m: b for m, b in buckets.items()},
        "real": real,
    }


def render_pnl_markdown(summary: dict) -> str:
    lines: list[str] = []
    lines.append(f"# Paper Props — P/L Summary (last {summary['window_days']} days)\n")
    lines.append(f"_Window: {summary['window_start']} → today_  ")
    lines.append("_Paper bets only — no real money involved. Sized flat at 0.5u each._\n")

    lines.append("\n## Paper props by market\n")
    lines.append("| Market | Bets | W-L-P-V-P | Win% | Risked | Profit | ROI |")
    lines.append("|---|---:|:---:|---:|---:|---:|---:|")
    for m, b in sorted(summary["paper"].items()):
        lines.append(f"| {m} | {b.bets} | "
                     f"{b.won}-{b.lost}-{b.push}-{b.void}-{b.pending} | "
                     f"{b.win_pct*100:.1f}% | {b.units_risked:.1f}u | "
                     f"{b.units_pl:+.2f}u | {b.roi*100:+.2f}% |")

    lines.append("\n## Real bets by market (same window, for comparison)\n")
    lines.append("| Market | Bets | W-L-P-V-P | Win% | Risked | Profit | ROI |")
    lines.append("|---|---:|:---:|---:|---:|---:|---:|")
    for m in ("all", "moneyline", "total", "runline", "f5_total", "nrfi"):
        b = summary["real"][m]
        lines.append(f"| {m} | {b.bets} | "
                     f"{b.won}-{b.lost}-{b.push}-{b.void}-{b.pending} | "
                     f"{b.win_pct*100:.1f}% | {b.units_risked:.1f}u | "
                     f"{b.units_pl:+.2f}u | {b.roi*100:+.2f}% |")

    lines.append("\n## Interpretation\n")
    lines.append("- Compare **ROI** between the paper-prop markets and the real bets above.")
    lines.append("- A statistically meaningful comparison needs ~50+ settled bets per "
                 "market — early-window numbers will swing.")
    lines.append("- If paper props sustain **higher ROI** over ~150-200 settled bets, "
                 "we promote them to the real betting layer with strict gates.")
    return "\n".join(lines)
