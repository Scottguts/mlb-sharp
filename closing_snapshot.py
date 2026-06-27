"""
closing_snapshot.py — capture closing-line value for pending bets

Designed to be invoked hourly during MLB game windows (1 PM – 11 PM ET).
For each `pending` row in `bet_log.csv` whose first pitch is within the
next ~LOOKAHEAD_MIN minutes AND that does not yet have a closing price,
this script:

  1. Pulls the current odds snapshot from The Odds API (same books +
     markets the daily scraper uses).
  2. Devigs the same market on Pinnacle to get the fair closing prob.
  3. Records:
       closing_price       (current best price across the 4 user books
                            at the bet's exact line, or empty if line moved)
       closing_fair_prob   (Pinnacle-devigged fair prob)
       clv_pct             (closing_fair_prob − bet_implied_prob)
       beat_close          ("yes" if your price is better than close, else "no")

CLV semantics
-------------
We compare your bet's IMPLIED probability to the closing FAIR probability.
Positive `clv_pct` means you bet at better-than-closing value. Across a
large enough sample, a sharp bettor should average +2-3% CLV; this is the
single most reliable short-term proof you are betting the right side.

Run:
    python closing_snapshot.py                   # default data root
    python closing_snapshot.py --lookahead 90    # look at games starting in next 90 min
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from bet_tracker import (
    DATA_ROOT_DEFAULT, _ensure_log, _read_log, _write_log, _f, _i,
)
from mlb_data_scraper import (
    ODDS_API, ALL_MARKETS, ALL_BOOKS, FULL_MARKETS, TARGET_BOOKS, SHARP_ANCHORS,
    american_to_prob, devig_two_way, _get_odds_json, _odds_keys,
)

LOOKAHEAD_MIN_DEFAULT = 60   # capture closing for games starting within 60 min


# ---------------------------------------------------------------------------
# Odds fetching (we re-fetch a fresh snapshot here on purpose)
# ---------------------------------------------------------------------------

def _fetch_current_odds(keys: list[str]) -> list[dict]:
    """Fetch current full-game MLB odds via the shared key-rotation helper.

    Requests only FULL_MARKETS (h2h/spreads/totals) in a SINGLE call: the old
    code tried the combined alt-inning markets first, which 422s every run and
    forced a second fallback call — doubling quota burn. It also used only the
    primary key; routing through _get_odds_json drains the primary then fails
    over to the backup, so a closing snapshot still captures when key 1 is spent.
    CLV for F5/NRFI is unavailable (those markets 422 anyway); ML/RL/total — the
    overwhelming majority of bets — capture fine.
    """
    return _get_odds_json(
        f"{ODDS_API}/sports/baseball_mlb/odds",
        {"regions": "us,us2,eu", "markets": ",".join(FULL_MARKETS),
         "oddsFormat": "american", "bookmakers": ",".join(ALL_BOOKS)},
        keys=keys) or []


# ---------------------------------------------------------------------------
# Matching odds -> bet rows
# ---------------------------------------------------------------------------

def _market_key_for(market: str) -> str | None:
    return {
        "moneyline":  "h2h",
        "runline":    "spreads",
        "total":      "totals",
        "f5_total":   "totals_1st_5_innings",
        "nrfi":       "totals_1st_1_innings",
    }.get(market)


def _find_book_outcome(game_odds: dict, book_key: str, market_key: str,
                       outcome_predicate) -> dict | None:
    book = next((b for b in game_odds.get("bookmakers", [])
                 if b["key"].lower() == book_key.lower()), None)
    if not book: return None
    market = next((m for m in book.get("markets", []) if m["key"] == market_key), None)
    if not market: return None
    for o in market.get("outcomes", []):
        if outcome_predicate(o): return o
    return None


def _best_price_at_line(game_odds: dict, market_key: str,
                        target_team_or_side: str, target_line, books) -> tuple[int | None, str]:
    """For the same market_key, side, and line — return the best (highest)
    American price across the user's target books. Returns (None, '') if no
    match found at that exact line."""
    best_price, best_book = None, ""
    for b in game_odds.get("bookmakers", []):
        if b["key"].lower() not in books: continue
        m = next((m for m in b.get("markets", []) if m["key"] == market_key), None)
        if not m: continue
        for o in m.get("outcomes", []):
            if not _outcome_matches(o, market_key, target_team_or_side, target_line):
                continue
            p = int(o["price"])
            if best_price is None or p > best_price:
                best_price, best_book = p, b["key"]
    return best_price, best_book


def _outcome_matches(o: dict, market_key: str, target: str, target_line) -> bool:
    """True if this outcome corresponds to the bet's side AND line."""
    name = o.get("name", "")
    point = o.get("point")
    if market_key == "h2h":
        return name == target
    if market_key == "spreads":
        return (name == target) and (target_line is None or
                                     abs(float(point or 0) - float(target_line)) < 0.001)
    if market_key in ("totals", "totals_1st_5_innings", "totals_1st_1_innings"):
        return (name.lower() == target.lower()) and \
               (target_line is None or abs(float(point or 0) - float(target_line)) < 0.001)
    return False


