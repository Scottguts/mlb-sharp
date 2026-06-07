"""
MLB Sharp Betting — Game Grader & Bet Card Generator
=====================================================

Reads JSON produced by `mlb_data_scraper.py` and emits:
  * `grades.json` — 0-100 grade per side per game across the 7 categories,
                    plus derived fair win probabilities, fair total runs,
                    fair F5 totals, fair NRFI/YRFI prices, and per-bet edge
                    vs the best price among the user's 4 target books.
  * `cards.md`    — filtered betting cards in the system's exact format.

Markets covered:
  * Full-game Moneyline
  * Full-game Run Line
  * Full-game Total
  * First-5-innings Total (F5)
  * No-Run-First-Inning / Yes-Run-First-Inning (NRFI / YRFI)

Books shopped:
  FanDuel, DraftKings, BetMGM, Caesars
  (Pinnacle is used as the sharp devig anchor only — never displayed
   as the "best book to bet at".)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from dataclasses import dataclass, asdict, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from mlb_data_scraper import (
    american_to_prob, prob_to_american, devig_two_way, edge_pct,
    TARGET_BOOKS, SHARP_ANCHORS,
)
from prop_tracking import build_tracked_props, render_markdown as render_props_md


# ===========================================================================
# CONFIG — tune these without touching logic
# ===========================================================================

# Category weights (must sum to 100)
# Rebalanced 2026-06-02: starter quality + team offense should drive most
# of the prediction in MLB. Bullpen is a tiebreaker for late innings, not
# the lead signal. 'Market' was 15 but it's also baked into the win-prob
# anchor — partial double-count, so trimmed.
#
# Old (pitching 25 / bullpen 15 / offense 15 / market 15)
# New (pitching 32 / bullpen 10 / offense 22 / market 10)
WEIGHTS = {
    "pitching":      32,   # +7  — starter quality is the #1 driver
    "bullpen":       10,   # -5  — usage/quality matters but secondary
    "offense":       22,   # +7  — team hitting + matchup hand splits
    "weather_park":  10,
    "market":        10,   # -5  — market signal already in win-prob anchor
    "situational":    8,   # -2
    "injury_lineup":  8,   # -2
}
# Sanity: must sum to 100
assert sum(WEIGHTS.values()) == 100, f"WEIGHTS sum = {sum(WEIGHTS.values())}"

# Win-prob model parameters
# CALIBRATION PHILOSOPHY: anchor to the market, not to absolute probabilities.
# The market (Pinnacle devigged) is the world's most accurate MLB win-prob
# estimator. Our edge is making *small, evidence-backed* adjustments to it
# based on signals the market may not have fully priced (velocity drops,
# bullpen exhaustion, lineup confirmations, weather, umpire).
#
# Without the market anchor, an unanchored 0-100 grade model will think every
# +200 underdog has a 50% chance and report fake 30%+ edges. Don't do that.
LEAGUE_AVG_TOTAL = 8.86    # fallback baseline runs per game (2022-24 trailing avg)
HOME_FIELD_PROB  = 0.025   # home edge as a probability bump (2022-24 home win % - 50%)
GRADE_TO_PROB    = 0.0025  # win-prob shift per grade-point edge (was 0.0035 — tightened
                            # after recent-30 analysis showed bigger model-vs-market gaps
                            # correlate with worse outcomes)
MAX_PROB_SHIFT   = 0.035   # cap deviation from market prior at +/-3.5pp (was 5%) —
                            # the 4.5-6% edge bucket had 22% W / -70% ROI; tightening
                            # the deviation cap eliminates those overconfident plays
GRADE_TO_RUNS    = 0.06    # total-runs shift per grade-point pitching/bullpen edge
MAX_TOTAL_SHIFT  = 0.80    # cap deviation from market total at +/-0.8 runs

# F5 model parameters (no bullpen contribution)
F5_LEAGUE_AVG    = 4.99    # fallback baseline F5 runs per game (2022-24 trailing avg)
MAX_F5_SHIFT     = 0.50    # cap deviation from market F5 line at +/-0.5 runs

# NRFI model parameters
LEAGUE_NRFI_RATE = 0.516   # 2022-24 trailing avg; rose noticeably from 2020-22
MAX_NRFI_SHIFT   = 0.06    # cap deviation from market-implied NRFI prob at +/-6pp

# Refresh these annually using historical_validate.py — see its output
# `historical_report_<startYear>_<endYear>.md` for the latest numbers.

# Minimum edge to publish a bet card by market type.
# Calibrated 2026-06-02 from 64 settled post-fix bets in bet_log.csv.
#
# Key empirical finding: the 2.5-4% edge bucket actually WINS (52% W, +4.5%
# ROI), while the 8-12% bucket loses badly (25% W, -77% ROI). Higher edges
# correlate with worse outcomes — classic model overconfidence on bets where
# we disagree heavily with the market. So we LOWER min edge and TIGHTEN max
# edge, capturing more small-edge plays and killing the trap-line zone.
MIN_EDGE = {
    "moneyline":  0.018,    # lowered to recapture daily play volume after
                             # rebalancing weights away from bullpen
    "runline":    0.035,
    "total":      0.025,
    "f5_total":   0.035,
    "nrfi":       0.035,
}

# Cap on advertised edge — anything above this is treated as a calibration
# bug rather than a real edge. Tightened from 0.12 to 0.06 after seeing
# the 8-12% bucket go 25% W / -77% ROI on 4 bets, including multiple
# FanDuel plus-money "edges" that turned into 1.5u losers.
MAX_REASONABLE_EDGE = 0.06

# Win-prob bias: never bet a team rated below this. Plus-money underdog
# "edges" where the model gives the dog <45% chance to actually win have
# been a disaster (FanDuel +130 dogs at 0-3 in the 8%+ edge bucket).
MIN_TEAM_WIN_PROB = 0.45

# Price range guard — no deep favorites (need 60%+ win rate to break even
# at -150 and worse) and no long dogs (variance hell).
MIN_AMERICAN_PRICE = -180
MAX_AMERICAN_PRICE = +180

# Two-book confirmation: the "best price" must also be available within this
# many cents at another target book. Kills FanDuel-only trap lines where
# their juiciest plus-money looks like edge but is just promo pricing.
BOOK_CONFIRMATION_TOLERANCE_CENTS = 8

# Markets to actually generate cards for. Setting False here suppresses
# the entire market type even if the threshold above would qualify.
ENABLED_MARKETS = {
    "moneyline":  True,
    "runline":    False,    # disabled — see MIN_EDGE comment above
    "total":      True,
    "f5_total":   True,
    "nrfi":       True,
    "pitcher_strikeouts": True,   # promoted from paper to real (2026-06-03)
    "pitcher_walks":      True,
}

# Umpire K%/BB% adjustment. High-K umps push under, contact-friendly push over.
# Each grade point of umpire K% deviation from average shifts expected total
# by this many runs.
UMPIRE_TOTAL_ADJUST = 0.30   # ~0.3 runs per std dev of ump K%

# Confidence floor — never publish a card below this
MIN_CONFIDENCE = 6   # only publish bets we genuinely believe in

# Unit sizing rules. 1u = 1% of bankroll.
# Re-calibrated 2026-06-02 from the bet-log analysis. Note that with
# MAX_REASONABLE_EDGE = 0.06, the old "Strong 6%+/8 conf" tier is now
# the ceiling. We also shift more volume to the small-edge bucket since
# that's where the model actually wins.
# (edge_floor, confidence_floor, units, risk_label)
UNIT_LADDER = [
    (0.050, 8, 1.5, "Strong"),    # 5%+ edge, 8/10 conf — near the new edge cap
    (0.035, 7, 1.0, "Standard"),  # 3.5%+ edge, 7/10 conf
    (0.018, 6, 0.5, "Lean"),      # 1.8%+ edge, 6/10 conf — daily-volume tier
]

# Hard caps — two pools, REGULAR (ML/total/RL/F5/NRFI) and PITCHER PROPS
# (K + BB). Separate pools so a heavy prop slate doesn't squeeze out the
# regular picks, and vice versa.
MAX_CARDS_PER_SLATE      = 5       # top-5 regular plays
MAX_UNITS_PER_SLATE      = 6.0     # regular pool bankroll cap
MAX_PROP_CARDS_PER_SLATE = 3       # top-3 prop plays (separate pool)
MAX_PROP_UNITS_PER_SLATE = 3.0     # prop pool bankroll cap
MAX_UNITS_PER_GAME       = 1.5     # regular-pool per-game unit cap (props excluded)
MAX_CARDS_PER_GAME       = 1       # only 1 REGULAR bet per game; props counted separately
ALLOW_PARLAYS            = False   # singles only

# Set of market keys that count as "pitcher prop" pool (vs regular pool)
PITCHER_PROP_MARKETS = ("pitcher_strikeouts", "pitcher_walks")

# Legacy alias (kept for backward compat in other files)
MAX_BETS_PER_SLATE     = MAX_UNITS_PER_SLATE


# ===========================================================================
# Dataclasses
# ===========================================================================

@dataclass
class CategoryScore:
    home: float
    away: float
    notes: list[str] = field(default_factory=list)

@dataclass
class BetCard:
    bet_label: str
    market: str               # moneyline / runline / total / f5_total / nrfi / pitcher_strikeouts / pitcher_walks
    side: str                 # home / away / over / under / nrfi / yrfi
    book: str
    price_american: int
    line: float | None
    fair_prob: float
    fair_american: int
    edge: float
    confidence: int
    unit_size: float
    risk: str
    reasoning: list[str]
    pass_triggers: list[str]
    # Player-prop fields (None for non-prop markets)
    player_id: int | None = None
    player_name: str | None = None


# ===========================================================================
# Helpers
# ===========================================================================

def _load(p: Path):     return json.loads(p.read_text())

def _safe(d, *keys, default=None):
    cur = d
    for k in keys:
        if cur is None: return default
        cur = cur.get(k) if isinstance(cur, dict) else None
    return cur if cur is not None else default

def _clip(x, lo, hi):  return max(lo, min(hi, x))


# ===========================================================================
# Sub-graders
# ===========================================================================

def grade_pitching(game: dict) -> CategoryScore:
    notes: list[str] = []
    out = {}
    for side in ("home", "away"):
        prof = _safe(game, side, "pitcher_profile") or {}
        if not prof.get("available"):
            out[side] = 5.0
            notes.append(f"{side}: pitcher profile unavailable — neutral 5")
            continue

        s = 5.0
        season_velo = prof.get("season_avg_velo")
        starts = prof.get("starts") or []
        if season_velo and starts:
            recent = starts[0].get("avg_velo")
            if recent:
                d = recent - season_velo
                if d <= -1.5:
                    s -= 2.0
                    notes.append(f"{side}: velo down {d:.1f} mph — RED FLAG")
                elif d <= -0.7:
                    s -= 1.0
                    notes.append(f"{side}: velo soft ({d:+.1f} mph)")
                elif d >= 0.7:
                    s += 0.5

        opp = "away" if side == "home" else "home"
        opp_lineup = _safe(game, "lineups", f"{opp}_lineup") or []
        opp_hand = _dominant_hand(opp_lineup)
        split = (prof.get("splits") or {}).get(opp_hand) if opp_hand else None
        if split:
            xwoba = split.get("xwoba")
            if xwoba is not None:
                if xwoba <= 0.290:   s += 2.0
                elif xwoba <= 0.310: s += 1.0
                elif xwoba >= 0.350: s -= 2.0
                elif xwoba >= 0.330: s -= 1.0
                notes.append(f"{side}: vs {opp_hand}HB xwOBA {xwoba:.3f}")

        csws = [st.get("csw") for st in starts if st.get("csw") is not None]
        if csws:
            csw = sum(csws)/len(csws)
            if csw >= 0.30: s += 1.0
            elif csw >= 0.28: s += 0.5
            elif csw < 0.25: s -= 0.5
            notes.append(f"{side}: CSW% L{len(csws)} starts {csw:.1%}")

        hhs = [st.get("hard_hit") for st in starts if st.get("hard_hit") is not None]
        if hhs:
            hh = sum(hhs)/len(hhs)
            if hh <= 0.33: s += 0.5
            elif hh >= 0.40: s -= 1.0

        # Pitch movement red flag — if a primary pitch's break shifted
        # materially in the last start, the starter is either injured,
        # mechanically off, or working on something new. Either way, it
        # raises variance and slightly hurts our expected line.
        mov_flags = prof.get("movement_flags") or []
        if mov_flags:
            s -= min(0.8, 0.4 * len(mov_flags))
            notes.append(f"{side}: {mov_flags[0]}")

        out[side] = _clip(s, 0, 10)
    return CategoryScore(home=out["home"], away=out["away"], notes=notes)


def grade_bullpen(game: dict) -> CategoryScore:
    """Bullpen grade combines USAGE (fatigue) and QUALITY (recent K%/BB%/ERA).
    A fresh-but-bad pen and a tired-but-elite pen used to grade the same;
    now they don't."""
    notes: list[str] = []
    out = {}
    for side in ("home", "away"):
        pen = _safe(game, side, "bullpen_usage", "relievers") or {}
        quality = _safe(game, side, "bullpen_usage", "quality") or {}
        if not pen and not quality:
            out[side] = 5.0
            notes.append(f"{side}: bullpen data missing — neutral 5")
            continue
        s = 6.0
        # Usage signal (fatigue)
        b2b = sum(1 for r in pen.values() if r.get("back_to_back"))
        gassed = sum(1 for r in pen.values()
                     if r.get("pitched_yesterday") and r.get("appearances", 0) >= 2)
        total_pitches = sum(r.get("pitches", 0) for r in pen.values())
        if gassed >= 3: s -= 2.0
        elif gassed == 2: s -= 1.0
        elif gassed == 0: s += 0.5
        if b2b >= 2: s -= 1.0
        if total_pitches > 850: s -= 1.0
        elif total_pitches < 500: s += 0.5

        # Quality signal (recent rate stats)
        # League-average bullpen 2024: ~22% K%, 9% BB%, 3.95 ERA
        k_pct  = quality.get("bp_k_pct")
        bb_pct = quality.get("bp_bb_pct")
        era    = quality.get("bp_era")
        ip     = quality.get("bp_innings") or 0
        if ip >= 5:   # need a meaningful sample
            if k_pct is not None:
                if k_pct >= 0.27:    s += 1.0
                elif k_pct >= 0.24:  s += 0.5
                elif k_pct < 0.18:   s -= 1.0
                elif k_pct < 0.21:   s -= 0.5
            if bb_pct is not None:
                if bb_pct >= 0.12:   s -= 1.0
                elif bb_pct >= 0.10: s -= 0.5
                elif bb_pct < 0.07:  s += 0.5
            if era is not None:
                if era <= 2.50:      s += 1.0
                elif era <= 3.50:    s += 0.5
                elif era >= 5.50:    s -= 1.5
                elif era >= 4.50:    s -= 0.5
            notes.append(f"{side} pen quality: K% {k_pct*100:.1f}, BB% {bb_pct*100:.1f}, ERA {era}"
                         if (k_pct is not None and bb_pct is not None and era is not None)
                         else f"{side} pen quality partial")
        # Bullpen handedness vs opposing lineup's primary hand.
        opp = "away" if side == "home" else "home"
        by_hand = quality.get("by_hand") or {}
        opp_lineup = _safe(game, "lineups", f"{opp}_lineup") or []
        opp_hand = _dominant_hand(opp_lineup)
        if opp_hand and by_hand:
            # We want the same hand as the opposing lineup's MAJORITY hand
            # (e.g. RHB-heavy lineup → we want LHP relievers to be available
            # because lefty arms are typically reverse-platoon-safe; but in
            # practice the SAME-hand path is the standard sharp angle:
            # RHB lineup → RHP reliever has the platoon edge).
            edge_hand = "R" if opp_hand == "R" else "L"
            edge_avail = (by_hand.get(edge_hand) or {}).get("fresh_count", 0)
            if edge_avail >= 3:
                s += 0.4
            elif edge_avail == 0:
                s -= 0.5
                notes.append(f"{side}: no fresh same-hand relievers vs {opp_hand}HB-heavy lineup")
        out[side] = _clip(s, 0, 10)
        notes.append(f"{side}: {gassed} arms gassed, {b2b} back-to-back, {total_pitches} pitches L7d")
    return CategoryScore(home=out["home"], away=out["away"], notes=notes)


