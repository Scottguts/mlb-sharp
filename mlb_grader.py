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
import sys
from dataclasses import dataclass, asdict, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from mlb_data_scraper import (
    american_to_prob, prob_to_american, devig_two_way, edge_pct,
    TARGET_BOOKS, SHARP_ANCHORS,
)


# ===========================================================================
# CONFIG — tune these without touching logic
# ===========================================================================

# Category weights (must sum to 100)
WEIGHTS = {
    "pitching":      25,
    "bullpen":       15,
    "offense":       15,
    "weather_park":  10,
    "market":        15,
    "situational":   10,
    "injury_lineup": 10,
}

# Win-prob model parameters
LEAGUE_AVG_TOTAL = 8.6     # baseline runs per game (refresh annually)
HOME_FIELD_PROB  = 0.035   # home edge as a probability bump
GRADE_TO_PROB    = 0.010   # 1% win prob per 1 grade-point edge
MAX_PROB_SHIFT   = 0.20    # cap model output relative to base

# F5 model parameters (no bullpen contribution)
F5_LEAGUE_AVG    = 4.4     # baseline F5 runs per game

# NRFI model parameters
LEAGUE_NRFI_RATE = 0.585   # ~58.5% of MLB games have a scoreless 1st (2023-24)

# Minimum edge to publish a bet card by market type
MIN_EDGE = {
    "moneyline":  0.030,
    "runline":    0.030,
    "total":      0.030,
    "f5_total":   0.035,
    "nrfi":       0.035,
}

# Confidence floor — never publish a card below this
MIN_CONFIDENCE = 5

# Unit sizing rules. 1u = 1% of bankroll.
# (edge_floor, confidence_floor, units, risk_label)
UNIT_LADDER = [
    (0.080, 9, 2.0, "Max"),       # rare max play
    (0.060, 7, 1.5, "Strong"),
    (0.040, 6, 1.0, "Standard"),
    (0.030, 5, 0.5, "Lean"),
]

# Hard caps
MAX_BETS_PER_SLATE     = 8       # never expose more than 8u in action on a day
MAX_UNITS_PER_GAME     = 2.0     # never more than 2u on a single game
ALLOW_PARLAYS          = False   # built-in for now: singles only


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
    market: str               # moneyline / runline / total / f5_total / nrfi
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

        out[side] = _clip(s, 0, 10)
    return CategoryScore(home=out["home"], away=out["away"], notes=notes)


def grade_bullpen(game: dict) -> CategoryScore:
    notes: list[str] = []
    out = {}
    for side in ("home", "away"):
        pen = _safe(game, side, "bullpen_usage", "relievers") or {}
        if not pen:
            out[side] = 5.0
            notes.append(f"{side}: bullpen data missing — neutral 5")
            continue
        s = 6.0
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
    wind = wx.get("wind_mph")
    if temp is not None:
        if temp >= 80: notes.append(f"warm ({temp}°F) — ball carries")
        elif temp <= 55: notes.append(f"cold ({temp}°F) — ball dies")
    if wind is not None and wind >= 12:
        notes.append(f"breezy ({wind} mph) — direction matters")
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

def _starter_throw_hand(profile): return None  # extension hook

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
    for b in _book_iter(odds_for_game):
        h2h = next((m for m in b.get("markets", []) if m["key"] == "h2h"), None)
        if not h2h: continue
        for o in h2h["outcomes"]:
            if o["name"] == target:
                p = int(o["price"])
                if best_price is None or p > best_price:
                    best_price, best_book = p, b["key"]
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

def _best_total_price(odds_for_game, side, market_key="totals"):
    best = (None, None, "")
    for b in _book_iter(odds_for_game):
        t = next((m for m in b.get("markets", []) if m["key"] == market_key), None)
        if not t: continue
        for o in t["outcomes"]:
            if o["name"].lower() != side.lower(): continue
            p, line = int(o["price"]), float(o.get("point", 0))
            if best[0] is None or p > best[0]:
                best = (p, line, b["key"])
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

def grade_to_win_prob(home_grade, away_grade):
    diff = home_grade - away_grade
    shift = _clip(diff * GRADE_TO_PROB, -MAX_PROB_SHIFT, MAX_PROB_SHIFT)
    h = _clip(0.5 + shift + HOME_FIELD_PROB, 0.05, 0.95)
    return {"home": round(h, 4), "away": round(1 - h, 4)}

