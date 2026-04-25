"""
pregame_alerts.py — pre-first-pitch sanity check for pending bets

Runs every ~15 minutes during MLB game windows. For each pending bet whose
first pitch is in the next ~5-15 minutes (and that we haven't already
alerted on), this script:

  1. Refreshes the lineup from MLB Stats API and compares to what was
     confirmed when we placed the bet. Flags any new scratches.
  2. Refreshes the weather from Open-Meteo and compares to the original
     forecast. Flags rain risk jumps, wind reversals, big temperature
     shifts.
  3. Refreshes the line at our 4 user books and compares to the price we
     bet at. Flags lines that have moved THROUGH our fair value.

If any of those triggers fires, posts a Discord alert (rich embed) for that
bet so you can decide whether to live-hedge, late-fade, or just pass.

This script is idempotent: it tracks which bets have already been alerted
in `mlb_data/<DATE>/alerted.json` so a single bet only generates one alert.

Run:
    python pregame_alerts.py
    python pregame_alerts.py --window 5 20    # check bets starting 5-20 min from now

Required env:
    DISCORD_WEBHOOK_URL  (or any other notify channel — uses notify.py)
    ODDS_API_KEY         (for line-move check)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

import requests

from bet_tracker import (
    DATA_ROOT_DEFAULT, _ensure_log, _read_log, _f, _i,
)
from mlb_data_scraper import (
    MLB_API, ODDS_API, ALL_MARKETS, ALL_BOOKS, TARGET_BOOKS, SHARP_ANCHORS,
    PARKS, fetch_weather, american_to_prob,
)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Default window: alert on bets whose first pitch is between (min, max) min from now
DEFAULT_WINDOW_MIN = (5, 15)

# Thresholds for what counts as a "real" change worth alerting
WEATHER_THRESHOLDS = {
    "rain_jump_pct":      20,    # +20%-pt rain probability since original
    "wind_reversal_deg":  90,    # wind direction shifted >90° (in/out flipped)
    "wind_speed_jump":    8,     # wind speed up >8 mph
    "temp_drop":          12,    # temperature down >12°F
    "rain_floor":         50,    # rain prob >50% in absolute terms
}
LINE_MOVE_THROUGH_FAIR_PCT = 0.005  # current fair vs bet implied: how far past = warn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _alerted_path(data_root: Path, date_iso: str) -> Path:
    return data_root / date_iso / "alerted.json"

def _load_alerted(data_root: Path, date_iso: str) -> set[str]:
    p = _alerted_path(data_root, date_iso)
    if not p.exists(): return set()
    return set(json.loads(p.read_text()))

def _save_alerted(data_root: Path, date_iso: str, alerted: set[str]) -> None:
    p = _alerted_path(data_root, date_iso)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sorted(alerted)))


def _load_original_game(data_root: Path, date_iso: str, game_pk: int) -> dict | None:
    p = data_root / date_iso / "games" / f"{game_pk}.json"
    if not p.exists(): return None
    return json.loads(p.read_text())


# ---------------------------------------------------------------------------
# Trigger checks
# ---------------------------------------------------------------------------

def check_lineup_scratches(original_game: dict, game_pk: int) -> list[str]:
    """Return a list of warnings about new scratches since lineups confirmed."""
    warnings: list[str] = []
    orig_lineups = original_game.get("lineups") or {}
    if not orig_lineups.get("lineups_confirmed"):
        return []

    # Re-fetch the live feed
    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
        live = requests.get(url, timeout=15).json()
    except Exception as e:
        return [f"could not refresh lineup ({e})"]

    box = live.get("liveData", {}).get("boxscore", {})

    for side in ("home", "away"):
        orig_lineup = orig_lineups.get(f"{side}_lineup") or []
        orig_ids = {p["id"] for p in orig_lineup if p.get("id")}
        if not orig_ids: continue

        team_box = box.get("teams", {}).get(side, {})
        new_order = team_box.get("battingOrder", []) or []
        new_ids = set(new_order)

        scratched = orig_ids - new_ids
        if scratched:
            scratched_names = [p["name"] for p in orig_lineup
                              if p.get("id") in scratched]
            for name in scratched_names:
                warnings.append(f"{side.title()} lineup: **{name}** SCRATCHED")
    return warnings


def check_weather_change(original_game: dict, venue_id: int, first_pitch_iso: str) -> list[str]:
    """Compare current weather forecast to original snapshot."""
    warnings: list[str] = []
    orig_wx = original_game.get("weather") or {}
    if not orig_wx.get("available") or orig_wx.get("indoor"):
        return []
    try:
        new_wx = fetch_weather(venue_id, first_pitch_iso)
    except Exception:
        return []
    if not new_wx.get("available") or new_wx.get("indoor"):
        return []

    rain_jump = (new_wx.get("precip_prob_pct", 0) - orig_wx.get("precip_prob_pct", 0))
    if rain_jump >= WEATHER_THRESHOLDS["rain_jump_pct"] or \
       new_wx.get("precip_prob_pct", 0) >= WEATHER_THRESHOLDS["rain_floor"]:
        warnings.append(
            f"Rain risk now **{new_wx.get('precip_prob_pct')}%** "
            f"(was {orig_wx.get('precip_prob_pct')}%)")

    if (orig_wx.get("wind_dir_deg") is not None and
            new_wx.get("wind_dir_deg") is not None):
        diff = abs(new_wx["wind_dir_deg"] - orig_wx["wind_dir_deg"]) % 360
        diff = min(diff, 360 - diff)
        if diff >= WEATHER_THRESHOLDS["wind_reversal_deg"]:
            warnings.append(
                f"Wind direction shifted {diff:.0f}° "
                f"({orig_wx.get('wind_dir_deg')}° → {new_wx.get('wind_dir_deg')}°)")

    wind_jump = (new_wx.get("wind_mph", 0) - orig_wx.get("wind_mph", 0))
    if wind_jump >= WEATHER_THRESHOLDS["wind_speed_jump"]:
        warnings.append(
            f"Wind speed up to **{new_wx.get('wind_mph')} mph** "
            f"(was {orig_wx.get('wind_mph')} mph)")

    temp_drop = (orig_wx.get("temp_f", 0) - new_wx.get("temp_f", 0))
    if temp_drop >= WEATHER_THRESHOLDS["temp_drop"]:
        warnings.append(
            f"Temperature dropped to **{new_wx.get('temp_f')}°F** "
            f"(was {orig_wx.get('temp_f')}°F)")

    return warnings


def check_line_movement(bet_row: dict) -> list[str]:
    """Compare current best price to the price we bet at.
    Flags if the line has moved through our fair value (i.e., we no longer have edge)."""
    warnings: list[str] = []
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key: return []

    # We only have the user's data via bet_log; we do a single odds API call
    # per script invocation for the entire window to save quota — caller can
    # cache. Here we accept a per-bet refetch cost since calls are infrequent.
    bet_price = _i(bet_row.get("price"))
    fair_prob = _f(bet_row.get("fair_prob"))
    if bet_price is None or fair_prob is None: return []

    # Convert "Away @ Home" -> teams
    matchup = bet_row.get("matchup", "")
    try:
        away, home = matchup.split(" @ ", 1)
    except ValueError:
        return []

    try:
        odds = requests.get(
            f"{ODDS_API}/sports/baseball_mlb/odds",
            params={
                "apiKey": api_key, "regions": "us,us2,eu",
                "markets": ",".join(ALL_MARKETS),
                "oddsFormat": "american",
                "bookmakers": ",".join(ALL_BOOKS),
            }, timeout=20).json()
    except Exception:
        return []

    game = next((g for g in odds
                 if g.get("home_team") == home and g.get("away_team") == away), None)
    if not game: return []

    market_key = {"moneyline":"h2h","runline":"spreads","total":"totals",
                  "f5_total":"totals_1st_5_innings","nrfi":"totals_1st_1_innings"
                 }.get(bet_row.get("market"))
    if not market_key: return []

    # Find best current price across the 4 target books at the same line
    side = bet_row.get("side", "")
    line = _f(bet_row.get("line"))
    target_name = (home if side == "home" else away) if market_key in ("h2h","spreads") \
                  else ("over" if side in ("over","yrfi") else "under")

    best_price = None
    for b in game.get("bookmakers", []):
        if b["key"].lower() not in TARGET_BOOKS: continue
        m = next((m for m in b.get("markets", []) if m["key"] == market_key), None)
        if not m: continue
        for o in m.get("outcomes", []):
            ok_name = (o["name"] == target_name) if market_key in ("h2h","spreads") \
                      else (o["name"].lower() == target_name)
            ok_line = (line is None) or (abs(float(o.get("point") or 0) - line) < 0.001)
            if ok_name and ok_line:
                p = int(o["price"])
                if best_price is None or p > best_price:
                    best_price = p

    if best_price is None: return []
    bet_implied = american_to_prob(bet_price)
    new_implied = american_to_prob(best_price)

    if new_implied >= fair_prob - LINE_MOVE_THROUGH_FAIR_PCT:
        # Line moved past our fair value — edge gone
        warnings.append(
            f"Line moved to **{best_price:+d}** (was {bet_price:+d}). "
            f"Implied prob now {new_implied:.1%}; our fair was {fair_prob:.1%} — "
            f"edge has compressed to ~{(fair_prob-new_implied)*100:+.1f}%")
    elif new_implied >= bet_implied + 0.025:
        # Line moved toward our side — confirms our take, just informational
        warnings.append(
            f"Line strengthened to **{best_price:+d}** (was {bet_price:+d}). "
            f"Sharp money agrees — your edge looks confirmed.")
    return warnings


# ---------------------------------------------------------------------------
# Discord alert
# ---------------------------------------------------------------------------

def send_alert(bet_row: dict, warnings_by_kind: dict[str, list[str]]) -> bool:
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        print(f"[alert] no DISCORD_WEBHOOK_URL set; would have alerted bet #{bet_row['bet_id']}")
        return False

    has_alert = any(warnings_by_kind.values())
    if not has_alert: return False

    # Determine severity color
    has_critical = bool(warnings_by_kind.get("lineup")) or \
                   bool(warnings_by_kind.get("line_through_fair"))
    color = 0xEF4444 if has_critical else 0xF59E0B   # red if scratch/edge gone, amber otherwise

    fields = []
    if warnings_by_kind.get("lineup"):
        fields.append({"name": "🚨 Lineup",
                       "value": "\n".join(f"⚠ {w}" for w in warnings_by_kind["lineup"][:5]),
                       "inline": False})
    if warnings_by_kind.get("weather"):
        fields.append({"name": "🌧 Weather",
                       "value": "\n".join(f"⚠ {w}" for w in warnings_by_kind["weather"][:5]),
                       "inline": False})
    if warnings_by_kind.get("line"):
        fields.append({"name": "📊 Market",
                       "value": "\n".join(f"⚠ {w}" for w in warnings_by_kind["line"][:5]),
                       "inline": False})

    bet_summary = (f"**{bet_row['matchup']}**\n"
                   f"{bet_row['market']} • {bet_row['side']}"
                   f"{' @ ' + bet_row['line'] if bet_row.get('line') else ''} "
                   f"@ **{bet_row.get('book','').upper()}** "
                   f"{int(_f(bet_row.get('price'),0)):+d} • {bet_row.get('units_risked')}u")

    payload = {
        "embeds": [{
            "title": "⚠ PRE-GAME ALERT",
            "description": bet_summary,
            "color": color,
            "fields": fields,
            "footer": {"text": f"First pitch ~10 min • bet #{bet_row['bet_id']}"},
        }]
    }
    try:
        r = requests.post(url, json=payload, timeout=20)
        return r.status_code in (200, 204)
    except Exception as e:
        print(f"[alert] discord post failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run(data_root: Path, window_min: tuple[int, int]) -> int:
    log = _ensure_log(data_root)
    rows = _read_log(log)
    if not rows:
        print("[pregame] empty log — nothing to check")
        return 0

    now = datetime.now(timezone.utc)
    lo = now + timedelta(minutes=window_min[0])
    hi = now + timedelta(minutes=window_min[1])

    # Build the date-keyed alerted set so we don't double-fire
    today = now.date().isoformat()
    alerted = _load_alerted(data_root, today)

    eligible = []
    for r in rows:
        if r.get("status") != "pending": continue
        bet_id = str(r.get("bet_id"))
        if bet_id in alerted: continue
        fp = r.get("first_pitch")
        if not fp: continue
        try:
            ts = datetime.fromisoformat(fp.replace("Z", "+00:00"))
        except Exception: continue
        if lo <= ts <= hi:
            eligible.append((r, ts))

    if not eligible:
        print(f"[pregame] no eligible bets in window {window_min[0]}-{window_min[1]} min")
        return 0

    print(f"[pregame] {len(eligible)} bet(s) eligible — running checks")
    fired = 0
    # group by gamePk to dedupe weather/lineup checks per game
    by_game: dict[int, list[dict]] = {}
    for r, _ in eligible:
        pk = _i(r.get("gamePk"))
        if pk is None: continue
        by_game.setdefault(pk, []).append(r)

    for pk, game_rows in by_game.items():
        original = _load_original_game(data_root, today, pk)
        if not original:
            print(f"  [skip] no original snapshot for gamePk {pk}")
            continue

        venue_id = (original.get("venue") or {}).get("venue_id")
        # venue_id may not be stored; pull from the schedule snapshot if needed
        if venue_id is None:
            # The scraper stores venue but not always venue_id; fall back to
            # the snapshot's venue.name lookup. For a robust check here we
            # accept that weather check may be skipped if missing.
            pass
        first_pitch = original.get("gameDate", "")

        lineup_warns = check_lineup_scratches(original, pk)
        weather_warns = check_weather_change(original, venue_id, first_pitch) if venue_id else []

        for r in game_rows:
            line_warns = check_line_movement(r)
            warnings = {
                "lineup":  lineup_warns,
                "weather": weather_warns,
                "line":    line_warns,
            }
            if not any(warnings.values()):
                continue
            if send_alert(r, warnings):
                alerted.add(str(r["bet_id"]))
                fired += 1

    _save_alerted(data_root, today, alerted)
    print(f"[pregame] sent {fired} alert(s)")
    return fired


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=str(DATA_ROOT_DEFAULT))
    ap.add_argument("--window", nargs=2, type=int, default=list(DEFAULT_WINDOW_MIN),
                    metavar=("MIN", "MAX"),
                    help="window in minutes from now to alert (default 5 15)")
    args = ap.parse_args(argv)
    data_root = Path(args.data_root).expanduser().resolve()
    run(data_root, tuple(args.window))
    return 0


if __name__ == "__main__":
    sys.exit(main())