def grade_offense(game: dict) -> CategoryScore:
    notes: list[str] = []
    out = {}
    for side in ("home", "away"):
        opp = "away" if side == "home" else "home"
        lineup = _safe(game, "lineups", f"{side}_lineup") or []
        opp_prof = _safe(game, opp, "pitcher_profile") or {}
        opp_hand = _starter_throw_hand(opp_prof)
        s = 5.0
        if lineup:
            n = len(lineup)
            if n < 9:
                s -= 0.5
                notes.append(f"{side}: short lineup ({n} batters)")
            if opp_hand:
                adv = sum(1 for b in lineup if _has_platoon_adv(b.get("bat_side"), opp_hand))
                pct = adv / n if n else 0
                if pct >= 0.7: s += 1.5
                elif pct >= 0.55: s += 0.7
                elif pct <= 0.3: s -= 0.5
                notes.append(f"{side}: {adv}/{n} platoon edge vs {opp_hand}HP")
        else:
            notes.append(f"{side}: lineup not confirmed — neutral baseline")

        # Recent form bump: above-average run production lately
        rf = _safe(game, side, "recent_form") or {}
        rpg = rf.get("rpg_for")
        if rpg is not None:
            if rpg >= 5.5:    s += 1.0; notes.append(f"{side}: hot bats ({rpg} RPG L14d)")
            elif rpg >= 5.0:  s += 0.5; notes.append(f"{side}: solid form ({rpg} RPG L14d)")
            elif rpg <= 3.5:  s -= 1.0; notes.append(f"{side}: cold bats ({rpg} RPG L14d)")
            elif rpg <= 4.0:  s -= 0.5; notes.append(f"{side}: slow form ({rpg} RPG L14d)")

        # Top-of-order quality (vs opposing starter's hand, when known).
        # Drives NRFI/F5/total prediction more than aggregate offense does,
        # because innings 1-3 are dominated by the top of the order.
        too = _safe(game, side, "top_of_order") or {}
        avg_woba = too.get("avg_woba")
        if avg_woba is not None:
            # MLB starter wOBA ~0.330; top-of-order skews higher.
            if   avg_woba >= 0.380: s += 1.5; notes.append(f"{side}: elite top-of-order wOBA {avg_woba:.3f}")
            elif avg_woba >= 0.355: s += 0.8; notes.append(f"{side}: strong top-of-order wOBA {avg_woba:.3f}")
            elif avg_woba <= 0.290: s -= 1.5; notes.append(f"{side}: weak top-of-order wOBA {avg_woba:.3f}")
            elif avg_woba <= 0.310: s -= 0.8; notes.append(f"{side}: soft top-of-order wOBA {avg_woba:.3f}")

        # 7-day rolling streak: avg recent wOBA across batters with sample.
        recent_wobas: list[float] = []
        for b in too.get("batters", []):
            r = b.get("recent_7d") or {}
            if r.get("available") and r.get("woba") is not None and r.get("pa", 0) >= 8:
                recent_wobas.append(r["woba"])
        if recent_wobas and avg_woba:
            avg_recent = sum(recent_wobas) / len(recent_wobas)
            delta = avg_recent - avg_woba
            if   delta >= +0.060: s += 0.7; notes.append(f"{side}: top-of-order heating up (7d wOBA {avg_recent:.3f})")
            elif delta >= +0.030: s += 0.3
            elif delta <= -0.060: s -= 0.7; notes.append(f"{side}: top-of-order cooling (7d wOBA {avg_recent:.3f})")
            elif delta <= -0.030: s -= 0.3

        # Travel penalty — long cross-country flights drag the bats.
        travel = _safe(game, side, "travel") or {}
        if travel.get("cross_country"):
            s -= 0.4
            notes.append(f"{side}: travel — {travel.get('miles_traveled')}mi since last game")

        out[side] = _clip(s, 0, 10)
    return CategoryScore(home=out["home"], away=out["away"], notes=notes)