def expected_total_runs(game, catscores):
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
    return round(base, 2)

def expected_f5_total(game, catscores):
    """F5 is mostly the two starters; bullpens barely play. Park + weather
    still matter, but we drop the bullpen-quality term entirely."""
    pf = (_safe(game, "venue", "pf_runs") or 100) / 100.0
    base = F5_LEAGUE_AVG * pf
    wx = game.get("weather") or {}
    if not wx.get("indoor", False):
        temp = wx.get("temp_f")
        if temp is not None: base += (temp - 70) * 0.010
    avg_pitch = (catscores["pitching"].home + catscores["pitching"].away) / 2.0
    base -= (avg_pitch - 5) * 0.30      # pitching matters MORE in F5
    return round(base, 2)

def estimate_nrfi_prob(game, catscores) -> tuple[float, list[str]]:
    """Estimate prob of a scoreless 1st inning.

    Approach: start from league NRFI rate, adjust by:
      - quality of both starters (pitching grade)
      - park run factor
      - top-of-order quality (proxy: lineup confirmed + platoon edge in offense grade)
    """
    notes: list[str] = []
    p = LEAGUE_NRFI_RATE
    avg_pitch = (catscores["pitching"].home + catscores["pitching"].away) / 2.0
    p += (avg_pitch - 5) * 0.020       # +/- 2% per grade pt vs avg
    notes.append(f"avg pitching grade {avg_pitch:.1f} → {('+' if avg_pitch>=5 else '')}{(avg_pitch-5)*0.02*100:+.1f}% NRFI")
    pf = (_safe(game, "venue", "pf_runs") or 100)
    p -= (pf - 100) * 0.0015           # hitter park = lower NRFI
    if pf != 100:
        notes.append(f"park factor {pf} → {(pf-100)*-0.0015*100:+.1f}% NRFI")
    avg_off = (catscores["offense"].home + catscores["offense"].away) / 2.0
    p -= (avg_off - 5) * 0.012
    p = _clip(p, 0.30, 0.85)
    return round(p, 4), notes


# ===========================================================================
# Bet sizing
# ===========================================================================

def confidence_from(grade_diff, edge):
    base = 5
    if abs(grade_diff) >= 15: base += 2
    elif abs(grade_diff) >= 8: base += 1
    if edge >= 0.07: base += 2
    elif edge >= 0.05: base += 1
    elif edge < 0.03: base -= 1
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
    price, book = _best_h2h_price(odds, side)
    if price is None: return None
    edge = edge_pct(fair_prob, price)
    if edge < MIN_EDGE["moneyline"]: return None
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
    edge = edge_pct(cover_p, price)
    if edge < MIN_EDGE["runline"]: return None
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
    for side in ("over", "under"):
        price, line, book = _best_total_price(odds, side, market_key="totals")
        if price is None or line is None: continue
        sigma = 4.0
        z = (line + 0.5 - expected_total) / sigma if side == "under" \
            else (expected_total - line + 0.5) / sigma
        prob = _clip(0.5 * (1 + math.erf(z / math.sqrt(2))), 0.10, 0.90)
        edge = edge_pct(prob, price)
        if edge < MIN_EDGE["total"]: continue
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
    for side in ("over", "under"):
        price, line, book = _best_total_price(odds, side, market_key="totals_1st_5_innings")
        if price is None or line is None: continue
        # F5 has tighter variance — sigma ~ 2.5 runs
        sigma = 2.5
        z = (line + 0.5 - expected_f5) / sigma if side == "under" \
            else (expected_f5 - line + 0.5) / sigma
        prob = _clip(0.5 * (1 + math.erf(z / math.sqrt(2))), 0.10, 0.90)
        edge = edge_pct(prob, price)
        if edge < MIN_EDGE["f5_total"]: continue
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