def _devig_one_book(market: dict, market_key: str, side_target: str,
                    target_line) -> float | None:
    """Compute side prob from one book's market via two-way devig."""
    outs = market.get("outcomes", [])
    if market_key == "h2h":
        if len(outs) != 2: return None
        prices = {o["name"]: int(o["price"]) for o in outs}
        if side_target not in prices: return None
        names = list(prices.keys())
        a, b = devig_two_way(prices[names[0]], prices[names[1]])
        return a if names[0] == side_target else b
    if market_key in ("totals", "totals_1st_5_innings", "totals_1st_1_innings"):
        over = next((o for o in outs if o["name"].lower() == "over" and
                     (target_line is None or abs(float(o.get("point") or 0) - float(target_line)) < 0.001)), None)
        under = next((o for o in outs if o["name"].lower() == "under" and
                      (target_line is None or abs(float(o.get("point") or 0) - float(target_line)) < 0.001)), None)
        if not over or not under: return None
        ov_p, un_p = devig_two_way(int(over["price"]), int(under["price"]))
        if side_target.lower() in ("over", "yrfi"): return ov_p
        if side_target.lower() in ("under", "nrfi"): return un_p
    return None


def _devigged_close_prob(game_odds: dict, market_key: str, side_target: str,
                         target_line) -> float | None:
    """Devigged P(side) at the close.

    Prefers Pinnacle when available, falls back to the median devigged
    prob across the user-facing target books. Pinnacle isn't always
    carrying the market by close (especially mid-week, smaller games),
    so the fallback prevents 0% CLV-capture rates.
    """
    candidates: list[float] = []
    for b in game_odds.get("bookmakers", []):
        bk = b.get("key", "").lower()
        if bk not in (TARGET_BOOKS + SHARP_ANCHORS):
            continue
        market = next((m for m in b.get("markets", []) if m["key"] == market_key), None)
        if not market: continue
        prob = _devig_one_book(market, market_key, side_target, target_line)
        if prob is None: continue
        if bk in SHARP_ANCHORS:
            return prob   # Pinnacle takes priority
        candidates.append(prob)
    if not candidates: return None
    candidates.sort()
    return candidates[len(candidates)//2]




# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def snapshot(data_root: Path, lookahead_min: int = LOOKAHEAD_MIN_DEFAULT) -> int:
    keys = _odds_keys()
    if not keys:
        print("[snapshot] no Odds API key set — cannot fetch closing odds")
        return 0
    log = _ensure_log(data_root)
    rows = _read_log(log)
    if not rows:
        print("[snapshot] empty bet log — nothing to snapshot")
        return 0

    now = datetime.now(timezone.utc)
    horizon = now + timedelta(minutes=lookahead_min)

    # Pending rows that still need a closing snapshot
    candidates = []
    for r in rows:
        if r.get("status") != "pending": continue
        if r.get("closing_price"): continue
        fp = r.get("first_pitch")
        if not fp: continue
        try:
            ts = datetime.fromisoformat(fp.replace("Z", "+00:00"))
        except Exception:
            continue
        # We want games whose first pitch is in the next `lookahead_min` minutes
        # OR that have just started in the last 5 min (catch lineup-late bets).
        if (now - timedelta(minutes=5)) <= ts <= horizon:
            candidates.append((r, ts))
    if not candidates:
        print(f"[snapshot] no pending bets within next {lookahead_min} min")
        return 0

    print(f"[snapshot] {len(candidates)} pending bet(s) eligible — fetching odds")
    try:
        all_odds = _fetch_current_odds(keys)
    except Exception as e:
        print(f"[snapshot] error fetching odds: {e}")
        return 0

    # Index odds by team-pair for quick lookup
    by_matchup = {(g.get("home_team"), g.get("away_team")): g for g in all_odds}

    captured = 0
    for r, ts in candidates:
        # bet matchup is "Away @ Home"
        matchup = r.get("matchup", "")
        try:
            away, home = matchup.split(" @ ", 1)
        except ValueError:
            continue
        game_odds = by_matchup.get((home, away))
        if not game_odds:
            continue
        market_key = _market_key_for(r["market"])
        if not market_key: continue

        line = _f(r.get("line"))
        # Determine which "side string" matches the odds API outcome name
        side = r.get("side")
        if r["market"] == "moneyline":
            side_target = home if side == "home" else away
        elif r["market"] == "runline":
            side_target = home if side == "home" else away
        elif r["market"] == "total":
            side_target = side  # over / under
        elif r["market"] == "f5_total":
            side_target = side
        elif r["market"] == "nrfi":
            side_target = "under" if side.lower() == "nrfi" else "over"
        else:
            continue

        close_price, close_book = _best_price_at_line(
            game_odds, market_key, side_target, line, TARGET_BOOKS)
        fair_p = _devigged_close_prob(game_odds, market_key, side_target, line)

        bet_price = _i(r.get("price"))
        bet_implied = american_to_prob(bet_price) if bet_price is not None else None

        r["closing_price"] = "" if close_price is None else str(close_price)
        r["closing_fair_prob"] = "" if fair_p is None else f"{fair_p:.4f}"

        if fair_p is not None and bet_implied is not None:
            clv = fair_p - bet_implied
            r["clv_pct"] = f"{clv:.4f}"
            r["beat_close"] = "yes" if clv > 0 else "no"
        else:
            r["clv_pct"] = ""
            r["beat_close"] = ""

        captured += 1

    _write_log(log, rows)
    print(f"[snapshot] captured closing data for {captured} bet(s)")
    return captured


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=str(DATA_ROOT_DEFAULT))
    ap.add_argument("--lookahead", type=int, default=LOOKAHEAD_MIN_DEFAULT,
                    help="minutes ahead to consider 'closing window' (default 60)")
    args = ap.parse_args(argv)
    data_root = Path(args.data_root).expanduser().resolve()
    snapshot(data_root, args.lookahead)
    return 0


if __name__ == "__main__":
    sys.exit(main())