def grade_weather_park(game: dict) -> CategoryScore:
    notes: list[str] = []
    venue = game.get("venue") or {}
    wx = game.get("weather") or {}
    pf = venue.get("pf_runs", 100)
    home = away = 5.0
    if wx.get("indoor"):
        notes.append("indoor / dome — weather neutral")
        return CategoryScore(home=5, away=5, notes=notes)
    if pf >= 105: notes.append(f"hitter park (pf_runs {pf})")
    elif pf <= 95: notes.append(f"pitcher park (pf_runs {pf})")
    temp = wx.get("temp_f")
    if temp is not None:
        if temp >= 80: notes.append(f"warm ({temp}°F) — ball carries")
        elif temp <= 55: notes.append(f"cold ({temp}°F) — ball dies")
    # Wind direction relative to centerfield (out/in/cross)
    we = wx.get("wind_effect") or {}
    eff = we.get("effect")
    if eff == "out":
        notes.append(f"wind {wx.get('wind_mph')}mph OUT to CF (Δ {we['delta_runs']:+.2f}r) — boosts totals")
    elif eff == "in":
        notes.append(f"wind {wx.get('wind_mph')}mph IN from CF (Δ {we['delta_runs']:+.2f}r) — suppresses totals")
    elif eff == "cross" and wx.get("wind_mph", 0) >= 12:
        notes.append(f"wind {wx.get('wind_mph')}mph crosswind — direction-dependent")
    precip = wx.get("precip_prob_pct")
    if precip is not None and precip >= 50:
        notes.append(f"rain risk {precip}% — re-check before bet time")
        home += 0.3; away += 0.3
    return CategoryScore(home=_clip(home, 0, 10), away=_clip(away, 0, 10), notes=notes)


def grade_market(game: dict, odds_for_game: dict | None) -> CategoryScore:
    notes: list[str] = []
    if not odds_for_game:
        notes.append("no odds snapshot — neutral 5")
        return CategoryScore(home=5, away=5, notes=notes)
    fair_h, fair_a = _pinnacle_fair_h2h(odds_for_game)
    bh_price, bh_book = _best_h2h_price(odds_for_game, "home")
    ba_price, ba_book = _best_h2h_price(odds_for_game, "away")
    home_score = away_score = 5.0
    if fair_h and bh_price is not None:
        gap = fair_h - american_to_prob(bh_price)
        if gap >= 0.04: home_score = 8.5
        elif gap >= 0.02: home_score = 7.0
        elif gap <= -0.02: home_score = 3.5
        notes.append(f"home best {bh_price:+d}@{bh_book}; fair {prob_to_american(fair_h):+d} ({fair_h:.1%}); gap {gap:+.2%}")
    if fair_a and ba_price is not None:
        gap = fair_a - american_to_prob(ba_price)
        if gap >= 0.04: away_score = 8.5
        elif gap >= 0.02: away_score = 7.0
        elif gap <= -0.02: away_score = 3.5
        notes.append(f"away best {ba_price:+d}@{ba_book}; fair {prob_to_american(fair_a):+d} ({fair_a:.1%}); gap {gap:+.2%}")
    return CategoryScore(home=_clip(home_score, 0, 10), away=_clip(away_score, 0, 10), notes=notes)


def grade_situational(game: dict) -> CategoryScore:
    notes: list[str] = []
    out = {"home": 5.0, "away": 5.0}
    for side in ("home", "away"):
        if not _safe(game, side, "probable_pitcher_id"):
            out[side] -= 1.5
            notes.append(f"{side}: no probable starter (bullpen game?)")
    # Catcher framing note — boosts the home pitcher's K projection if home
    # catcher is elite, hurts the away pitcher if away catcher is below avg.
    cf = game.get("catcher_framing") or {}
    if cf.get("available"):
        for side in ("home", "away"):
            runs = (cf.get(side) or {}).get("season_runs")
            if runs is None: continue
            if runs >= +6:    notes.append(f"{side} catcher: elite framer (+{runs:.0f} runs/season)")
            elif runs <= -5:  notes.append(f"{side} catcher: poor framer ({runs:.0f} runs/season)")
    return CategoryScore(home=out["home"], away=out["away"], notes=notes)


def grade_injury_lineup(game: dict) -> CategoryScore:
    notes: list[str] = []
    confirmed = _safe(game, "lineups", "lineups_confirmed")
    home = away = 6.5 if confirmed else 5.0
    notes.append("lineups confirmed" if confirmed else "lineups NOT confirmed — re-grade closer to first pitch")
    return CategoryScore(home=home, away=away, notes=notes)


# ===========================================================================
# Helpers used by graders / odds parsing — books restricted to TARGET_BOOKS
# ===========================================================================

def _dominant_hand(lineup):
    if not lineup: return None
    L = R = 0
    for b in lineup:
        s = (b.get("bat_side") or "").upper()
        if s == "L": L += 1
        elif s == "R": R += 1
        elif s == "S": L += 0.5; R += 0.5
    if L > R: return "L"
    if R > L: return "R"
    return None

def _starter_throw_hand(profile):
    """Throws hand (L/R) of the pitcher. Populated by fetch_pitcher_profile."""
    if not profile or not profile.get("available"): return None
    th = profile.get("throws")
    return th.upper() if th else None

def _has_platoon_adv(bat_side, pitch_hand):
    if not bat_side or not pitch_hand: return False
    bs, ph = bat_side.upper(), pitch_hand.upper()
    if bs == "S": return True
    return bs != ph

def _book_iter(odds_for_game, only_target_books=True):
    for b in odds_for_game.get("bookmakers", []):
        if only_target_books and b["key"].lower() not in TARGET_BOOKS:
            continue
        yield b

def _pinnacle_total_prob(odds_for_game, market_key="totals") -> tuple[float | None, float | None]:
    """Devigged Pinnacle P(over) at its posted line. Returns (over_prob, line)
    or (None, None) if Pinnacle isn't carrying that market.
    Used as the Bayesian prior for over/under bets so edges are bounded."""
    if not odds_for_game: return (None, None)
    pinny = next((b for b in odds_for_game.get("bookmakers", [])
                  if b["key"].lower() in SHARP_ANCHORS), None)
    if not pinny: return (None, None)
    m = next((m for m in pinny.get("markets", []) if m["key"] == market_key), None)
    if not m: return (None, None)
    over = next((o for o in m["outcomes"] if o.get("name", "").lower() == "over"), None)
    under = next((o for o in m["outcomes"] if o.get("name", "").lower() == "under"), None)
    if not over or not under: return (None, None)
    pt_o = over.get("point"); pt_u = under.get("point")
    if pt_o is None or pt_u is None or abs(float(pt_o) - float(pt_u)) > 0.001:
        return (None, None)   # different lines on each side; skip
    over_p, _ = devig_two_way(int(over["price"]), int(under["price"]))
    return (over_p, float(pt_o))


def _pinnacle_fair_h2h(odds_for_game):
    pinny = next((b for b in odds_for_game.get("bookmakers", [])
                  if b["key"].lower() in SHARP_ANCHORS), None)
    if not pinny: return None, None
    h2h = next((m for m in pinny.get("markets", []) if m["key"] == "h2h"), None)
    if not h2h: return None, None
    home, away = odds_for_game.get("home_team"), odds_for_game.get("away_team")
    h_p = a_p = None
    for o in h2h["outcomes"]:
        if o["name"] == home: h_p = int(o["price"])
        elif o["name"] == away: a_p = int(o["price"])
    if h_p is None or a_p is None: return None, None
    return devig_two_way(h_p, a_p)

def _best_h2h_price(odds_for_game, side):
    target = odds_for_game.get("home_team" if side == "home" else "away_team")
    best_price, best_book = None, ""
    prices: list[int] = []   # all target-book prices for this outcome
    for b in _book_iter(odds_for_game):
        h2h = next((m for m in b.get("markets", []) if m["key"] == "h2h"), None)
        if not h2h: continue
        for o in h2h["outcomes"]:
            if o["name"] == target:
                p = int(o["price"])
                prices.append(p)
                if best_price is None or p > best_price:
                    best_price, best_book = p, b["key"]
    # Two-book confirmation: require at least one OTHER book within tolerance
    # of the best price. Kills FanDuel-only promo lines that aren't real edge.
    if best_price is not None and len(prices) >= 2:
        others = [p for p in prices if p != best_price]
        if not any(abs(p - best_price) <= BOOK_CONFIRMATION_TOLERANCE_CENTS for p in others):
            return None, ""   # no confirmation → no play
    elif best_price is not None and len(prices) < 2:
        # Only one book carrying this market — too thin, skip
        return None, ""
    return best_price, best_book

def _best_runline_price(odds_for_game, side):
    """Best price for runline. side='home' looks for the home team's spread
    line (which will be either -1.5 (favorite) or +1.5 (dog))."""
    target = odds_for_game.get("home_team" if side == "home" else "away_team")
    best = (None, None, "")
    for b in _book_iter(odds_for_game):
        rl = next((m for m in b.get("markets", []) if m["key"] == "spreads"), None)
        if not rl: continue
        for o in rl["outcomes"]:
            if o["name"] != target: continue
            p, line = int(o["price"]), float(o.get("point", 0))
            if best[0] is None or p > best[0]:
                best = (p, line, b["key"])
    return best

def _best_total_price(odds_for_game, side, market_key="totals", target_line=None):
    """Best price across target books. If target_line is provided, only
    consider outcomes at that exact line. Requires two-book confirmation
    (a second book within tolerance) to filter out single-book trap lines."""
    best = (None, None, "")
    prices: list[int] = []
    for b in _book_iter(odds_for_game):
        t = next((m for m in b.get("markets", []) if m["key"] == market_key), None)
        if not t: continue
        for o in t["outcomes"]:
            if o["name"].lower() != side.lower(): continue
            p, line = int(o["price"]), float(o.get("point", 0))
            if target_line is not None and abs(line - target_line) > 0.001:
                continue
            prices.append(p)
            if best[0] is None or p > best[0]:
                best = (p, line, b["key"])
    # Two-book confirmation
    if best[0] is not None and len(prices) >= 2:
        others = [p for p in prices if p != best[0]]
        if not any(abs(p - best[0]) <= BOOK_CONFIRMATION_TOLERANCE_CENTS for p in others):
            return (None, None, "")
    elif best[0] is not None and len(prices) < 2:
        return (None, None, "")
    return best


# ===========================================================================
# Synthesis
# ===========================================================================

def total_grade(catscores):
    h = a = 0.0
    for cat, s in catscores.items():
        w = WEIGHTS[cat] / 10.0
        h += s.home * w; a += s.away * w
    return {"home": round(h, 1), "away": round(a, 1)}


# ===========================================================================
# Market-anchored priors (the heart of the calibration)
# ===========================================================================