def make_nrfi_card(game, nrfi_prob, nrfi_notes, odds):
    """The NRFI/YRFI market on most US books is published as a 1st-inning
    total at 0.5 runs.  Under 0.5 = NRFI, Over 0.5 = YRFI."""
    out = []
    for label, side, our_prob in (("NRFI", "under", nrfi_prob),
                                  ("YRFI", "over", 1 - nrfi_prob)):
        price, line, book = _best_total_price(odds, side, market_key="totals_1st_1_innings")
        if price is None or line is None or abs(line - 0.5) > 0.01:
            continue
        edge = edge_pct(our_prob, price)
        if edge < MIN_EDGE["nrfi"]: continue
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
    win_p  = grade_to_win_prob(totals["home"], totals["away"])
    exp_t  = expected_total_runs(game, cats)
    exp_f5 = expected_f5_total(game, cats)
    nrfi_p, nrfi_notes = estimate_nrfi_prob(game, cats)

    cards: list[BetCard] = []
    if odds_for_game:
        for side in ("home", "away"):
            c = make_ml_card(game, side, win_p[side], odds_for_game, cats, totals["home"], totals["away"])
            if c: cards.append(c)
            r = make_runline_card(game, side, win_p[side], odds_for_game, cats, totals["home"], totals["away"])
            if r: cards.append(r)
        cards.extend(make_total_card(game, exp_t, odds_for_game, cats))
        cards.extend(make_f5_card(game, exp_f5, odds_for_game, cats))
        cards.extend(make_nrfi_card(game, nrfi_p, nrfi_notes, odds_for_game))

    # Per-game cap
    cards.sort(key=lambda c: c.edge, reverse=True)
    capped: list[BetCard] = []
    units_so_far = 0.0
    for c in cards:
        if units_so_far + c.unit_size > MAX_UNITS_PER_GAME: continue
        capped.append(c); units_so_far += c.unit_size

    return {
        "gamePk": game["gamePk"],
        "matchup": f'{game["away"]["team_name"]} @ {game["home"]["team_name"]}',
        "gameDate": game["gameDate"],
        "categories": {k: asdict(v) for k, v in cats.items()},
        "grade": totals, "win_prob": win_p,
        "expected_total": exp_t, "expected_f5_total": exp_f5,
        "nrfi_prob": nrfi_p,
        "bet_cards": [asdict(c) for c in capped],
    }

def match_odds(odds_root, game):
    if not odds_root or not odds_root.get("available"): return None
    away = game["away"]["team_name"]; home = game["home"]["team_name"]
    for og in odds_root.get("games", []):
        if og.get("home_team") == home and og.get("away_team") == away:
            return og
    return None


def run(target, data_root):
    day_dir = data_root / target.isoformat()
    games_dir = day_dir / "games"
    if not games_dir.exists():
        print(f"[error] no scraper data at {games_dir}. Run mlb_data_scraper.py first.")
        sys.exit(1)
    odds_path = day_dir / "odds.json"
    odds_root = _load(odds_path) if odds_path.exists() else None

    grades_out: list[dict] = []
    md = [
        f"# MLB Sharp Betting Cards — {target.isoformat()}\n",
        f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M %Z')}_  ",
        f"_Books shopped: {', '.join(b.upper() for b in TARGET_BOOKS)}_  ",
        f"_Markets: Full-game ML/RL/Total, F5 Total, NRFI/YRFI_\n",
    ]
    bet_count = 0
    total_units = 0.0
    for gp in sorted(games_dir.glob("*.json")):
        game = _load(gp)
        odds = match_odds(odds_root, game) if odds_root else None
        graded = grade_one_game(game, odds)
        grades_out.append(graded)
        cards = graded["bet_cards"]
        if cards and total_units < MAX_BETS_PER_SLATE:
            md.append(f"## {graded['matchup']}  \n"
                      f"Grade H{graded['grade']['home']} / A{graded['grade']['away']} · "
                      f"FG xRuns {graded['expected_total']} · F5 xRuns {graded['expected_f5_total']} · "
                      f"NRFI {graded['nrfi_prob']:.1%}\n")
            for c in cards:
                if total_units + c["unit_size"] > MAX_BETS_PER_SLATE: break
                bet_count += 1
                total_units += c["unit_size"]
                md.append(render_card_md(game, BetCard(**c), bet_count))
        else:
            md.append(render_no_play(game, graded["grade"], graded["expected_total"],
                                     graded["expected_f5_total"], graded["nrfi_prob"]))

    md.append(f"\n_Total exposure today: **{total_units:.1f}u** across **{bet_count}** bets._\n")

    grades_path = day_dir / "grades.json"
    cards_path = day_dir / "cards.md"
    grades_path.write_text(json.dumps(grades_out, indent=2, default=str))
    cards_path.write_text("\n".join(md))
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