def _market_total_line(odds_for_game) -> float | None:
    """Pinnacle full-game total line (consensus). Falls back to median across
    target books if Pinnacle is missing the market."""
    if not odds_for_game:
        return None
    pinny = next((b for b in odds_for_game.get("bookmakers", [])
                  if b["key"].lower() in SHARP_ANCHORS), None)
    candidates = []
    for b in odds_for_game.get("bookmakers", []):
        m = next((m for m in b.get("markets", []) if m["key"] == "totals"), None)
        if not m: continue
        for o in m.get("outcomes", []):
            pt = o.get("point")
            if pt is not None:
                candidates.append(float(pt))
                break
    if pinny:
        m = next((m for m in pinny.get("markets", []) if m["key"] == "totals"), None)
        if m:
            for o in m.get("outcomes", []):
                if o.get("point") is not None:
                    return float(o["point"])
    if candidates:
        candidates.sort()
        return candidates[len(candidates)//2]
    return None


def _market_f5_line(odds_for_game) -> float | None:
    if not odds_for_game:
        return None
    candidates = []
    for b in odds_for_game.get("bookmakers", []):
        m = next((m for m in b.get("markets", []) if m["key"] == "totals_1st_5_innings"), None)
        if not m: continue
        for o in m.get("outcomes", []):
            pt = o.get("point")
            if pt is not None:
                candidates.append(float(pt))
                break
    if not candidates:
        return None
    candidates.sort()
    return candidates[len(candidates)//2]


def _market_nrfi_prob(odds_for_game) -> float | None:
    """Pinnacle-devigged P(NRFI). Returns None if 1st-inning total market not posted."""
    if not odds_for_game:
        return None
    pinny = next((b for b in odds_for_game.get("bookmakers", [])
                  if b["key"].lower() in SHARP_ANCHORS), None)
    if not pinny: return None
    m = next((m for m in pinny.get("markets", []) if m["key"] == "totals_1st_1_innings"), None)
    if not m: return None
    over = next((o for o in m["outcomes"] if o.get("name", "").lower() == "over"), None)
    under = next((o for o in m["outcomes"] if o.get("name", "").lower() == "under"), None)
    if not over or not under:
        return None
    over_p, under_p = devig_two_way(int(over["price"]), int(under["price"]))
    return under_p   # NRFI = under


def grade_to_win_prob(home_grade, away_grade, odds_for_game=None):
    """Derive home/away win probability.

    PREFERRED PATH: take Pinnacle-devigged fair prob as the prior, then nudge
    it slightly based on grade differential (capped at ±MAX_PROB_SHIFT pp).
    This is what keeps edges realistic.

    FALLBACK PATH (no market): use the older grade-only formula.
    """
    fair_h = fair_a = None
    if odds_for_game:
        fair_h, fair_a = _pinnacle_fair_h2h(odds_for_game)
    diff = home_grade - away_grade
    if fair_h is not None:
        shift = _clip(diff * GRADE_TO_PROB, -MAX_PROB_SHIFT, MAX_PROB_SHIFT)
        h = _clip(fair_h + shift, 0.05, 0.95)
    else:
        # No market — fall back to a grade-only model with home-field bump
        shift = _clip(diff * 0.005, -0.10, 0.10)
        h = _clip(0.5 + shift + HOME_FIELD_PROB, 0.05, 0.95)
    return {"home": round(h, 4), "away": round(1 - h, 4)}

# Umpire K%/BB% lookup. Hand-curated from UmpScorecards multi-year data.
# K_DELTA: percentage points above/below league average (~22%) — positive = K-friendly
# Used to adjust F5 + total expected runs.
UMPIRE_TENDENCIES = {
    # K-friendly umps (push under)
    "Pat Hoberg":          { "k_delta": +1.6, "run_delta": -0.45 },
    "Jansen Visconti":     { "k_delta": +1.4, "run_delta": -0.35 },
    "Will Little":         { "k_delta": +1.2, "run_delta": -0.30 },
    "Tripp Gibson":        { "k_delta": +1.1, "run_delta": -0.30 },
    "Lance Barksdale":     { "k_delta": +1.0, "run_delta": -0.25 },
    "John Tumpane":        { "k_delta": +0.9, "run_delta": -0.20 },
    "Dan Iassogna":        { "k_delta": +0.8, "run_delta": -0.20 },
    "James Hoye":          { "k_delta": +0.7, "run_delta": -0.20 },
    "Edwin Moscoso":       { "k_delta": +0.6, "run_delta": -0.15 },
    "Jordan Baker":        { "k_delta": +0.6, "run_delta": -0.15 },
    # Contact-friendly umps (push over)
    "Angel Hernandez":     { "k_delta": -1.5, "run_delta": +0.40 },
    "C.B. Bucknor":        { "k_delta": -1.3, "run_delta": +0.35 },
    "Doug Eddings":        { "k_delta": -1.0, "run_delta": +0.30 },
    "Laz Diaz":            { "k_delta": -1.0, "run_delta": +0.25 },
    "Ron Kulpa":           { "k_delta": -0.9, "run_delta": +0.25 },
    "Phil Cuzzi":          { "k_delta": -0.9, "run_delta": +0.20 },
    "Larry Vanover":       { "k_delta": -0.7, "run_delta": +0.20 },
    "Hunter Wendelstedt":  { "k_delta": -0.6, "run_delta": +0.15 },
    "Manny Gonzalez":      { "k_delta": -0.5, "run_delta": +0.15 },
    "Jeremy Riggs":        { "k_delta": -0.5, "run_delta": +0.15 },
    # Refresh annually from UmpScorecards data
}


def _umpire_run_delta(game: dict) -> tuple[float, str | None]:
    """Returns (run_adjustment, ump_name) based on home plate umpire.

    Prefers the live 60-day tendency from MLB Stats API (`hp_ump_tendency`)
    over the hand-curated UMPIRE_TENDENCIES table — the live data captures
    ump drift and stays current automatically.
    """
    umps = _safe(game, "lineups", "umpires") or []
    hp = next((u for u in umps if (u.get("type") or "").lower() in
               ("home plate", "home", "hp", "plate")), None)
    if not hp: return 0.0, None
    name = hp.get("name", "")
    # Prefer dynamic tendency when we have a meaningful sample
    dyn = _safe(game, "lineups", "hp_ump_tendency") or {}
    if dyn.get("available") and dyn.get("n_games", 0) >= 5:
        # Clamp the live delta — extreme small-sample noise gets capped.
        return _clip(float(dyn["run_delta"]), -0.55, +0.55), name
    info = UMPIRE_TENDENCIES.get(name)
    if not info: return 0.0, name
    return info["run_delta"], name


def _grade_run_delta(game, catscores, weight_pitch=0.5, weight_pen=0.25, weight_off=0.25,
                     temp_coef=0.012, include_park=False) -> float:
    """Compute a deviation from the market total based on our signals.

    The market already prices the consensus park factor and most weather; we
    only nudge for things the market may not have caught up to: a velocity
    drop in last start, an exhausted pen, a notably hot/cold lineup, and the
    home-plate umpire's K%/run tendency. include_park=True is reserved for
    the fallback path when there is no market line.
    """
    delta = 0.0
    if include_park:
        pf = (_safe(game, "venue", "pf_runs") or 100) / 100.0
        delta += LEAGUE_AVG_TOTAL * (pf - 1.0)
    wx = game.get("weather") or {}
    if not wx.get("indoor", False):
        temp = wx.get("temp_f")
        if temp is not None:
            delta += (temp - 70) * temp_coef
        # Wind direction vs park CF (already capped at +/-0.4 runs in scraper)
        we = wx.get("wind_effect") or {}
        delta += float(we.get("delta_runs") or 0.0)
    avg_pitch = (catscores["pitching"].home + catscores["pitching"].away) / 2.0
    delta -= (avg_pitch - 5) * GRADE_TO_RUNS * weight_pitch * 4   # pitch grade is dominant
    avg_pen = (catscores["bullpen"].home + catscores["bullpen"].away) / 2.0
    delta -= (avg_pen - 5) * GRADE_TO_RUNS * weight_pen * 4
    avg_off = (catscores["offense"].home + catscores["offense"].away) / 2.0
    delta += (avg_off - 5) * GRADE_TO_RUNS * weight_off * 4
    ump_delta, _ = _umpire_run_delta(game)
    delta += ump_delta

    # Catcher framing: combined effect of both catchers on total runs.
    # A great-framing catcher behind plate steals strikes → fewer hits/runs.
    cf = game.get("catcher_framing") or {}
    if cf.get("available"):
        home_pg = (cf.get("home") or {}).get("per_game", 0.0) or 0.0
        away_pg = (cf.get("away") or {}).get("per_game", 0.0) or 0.0
        # Each catcher only frames for their own team's pitcher, so the
        # combined impact on total runs is the SUM (both are run-suppressing
        # when positive).
        delta -= (home_pg + away_pg)

    # Travel + rest: long cross-country flights cost the offense ~0.1-0.2 r.
    # If BOTH teams flew, effects roughly cancel.
    home_t = (game.get("home") or {}).get("travel") or {}
    away_t = (game.get("away") or {}).get("travel") or {}
    travel_penalty = 0.0
    if home_t.get("cross_country"): travel_penalty -= 0.10
    if away_t.get("cross_country"): travel_penalty -= 0.15   # away takes the hit more
    delta += travel_penalty
    return delta


def expected_total_runs(game, catscores, odds_for_game=None) -> float:
    """Market-anchored full-game total. Starts from Pinnacle/median market
    line and shifts by at most ±MAX_TOTAL_SHIFT runs based on our signals.
    Falls back to the additive league-baseline model if no market is found
    or the market line is implausible (DH 7-inning game, F5 mislabeled, etc)."""
    market_line = _market_total_line(odds_for_game) if odds_for_game else None
    if market_line is not None and 6.0 <= market_line <= 13.5:
        delta = _grade_run_delta(game, catscores, weight_pitch=0.5, weight_pen=0.25,
                                 weight_off=0.25, temp_coef=0.015, include_park=False)
        delta = _clip(delta, -MAX_TOTAL_SHIFT, MAX_TOTAL_SHIFT)
        return round(market_line + delta, 2)
    # Fallback: original league-baseline math
    pf = (_safe(game, "venue", "pf_runs") or 100) / 100.0
    base = LEAGUE_AVG_TOTAL * pf
    wx = game.get("weather") or {}
    if not wx.get("indoor", False):
        temp = wx.get("temp_f")
        if temp is not None: base += (temp - 70) * 0.015
    avg_pitch = (catscores["pitching"].home + catscores["pitching"].away) / 2.0
    base -= (avg_pitch - 5) * 0.20
    avg_pen = (catscores["bullpen"].home + catscores["bullpen"].away) / 2.0
    base -= (avg_pen - 5) * 0.10
    ump_delta, _ = _umpire_run_delta(game)
    base += ump_delta
    return round(base, 2)


def expected_f5_total(game, catscores, odds_for_game=None) -> float:
    """Market-anchored F5 total. Same idea as the full-game model but with
    no bullpen contribution and a tighter cap on deviation from market."""
    market_line = _market_f5_line(odds_for_game) if odds_for_game else None
    if market_line is not None and 2.5 <= market_line <= 7.5:
        delta = _grade_run_delta(game, catscores, weight_pitch=0.7, weight_pen=0.0,
                                 weight_off=0.3, temp_coef=0.010, include_park=False)
        # umpire half-effect for F5 is already in _grade_run_delta via _umpire_run_delta;
        # F5 sees ~5/9 of innings so the ump effect per inning is similar — leave full delta.
        delta = _clip(delta, -MAX_F5_SHIFT, MAX_F5_SHIFT)
        return round(market_line + delta, 2)
    # Fallback: original baseline
    pf = (_safe(game, "venue", "pf_runs") or 100) / 100.0
    base = F5_LEAGUE_AVG * pf
    wx = game.get("weather") or {}
    if not wx.get("indoor", False):
        temp = wx.get("temp_f")
        if temp is not None: base += (temp - 70) * 0.010
    avg_pitch = (catscores["pitching"].home + catscores["pitching"].away) / 2.0
    base -= (avg_pitch - 5) * 0.30
    ump_delta, _ = _umpire_run_delta(game)
    base += ump_delta * 0.55
    return round(base, 2)


def estimate_nrfi_prob(game, catscores, odds_for_game=None) -> tuple[float, list[str]]:
    """Market-anchored NRFI probability.

    PREFERRED PATH: start from Pinnacle-devigged P(NRFI), nudge slightly by
    pitching grade and offense grade. Capped at ±MAX_NRFI_SHIFT.

    FALLBACK PATH: league-rate Bayesian update if no 1st-inning market posted.
    """
    notes: list[str] = []
    market_p = _market_nrfi_prob(odds_for_game) if odds_for_game else None
    avg_pitch = (catscores["pitching"].home + catscores["pitching"].away) / 2.0
    avg_off = (catscores["offense"].home + catscores["offense"].away) / 2.0
    grade_shift = (avg_pitch - 5) * 0.012 - (avg_off - 5) * 0.008
    if market_p is not None:
        grade_shift = _clip(grade_shift, -MAX_NRFI_SHIFT, MAX_NRFI_SHIFT)
        p = _clip(market_p + grade_shift, 0.30, 0.85)
        notes.append(f"market NRFI prior {market_p:.1%} → adj {grade_shift:+.1%}")
        return round(p, 4), notes
    p = LEAGUE_NRFI_RATE + grade_shift
    notes.append(f"no 1st-inn market — league prior {LEAGUE_NRFI_RATE:.1%} adj {grade_shift:+.1%}")
    pf = (_safe(game, "venue", "pf_runs") or 100)
    p -= (pf - 100) * 0.0015
    if pf != 100:
        notes.append(f"park factor {pf} → {(pf-100)*-0.0015*100:+.1f}% NRFI")
    p = _clip(p, 0.30, 0.85)
    return round(p, 4), notes


# ===========================================================================
# Bet sizing
# ===========================================================================

def confidence_from(grade_diff, edge):
    """Confidence calibrated from the bet-log analysis (2026-06-02).

    Key empirical finding: bets in the 9-10 confidence tier had a 30% win
    rate vs 51.7% in the 7-8 tier — the OLD formula was over-rewarding
    large edges, which correlated with the model being wrong. Now edge
    is capped at MAX_REASONABLE_EDGE=0.06 so edge_score tops out at 3.
    Combined with grade_score 0-3, max confidence is 4+3+3 = 10 only when
    BOTH a real grade gap AND a top-end edge are present.
    """
    abs_diff = abs(grade_diff)
    # Grade-gap sub-score (0-3)
    grade_score = (3 if abs_diff >= 18 else
                   2 if abs_diff >= 12 else
                   1 if abs_diff >=  6 else 0)
    # Edge sub-score (0-3) — calibrated so a 3%+ edge can clear MIN_CONFIDENCE
    # on its own (was requiring 3.5%), since the bet-log analysis shows the
    # 2.5-4% edge bucket is the model's most profitable zone.
    edge_score  = (3 if edge >= 0.045 else
                   2 if edge >= 0.025 else
                   1 if edge >= 0.018 else 0)
    # Both axes must contribute. Single-axis ceiling is 6.
    if grade_score == 0 or edge_score == 0:
        return int(_clip(4 + max(grade_score, edge_score), 1, 6))
    base = 4 + grade_score + edge_score
    return int(_clip(base, 1, 10))

def unit_size_from(edge, conf):
    for edge_floor, conf_floor, units, label in UNIT_LADDER:
        if edge >= edge_floor and conf >= conf_floor:
            return units, label
    return 0.0, "Pass"


# ===========================================================================
# Card factories per market
# ===========================================================================

def _build_reasoning(catscores, side):
    msgs = []
    for cat in ("pitching", "bullpen", "offense", "weather_park", "market", "injury_lineup"):
        s = catscores[cat]
        my, opp = (s.home, s.away) if side == "home" else (s.away, s.home)
        if my - opp >= 1.0:
            msgs.append(f"{cat.replace('_','/').title()} edge ({my:.1f} vs {opp:.1f})")
    for cat in ("pitching", "bullpen"):
        for n in catscores[cat].notes[:2]:
            if n: msgs.append(n)
    return msgs[:6]

def _default_pass(side="generic"):
    return [
        "Key bat scratched at lineup release",
        "Line moves through your fair value",
        "Weather forecast worsens (rain >50% or wind reversal)",
    ]

def make_ml_card(game, side, fair_prob, odds, cats, hg, ag):
    # Win-prob bias: don't bet teams we rate below MIN_TEAM_WIN_PROB to win.
    # Filters out the empirically-disastrous plus-money "trap" plays.
    if fair_prob < MIN_TEAM_WIN_PROB: return None
    price, book = _best_h2h_price(odds, side)
    if price is None: return None
    # Price range guard — no deep favorites or long dogs
    if price < MIN_AMERICAN_PRICE or price > MAX_AMERICAN_PRICE: return None
    edge = edge_pct(fair_prob, price)
    if edge < MIN_EDGE["moneyline"]: return None
    if edge > MAX_REASONABLE_EDGE: return None   # calibration sanity check
    diff = (hg - ag) if side == "home" else (ag - hg)
    conf = confidence_from(diff, edge)
    if conf < MIN_CONFIDENCE: return None
    units, risk = unit_size_from(edge, conf)
    if units == 0: return None
    return BetCard(
        bet_label=f"{game[side]['team_name']} ML",
        market="moneyline", side=side, book=book,
        price_american=price, line=None,
        fair_prob=fair_prob, fair_american=prob_to_american(fair_prob),
        edge=edge, confidence=conf, unit_size=units, risk=risk,
        reasoning=_build_reasoning(cats, side),
        pass_triggers=_default_pass(),
    )

def make_runline_card(game, side, win_prob, odds, cats, hg, ag):
    price, line, book = _best_runline_price(odds, side)
    if price is None: return None
    # Convert ML win prob to runline cover prob with a simple translation:
    # team -1.5 covers ~ win_prob × 0.55 (favorites win by 2+ ~half their wins)
    # team +1.5 covers ~ 1 - (1 - win_prob) × 0.55
    if line < 0:
        cover_p = win_prob * 0.55
    else:
        cover_p = 1 - (1 - win_prob) * 0.55
    cover_p = _clip(cover_p, 0.05, 0.95)
    if cover_p < MIN_TEAM_WIN_PROB: return None
    if price < MIN_AMERICAN_PRICE or price > MAX_AMERICAN_PRICE: return None
    edge = edge_pct(cover_p, price)
    if edge < MIN_EDGE["runline"]: return None
    if edge > MAX_REASONABLE_EDGE: return None
    diff = (hg - ag) if side == "home" else (ag - hg)
    conf = confidence_from(diff, edge)
    if conf < MIN_CONFIDENCE: return None
    units, risk = unit_size_from(edge, conf)
    if units == 0: return None
    sign = "-1.5" if line < 0 else "+1.5"
    return BetCard(
        bet_label=f"{game[side]['team_name']} {sign}",
        market="runline", side=side, book=book,
        price_american=price, line=line,
        fair_prob=cover_p, fair_american=prob_to_american(cover_p),
        edge=edge, confidence=conf, unit_size=units, risk=risk,
        reasoning=_build_reasoning(cats, side),
        pass_triggers=_default_pass(),
    )

def make_total_card(game, expected_total, odds, cats):
    out = []
    # Market-anchored side probabilities: use Pinnacle's devigged P(over)/P(under)
    # at the consensus line as the prior, then nudge based on (expected_total - line).
    # This keeps edges realistic and prevents the symmetric-inflation bug where
    # both over and under appeared +EV from a small expected-vs-line gap.
    prior_over, prior_line = _pinnacle_total_prob(odds, market_key="totals")
    if prior_line is None:
        return out   # no consensus line → no play (avoids alt-line hijack)
    # Plausibility guard: real MLB FG totals run ~6.5-12. If the API returns a
    # line outside that range, the matched event is probably a doubleheader
    # 7-inning game, F5 mislabeled as full-game, or an alt-line in disguise.
    # Skip — this is a data hygiene issue, not an edge.
    if not (6.0 <= prior_line <= 13.5):
        return out
    for side in ("over", "under"):
        price, line, book = _best_total_price(odds, side, market_key="totals",
                                              target_line=prior_line)
        if price is None or line is None: continue
        prior = prior_over if side == "over" else (1.0 - prior_over)
        sigma = 4.0
        # Convert "expected vs line" gap into a probability shift relative to prior
        z = (expected_total - line) / sigma if side == "over" \
            else (line - expected_total) / sigma
        # Map z to a small adjustment around prior (capped at ±5pp)
        adj = _clip(0.5 * math.erf(z / math.sqrt(2)) * 0.40, -0.05, 0.05)
        prob = _clip(prior + adj, 0.10, 0.90)
        edge = edge_pct(prob, price)
        if edge < MIN_EDGE["total"]: continue
        if edge > MAX_REASONABLE_EDGE: continue
        diff = abs(expected_total - line)
        conf = confidence_from(diff * 4, edge)
        if conf < MIN_CONFIDENCE: continue
        units, risk = unit_size_from(edge, conf)
        if units == 0: continue
        out.append(BetCard(
            bet_label=f"FG {side.capitalize()} {line}",
            market="total", side=side, book=book,
            price_american=price, line=line,
            fair_prob=prob, fair_american=prob_to_american(prob),
            edge=edge, confidence=conf, unit_size=units, risk=risk,
            reasoning=[
                f"Expected total {expected_total} vs market {line}",
                *cats["pitching"].notes[:2], *cats["weather_park"].notes[:2],
                *cats["bullpen"].notes[:1],
            ],
            pass_triggers=_default_pass(),
        ))
    return out

def make_f5_card(game, expected_f5, odds, cats):
    out = []
    prior_over, prior_line = _pinnacle_total_prob(odds, market_key="totals_1st_5_innings")
    if prior_line is None:
        return out
    # Plausibility guard: real F5 totals run ~3-7
    if not (2.5 <= prior_line <= 7.5):
        return out
    for side in ("over", "under"):
        price, line, book = _best_total_price(odds, side,
                                              market_key="totals_1st_5_innings",
                                              target_line=prior_line)
        if price is None or line is None: continue
        prior = prior_over if side == "over" else (1.0 - prior_over)
        sigma = 2.5
        z = (expected_f5 - line) / sigma if side == "over" \
            else (line - expected_f5) / sigma
        adj = _clip(0.5 * math.erf(z / math.sqrt(2)) * 0.50, -0.05, 0.05)
        prob = _clip(prior + adj, 0.10, 0.90)
        edge = edge_pct(prob, price)
        if edge < MIN_EDGE["f5_total"]: continue
        if edge > MAX_REASONABLE_EDGE: continue
        diff = abs(expected_f5 - line)
        conf = confidence_from(diff * 6, edge)   # tighter market = bigger conf swing per gap
        if conf < MIN_CONFIDENCE: continue
        units, risk = unit_size_from(edge, conf)
        if units == 0: continue
        out.append(BetCard(
            bet_label=f"F5 {side.capitalize()} {line}",
            market="f5_total", side=side, book=book,
            price_american=price, line=line,
            fair_prob=prob, fair_american=prob_to_american(prob),
            edge=edge, confidence=conf, unit_size=units, risk=risk,
            reasoning=[
                f"Expected F5 total {expected_f5} vs market {line}",
                *cats["pitching"].notes[:3],
                *cats["weather_park"].notes[:1],
            ],
            pass_triggers=_default_pass() + ["Either starter scratched"],
        ))
    return out

# Pitcher-prop config: higher edge band than ML/total because pitcher prop
# markets have more variance and the model produces a wider edge spread.
MIN_EDGE_PITCHER_PROP = 0.05      # 5%+ edge required (vs 1.8% for ML)
MAX_EDGE_PITCHER_PROP = 0.15      # 15% cap — beyond this = bad lambda, skip
MIN_PITCHER_STARTS    = 3         # need 3+ Statcast starts in window
MIN_PITCHER_PROJ      = {"pitcher_strikeouts": 3.0, "pitcher_walks": 0.5}


def _poisson_cdf_local(k: int, lam: float) -> float:
    """P(X <= k) for Poisson — iterative to avoid factorial overflow."""
    import math
    if lam <= 0: return 1.0 if k >= 0 else 0.0
    if k < 0: return 0.0
    s = 0.0
    term = math.exp(-lam)
    s += term
    for i in range(1, k + 1):
        term *= lam / i
        s += term
    return min(1.0, s)


def _devig_player_props(prop_event: dict, market_key: str, player_name: str,
                         target_line: float) -> tuple[float, list[tuple[str, int, int]]] | tuple[None, None]:
    """Pull every book's O/U on this player at the consensus line. Returns
    (median_devigged_P_over, [(book, over_price, under_price), ...]) for the
    target books only."""
    target = player_name.lower()
    offers = []   # (book, over_price, under_price) at target_line
    for b in prop_event.get("bookmakers", []):
        bk = b.get("key", "").lower()
        if bk not in TARGET_BOOKS + SHARP_ANCHORS: continue
        m = next((m for m in b.get("markets", []) if m["key"] == market_key), None)
        if not m: continue
        over = under = None
        for o in m.get("outcomes", []):
            if (o.get("description") or "").lower() != target: continue
            pt = o.get("point")
            if pt is None or abs(float(pt) - target_line) > 0.001: continue
            if (o.get("name") or "").lower() == "over":  over = int(o["price"])
            elif (o.get("name") or "").lower() == "under": under = int(o["price"])
        if over is None or under is None: continue
        offers.append((bk, over, under))
    if not offers: return None, None
    # Pinnacle-priority devig
    pin = [o for o in offers if o[0] in SHARP_ANCHORS]
    if pin:
        bk, op, up = pin[0]
        fo, _ = devig_two_way(op, up)
        return fo, offers
    # Median across user books
    devigged = []
    for bk, op, up in offers:
        if bk not in TARGET_BOOKS: continue
        fo, _ = devig_two_way(op, up)
        devigged.append(fo)
    if not devigged: return None, offers
    devigged.sort()
    return devigged[len(devigged) // 2], offers


# Pitcher-prop verification gates — shared by the real-bet pipeline
# (make_pitcher_prop_card) and the website board builder
# (build_site.build_rich_pitcher_prop) so a board never appears for a pitcher
# whose projection would have been filtered out for a real bet.
PROP_FRESHNESS_DAYS = 14          # most-recent start must be within N days
PROP_RECENT_WINDOW  = 5           # how many recent starts define "recent actuals"
PROP_PLAUSIBILITY = {             # market_key -> (recent_field, lo_mult, hi_mult)
    "pitcher_strikeouts": ("strikeouts", 0.4, 2.5),
    "pitcher_walks":      ("walks",      0.3, 3.0),
}


def pitcher_prop_passes_gates(game: dict, side: str, market_key: str, lam: float,
                              today: date | None = None) -> bool:
    """Sanity-check a pitcher's data before emitting a K/BB prop.

    1. Freshness: most-recent start within PROP_FRESHNESS_DAYS.
    2. Plausibility: lambda within [lo_mult, hi_mult] x the average of the
       pitcher's last PROP_RECENT_WINDOW actuals — filters hot/cold
       extrapolations from one anomalous start.

    Returns False (skip) on missing, stale, or implausible data.
    """
    prof = ((game or {}).get(side) or {}).get("pitcher_profile") or {}
    starts_list = prof.get("starts") or []
    if not starts_list:
        return False
    today = today or date.today()
    try:
        last_date = date.fromisoformat(str(starts_list[0].get("game_date", ""))[:10])
    except ValueError:
        return False
    if (today - last_date).days > PROP_FRESHNESS_DAYS:
        return False
    spec = PROP_PLAUSIBILITY.get(market_key)
    if spec:
        recent_field, lo_mult, hi_mult = spec
        vals = [s.get(recent_field) for s in starts_list[:PROP_RECENT_WINDOW]
                if s.get(recent_field) is not None]
        if len(vals) >= 2:
            avg_recent = sum(vals) / len(vals)
            if avg_recent > 0 and (lam > hi_mult * avg_recent or lam < lo_mult * avg_recent):
                return False
    return True


def pitcher_prop_confidence(edge: float, starts: int) -> int:
    """1-10 confidence for a pitcher prop, driven by edge and sample size.
    Shared with build_site so the board's unit count matches the real bet."""
    if   edge >= 0.10: conf_e = 4
    elif edge >= 0.07: conf_e = 3
    elif edge >= 0.05: conf_e = 2
    else: conf_e = 1
    sample_score = 2 if starts >= 8 else (1 if starts >= 5 else 0)
    return int(_clip(4 + conf_e + sample_score, 1, 10))


def make_pitcher_prop_card(game: dict, side: str, pitcher_proj: dict,
                            prop_event: dict, market_key: str) -> BetCard | None:
    """Generate a real-bet card from a pitcher prop projection (K or BB).

    Filters:
      - data_quality must be 'ok' (3+ starts in Statcast window)
      - projection >= market-specific minimum
      - per-book confirmation (require ≥1 OTHER target book within 12 cents)
      - edge ∈ [MIN_EDGE_PITCHER_PROP, MAX_REASONABLE_EDGE]
    """
    import math
    if not prop_event: return None
    if (pitcher_proj or {}).get("data_quality") != "ok": return None
    starts = pitcher_proj.get("starts_in_window") or 0
    if starts < MIN_PITCHER_STARTS: return None

    player_name = pitcher_proj.get("name")
    player_id   = pitcher_proj.get("id")
    if not (player_name and player_id): return None

    if market_key == "pitcher_strikeouts":
        lam = pitcher_proj.get("projected_k")
    elif market_key == "pitcher_walks":
        lam = pitcher_proj.get("projected_walks")
    else:
        return None
    if not lam or lam < MIN_PITCHER_PROJ.get(market_key, 0.5): return None

    # Verification gates — freshness + projection plausibility. Shared with
    # build_site.build_rich_pitcher_prop so the website board matches the
    # real-bet decision exactly.
    if not pitcher_prop_passes_gates(game, side, market_key, lam):
        return None

    # Find consensus line (mode across all books carrying this player's market)
    target = (player_name or "").lower()
    line_counts: dict[float, int] = {}
    for b in prop_event.get("bookmakers", []):
        m = next((m for m in b.get("markets", []) if m["key"] == market_key), None)
        if not m: continue
        seen_for_book: set[float] = set()
        for o in m.get("outcomes", []):
            if (o.get("description") or "").lower() != target: continue
            pt = o.get("point")
            if pt is None: continue
            seen_for_book.add(float(pt))
        for v in seen_for_book: line_counts[v] = line_counts.get(v, 0) + 1
    if not line_counts: return None
    consensus_line = max(line_counts.items(), key=lambda kv: kv[1])[0]

    # Plausibility guard
    if market_key == "pitcher_strikeouts" and not (2.5 <= consensus_line <= 12.5): return None
    if market_key == "pitcher_walks"      and not (0.5 <= consensus_line <= 5.5):  return None

    # Devigged P(over) at consensus line + per-book offers
    market_over, offers = _devig_player_props(prop_event, market_key, player_name, consensus_line)
    if market_over is None: return None

    # Two-book confirmation — require ≥2 target books on this line
    book_offers = [(bk, op, up) for bk, op, up in offers if bk in TARGET_BOOKS]
    if len(book_offers) < 2: return None

    # Raw Poisson side probabilities
    k_floor = int(consensus_line)
    poisson_over = 1.0 - _poisson_cdf_local(k_floor, lam)

    # Market-anchored side prob: nudge market prior by capped delta
    side_target = "over" if poisson_over >= 0.5 else "under"
    market_side = market_over if side_target == "over" else (1.0 - market_over)
    model_side  = poisson_over if side_target == "over" else (1.0 - poisson_over)
    shift = _clip(model_side - 0.5, -0.06, 0.06)
    our_prob = _clip(market_side + shift, 0.05, 0.95)

    # Best price across target books for our side
    best_book, best_price = None, None
    for bk, op, up in book_offers:
        price = op if side_target == "over" else up
        if best_price is None or price > best_price:
            best_price, best_book = price, bk
    if best_price is None or best_book is None: return None
    if best_price < MIN_AMERICAN_PRICE or best_price > MAX_AMERICAN_PRICE: return None

    # Edge + Kelly — use prop-specific cap (not the tighter ML/total cap)
    edge = edge_pct(our_prob, best_price)
    if edge < MIN_EDGE_PITCHER_PROP: return None
    if edge > MAX_EDGE_PITCHER_PROP:  return None

    # Confidence — driven primarily by edge and sample size
    conf = pitcher_prop_confidence(edge, starts)
    if conf < MIN_CONFIDENCE: return None

    units, risk = unit_size_from(edge, conf)
    if units == 0: return None

    # Build label like "Jeffrey Springs Under 4.5 K" or "... Under 2.5 BB"
    unit_tag = "K" if market_key == "pitcher_strikeouts" else "BB"
    label = f"{player_name} {side_target.capitalize()} {consensus_line} {unit_tag}"

    reasoning = [
        f"Model {market_key.replace('_',' ')} projection {lam:.2f} {unit_tag} vs line {consensus_line}",
        f"P({side_target} {consensus_line}) = {our_prob*100:.1f}% · market {market_side*100:.1f}%",
        f"{starts} starts in 30-day Statcast window",
    ]
    if pitcher_proj.get("opp_lineup_k_pct"):
        reasoning.append(f"Opp lineup K-rate: {pitcher_proj['opp_lineup_k_pct']*100:.1f}%")
    if pitcher_proj.get("catcher_framing_bump"):
        reasoning.append(f"Catcher framing bump: {pitcher_proj['catcher_framing_bump']:+.2f} K")

    return BetCard(
        bet_label=label,
        market=market_key, side=side_target, book=best_book,
        price_american=best_price, line=consensus_line,
        fair_prob=our_prob, fair_american=prob_to_american(our_prob),
        edge=edge, confidence=conf, unit_size=units, risk=risk,
        reasoning=reasoning,
        pass_triggers=["Starter scratched / late lineup change",
                        "Line moves through your fair value",
                        "Rain delay / shortened game risk"],
        player_id=player_id, player_name=player_name,
    )


def make_nrfi_card(game, nrfi_prob, nrfi_notes, odds):
    """The NRFI/YRFI market on most US books is published as a 1st-inning
    total at 0.5 runs.  Under 0.5 = NRFI, Over 0.5 = YRFI."""
    out = []
    for label, side, our_prob in (("NRFI", "under", nrfi_prob),
                                  ("YRFI", "over", 1 - nrfi_prob)):
        price, line, book = _best_total_price(odds, side,
                                              market_key="totals_1st_1_innings",
                                              target_line=0.5)
        if price is None or line is None:
            continue
        edge = edge_pct(our_prob, price)
        if edge < MIN_EDGE["nrfi"]: continue
        if edge > MAX_REASONABLE_EDGE: continue
        # Confidence from how far our prob is from 50/50 + edge size
        conf = confidence_from(abs(our_prob - 0.5) * 30, edge)
        if conf < MIN_CONFIDENCE: continue
        units, risk = unit_size_from(edge, conf)
        if units == 0: continue
        out.append(BetCard(
            bet_label=label,
            market="nrfi", side=label.lower(), book=book,
            price_american=price, line=line,
            fair_prob=our_prob, fair_american=prob_to_american(our_prob),
            edge=edge, confidence=conf, unit_size=units, risk=risk,
            reasoning=nrfi_notes + [f"Our NRFI prob {nrfi_prob:.1%}"],
            pass_triggers=["Top of opposing lineup changes",
                           "Either starter throws unusually short pregame bullpen"],
        ))
    return out


# ===========================================================================
# Markdown rendering
# ===========================================================================

def render_card_md(game, card, idx):
    away = game["away"]["team_name"]; home = game["home"]["team_name"]
    when = game.get("gameDate", "")
    line_str = f" (line {card.line})" if card.line is not None else ""
    reasoning = "\n".join(f"- {r}" for r in card.reasoning) or "- (no notes)"
    triggers = "\n".join(f"- {t}" for t in card.pass_triggers)
    return f"""### Bet #{idx} — {card.bet_label}

| Field | Value |
|---|---|
| Game | {away} @ {home} ({when}) |
| Market | {card.market} |
| Best Book | {card.book.upper()} {card.price_american:+d}{line_str} |
| Fair Odds | {card.fair_american:+d} ({card.fair_prob:.1%}) |
| Edge | {card.edge*100:.2f}% |
| Confidence | {card.confidence}/10 |
| Risk | {card.risk} |
| Unit Size | {card.unit_size}u |

**Reasoning**

{reasoning}

**Pass triggers**

{triggers}

---
"""

def render_no_play(game, grades, exp_total, exp_f5, nrfi_p):
    away = game["away"]["team_name"]; home = game["home"]["team_name"]
    return (f"### {away} @ {home} — NO PLAY\n\n"
            f"Grade H{grades['home']} / A{grades['away']} | "
            f"FG xRuns {exp_total} | F5 xRuns {exp_f5} | NRFI {nrfi_p:.1%}\n"
            f"No bet cleared edge + confidence thresholds.\n")


# ===========================================================================
# Driver
# ===========================================================================

def grade_one_game(game, odds_for_game):
    cats = {
        "pitching":      grade_pitching(game),
        "bullpen":       grade_bullpen(game),
        "offense":       grade_offense(game),
        "weather_park":  grade_weather_park(game),
        "market":        grade_market(game, odds_for_game),
        "situational":   grade_situational(game),
        "injury_lineup": grade_injury_lineup(game),
    }
    totals = total_grade(cats)
    win_p  = grade_to_win_prob(totals["home"], totals["away"], odds_for_game)
    exp_t  = expected_total_runs(game, cats, odds_for_game)
    exp_f5 = expected_f5_total(game, cats, odds_for_game)
    nrfi_p, nrfi_notes = estimate_nrfi_prob(game, cats, odds_for_game)

    cards: list[BetCard] = []
    if odds_for_game:
        if ENABLED_MARKETS.get("moneyline", True):
            for side in ("home", "away"):
                c = make_ml_card(game, side, win_p[side], odds_for_game, cats, totals["home"], totals["away"])
                if c: cards.append(c)
        if ENABLED_MARKETS.get("runline", False):
            for side in ("home", "away"):
                r = make_runline_card(game, side, win_p[side], odds_for_game, cats, totals["home"], totals["away"])
                if r: cards.append(r)
        if ENABLED_MARKETS.get("total", True):
            cards.extend(make_total_card(game, exp_t, odds_for_game, cats))
        if ENABLED_MARKETS.get("f5_total", True):
            cards.extend(make_f5_card(game, exp_f5, odds_for_game, cats))
        if ENABLED_MARKETS.get("nrfi", True):
            cards.extend(make_nrfi_card(game, nrfi_p, nrfi_notes, odds_for_game))

    # Pitcher prop cards (K + BB) — need prop_odds.json for the event.
    # The grader doesn't have direct access; assume mlb_grader is invoked
    # from run() which loads prop_odds.json and re-injects via game["_prop_event"].
    prop_event = game.get("_prop_event")
    if prop_event:
        # tracked_props is already computed below; recompute pitcher projections via prop_tracking
        ump_delta, _ = _umpire_run_delta(game)
        tp_prelim = build_tracked_props(game, ump_run_delta=ump_delta)
        if ENABLED_MARKETS.get("pitcher_strikeouts", True):
            for pp in tp_prelim.get("pitcher_ks", []):
                c = make_pitcher_prop_card(game, pp.get("side"), pp, prop_event, "pitcher_strikeouts")
                if c: cards.append(c)
        if ENABLED_MARKETS.get("pitcher_walks", True):
            for pp in tp_prelim.get("pitcher_walks", []):
                c = make_pitcher_prop_card(game, pp.get("side"), pp, prop_event, "pitcher_walks")
                if c: cards.append(c)

    # Per-game cap — applied PER POOL so a pitcher prop and a regular bet on
    # the same game don't compete. Regular markets keep the single best-edge
    # card per game (MAX_CARDS_PER_GAME / MAX_UNITS_PER_GAME); prop cards pass
    # through here and are deduped per-pitcher and pool-capped in run().
    cards.sort(key=lambda c: (-c.edge, -c.confidence))
    capped: list[BetCard] = []
    reg_count = 0
    reg_units = 0.0
    for c in cards:
        if c.market in PITCHER_PROP_MARKETS:
            capped.append(c)
            continue
        if reg_count >= MAX_CARDS_PER_GAME: continue
        if reg_units + c.unit_size > MAX_UNITS_PER_GAME: continue
        capped.append(c); reg_count += 1; reg_units += c.unit_size

    # Tracked props (Phase 1: data tracking only, no bets fired from these)
    ump_delta, _ = _umpire_run_delta(game)
    tracked_props = build_tracked_props(game, ump_run_delta=ump_delta)

    return {
        "gamePk": game["gamePk"],
        "matchup": f'{game["away"]["team_name"]} @ {game["home"]["team_name"]}',
        "gameDate": game["gameDate"],
        "categories": {k: asdict(v) for k, v in cats.items()},
        "grade": totals, "win_prob": win_p,
        "expected_total": exp_t, "expected_f5_total": exp_f5,
        "nrfi_prob": nrfi_p,
        "bet_cards": [asdict(c) for c in capped],
        "tracked_props": tracked_props,
    }

def match_odds(odds_root, game):
    """Match the game's odds entry. Picks the event whose commence_time is
    closest to the game's scheduled first pitch — the Odds API can return
    multiple matches for the same teams (today's game + tomorrow's game in
    a series), and we don't want to grade against tomorrow's lines."""
    if not odds_root or not odds_root.get("available"): return None
    away = game["away"]["team_name"]; home = game["home"]["team_name"]
    target = game.get("gameDate")
    candidates = [og for og in odds_root.get("games", [])
                  if og.get("home_team") == home and og.get("away_team") == away]
    if not candidates:
        return None
    if not target or len(candidates) == 1:
        return candidates[0]
    # Pick the candidate whose commence_time is closest to target
    from datetime import datetime
    try:
        t = datetime.fromisoformat(target.replace("Z", "+00:00"))
    except Exception:
        return candidates[0]
    def _score(og):
        ct = og.get("commence_time")
        if not ct: return float("inf")
        try:
            return abs((datetime.fromisoformat(ct.replace("Z", "+00:00")) - t).total_seconds())
        except Exception:
            return float("inf")
    return min(candidates, key=_score)


def run(target, data_root):
    day_dir = data_root / target.isoformat()
    games_dir = day_dir / "games"
    if not games_dir.exists():
        print(f"[error] no scraper data at {games_dir}. Run mlb_data_scraper.py first.")
        sys.exit(1)
    odds_path = day_dir / "odds.json"
    odds_root = _load(odds_path) if odds_path.exists() else None
    # Detect a real data outage: no odds file, or the scraper flagged the feed
    # unavailable, or it returned zero games. Without market prices the model has
    # nothing to compute an edge against, so EVERY game is forced to "no play."
    # That must NOT be rendered as a disciplined NO PLAYS — flag it loudly.
    odds_outage = (
        odds_root is None
        or odds_root.get("available") is False
        or not (odds_root.get("games") or [])
    )
    prop_odds_path = day_dir / "prop_odds.json"
    prop_odds_root = _load(prop_odds_path) if prop_odds_path.exists() else None
    # Map prop events by team-pair for fast lookup
    prop_by_pair: dict = {}
    if prop_odds_root:
        for _eid, ev in (prop_odds_root.get("events") or {}).items():
            prop_by_pair[(ev.get("home_team"), ev.get("away_team"))] = ev

    # First pass: grade every game (each is already capped to MAX_CARDS_PER_GAME=1)
    grades_out: list[dict] = []
    all_candidates: list[tuple[dict, dict]] = []   # (game, card) tuples
    for gp in sorted(games_dir.glob("*.json")):
        game = _load(gp)
        odds = match_odds(odds_root, game) if odds_root else None
        # Inject the prop event so grade_one_game can fire pitcher prop cards
        game["_prop_event"] = prop_by_pair.get(
            (game["home"]["team_name"], game["away"]["team_name"])
        )
        graded = grade_one_game(game, odds)
        grades_out.append(graded)
        for c in graded["bet_cards"]:
            all_candidates.append((game, c))

    # Sort candidates by edge × confidence, then split into REGULAR vs PROPS
    # pools so a heavy prop slate doesn't squeeze out the regular picks.
    all_candidates.sort(key=lambda gc: -(gc[1]["edge"] * gc[1]["confidence"]))

    regular_candidates = [(g, c) for g, c in all_candidates if c["market"] not in PITCHER_PROP_MARKETS]
    prop_candidates    = [(g, c) for g, c in all_candidates if c["market"] in PITCHER_PROP_MARKETS]

    # Per-game lock applies to the REGULAR pool only — props don't compete
    # for the same per-game slot as a ML/total pick.
    chosen_regular: list[tuple[dict, dict]] = []
    regular_game_pks: set[int] = set()
    reg_units = 0.0
    for game, card in regular_candidates:
        if len(chosen_regular) >= MAX_CARDS_PER_SLATE: break
        if reg_units + card["unit_size"] > MAX_UNITS_PER_SLATE: continue
        if game["gamePk"] in regular_game_pks: continue   # 1 regular per game
        chosen_regular.append((game, card))
        regular_game_pks.add(game["gamePk"])
        reg_units += card["unit_size"]

    # Props get their own pool with their own caps. Two prop bets per pitcher
    # rarely happen (would need both K and BB to qualify), but cap at 1 per
    # pitcher to avoid stacking on one arm.
    chosen_props: list[tuple[dict, dict]] = []
    prop_pitcher_ids: set = set()
    prop_units = 0.0
    for game, card in prop_candidates:
        if len(chosen_props) >= MAX_PROP_CARDS_PER_SLATE: break
        if prop_units + card["unit_size"] > MAX_PROP_UNITS_PER_SLATE: continue
        pid = card.get("player_id")
        if pid is None or pid in prop_pitcher_ids: continue   # 1 prop per pitcher; drop id-less
        chosen_props.append((game, card))
        prop_pitcher_ids.add(pid)
        prop_units += card["unit_size"]

    chosen = chosen_regular + chosen_props
    chosen_game_pks = regular_game_pks | {g["gamePk"] for g, _ in chosen_props}
    total_units = reg_units + prop_units

    # Mutate grades_out so games NOT in the chosen set show empty bet_cards
    chosen_pks = {pk for pk in chosen_game_pks}
    chosen_pairs = {(game["gamePk"], c["bet_label"]): True for game, c in chosen}
    for g in grades_out:
        if g["gamePk"] not in chosen_pks:
            g["bet_cards"] = []
        else:
            g["bet_cards"] = [c for c in g["bet_cards"]
                              if (g["gamePk"], c["bet_label"]) in chosen_pairs]

    # Render markdown — regular and props rendered in separate sections so
    # the user can scan them as distinct streams.
    md = [
        f"# MLB Sharp Betting Cards — {target.isoformat()}\n",
        f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M %Z')}_  ",
        f"_Books shopped: {', '.join(b.upper() for b in TARGET_BOOKS)}_  ",
        f"_Caps: regular {MAX_CARDS_PER_SLATE} / {MAX_UNITS_PER_SLATE}u · "
        f"props {MAX_PROP_CARDS_PER_SLATE} / {MAX_PROP_UNITS_PER_SLATE}u_\n",
    ]
    bet_count = 0
    if odds_outage and not chosen:
        reason = "odds.json missing" if odds_root is None else \
                 "; ".join((odds_root or {}).get("errors") or ["feed returned no games"])
        # Never leak an API key into the committed card, even if an older
        # odds.json still embeds one in its stored error URLs.
        reason = re.sub(r"(apiKey=)[^&\s]+", r"\1***", reason)
        md.append(
            "## ⚠️ DATA OUTAGE — odds feed unavailable, NOT a model no-play.\n\n"
            f"_{len(grades_out)} games graded on fundamentals, but **no market odds were "
            f"available** to compute edges against, so no bets could be evaluated. "
            f"This is an upstream data problem (likely API quota/auth), not the model "
            f"finding no edge._\n\n"
            f"_Reason: {reason}_\n"
        )
    elif not chosen:
        md.append(f"## NO PLAYS — {len(grades_out)} games graded, none cleared the filters.\n")
    else:
        if chosen_regular:
            md.append(f"## 🎯 GAME PICKS · {len(chosen_regular)} play(s) · {reg_units:.1f}u\n")
            for game, card in chosen_regular:
                bet_count += 1
                md.append(render_card_md(game, BetCard(**card), bet_count))
        if chosen_props:
            md.append(f"\n## ⚾ PITCHER PROPS · {len(chosen_props)} play(s) · {prop_units:.1f}u\n")
            for game, card in chosen_props:
                bet_count += 1
                md.append(render_card_md(game, BetCard(**card), bet_count))

    # Append the no-play summary table for context
    md.append(f"\n## Other graded games (no play)\n")
    for g in grades_out:
        if g["bet_cards"]: continue
        md.append(f"- **{g['matchup']}** · grade H{g['grade']['home']}/A{g['grade']['away']} · "
                  f"xRuns {g['expected_total']} · F5 {g['expected_f5_total']} · "
                  f"NRFI {g['nrfi_prob']:.1%}")

    md.append(f"\n_Total exposure today: **{total_units:.1f}u** across **{bet_count}** bets._\n")

    grades_path = day_dir / "grades.json"
    cards_path = day_dir / "cards.md"
    grades_path.write_text(json.dumps(grades_out, indent=2, default=str))
    cards_path.write_text("\n".join(md))

    # Prop tracking (Phase 1: paper only, no bets fired). Written so we can
    # eyeball data freshness day-over-day before turning on prop betting.
    try:
        prop_md = render_props_md(grades_out, target.isoformat())
        prop_path = day_dir / "prop_tracking.md"
        prop_path.write_text(prop_md)
        print(f"       props  → {prop_path}")
    except Exception as e:
        print(f"       [warn] prop_tracking render failed: {e}")

    # Phase 2: paper-trading prop cards. Generates "would-have-bet" rows from
    # model projection × market line, appends to prop_paper_log.csv. NOT a
    # real bet — separate log, separate Discord section.
    try:
        from paper_props import generate_paper_cards, append_paper_log
        prop_odds_path = day_dir / "prop_odds.json"
        if prop_odds_path.exists():
            prop_odds = json.loads(prop_odds_path.read_text())
            paper_cards = generate_paper_cards(grades_out, prop_odds)
            added = append_paper_log(data_root, target.isoformat(), paper_cards)
            print(f"       paper  → {added} paper prop card(s) (of {len(paper_cards)} candidates)")
    except Exception as e:
        print(f"       [warn] paper-props generation failed: {e}")

    print(f"[done] {len(grades_out)} games graded, {bet_count} cards ({total_units:.1f}u total)")
    print(f"       grades → {grades_path}")
    print(f"       cards  → {cards_path}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="MLB Sharp Betting grader")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--data-root", default="./mlb_data")
    args = ap.parse_args(argv)
    target = date.fromisoformat(args.date) if args.date else date.today()
    run(target, Path(args.data_root).expanduser().resolve())
    return 0

if __name__ == "__main__":
    sys.exit(main())
