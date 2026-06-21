"""
MLB Sharp Betting — Data Scraper
================================
Pulls every data feed the Sharp MLB Betting System needs into a single
JSON-per-game payload.

Data sources (all free unless noted):
  - MLB Stats API (statsapi.mlb.com)         schedule, lineups, box scores, umpires
  - Baseball Savant (via pybaseball)         Statcast pitcher data, splits, velo
  - FanGraphs (via pybaseball)               team offensive stats, pitcher rates
  - Open-Meteo (no API key)                  first-pitch weather per park
  - The Odds API (free key required)         multi-book odds (set ODDS_API_KEY env)

Run:
    python mlb_data_scraper.py                         # today's slate
    python mlb_data_scraper.py --date 2026-04-25       # specific date
    python mlb_data_scraper.py --game-pk 745432        # single game
    python mlb_data_scraper.py --no-odds               # skip odds (no key)

Outputs:
    ./mlb_data/<DATE>/slate.json                       summary of all games
    ./mlb_data/<DATE>/games/<gamePk>.json              per-game payload
    ./mlb_data/<DATE>/pitchers/<mlbamId>.json          pitcher profiles
    ./mlb_data/<DATE>/odds.json                        raw odds snapshot

Install:
    pip install requests pandas pybaseball python-dateutil
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, date, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any

import requests

try:
    import pybaseball as pyb
    pyb.cache.enable()
    PYBASEBALL = True
except ImportError:
    PYBASEBALL = False
    print("[warn] pybaseball not installed — Statcast/FanGraphs scrapes disabled.")
    print("       pip install pybaseball")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MLB_API = "https://statsapi.mlb.com/api/v1"
ODDS_API = "https://api.the-odds-api.com/v4"
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"

USER_AGENT = "mlb-sharp-scraper/1.0 (educational use)"

# Park lat/lng + roof type + park run factor (R/100, 100 = neutral).
# pf_runs is calibrated from 2022-2024 actual MLB outcomes via
# historical_validate.py. pf_hr_* are static estimates (refresh from
# Statcast batted-ball data when available).
# Venue IDs verified against statsapi.mlb.com/api/v1/venues.
PARKS: dict[int, dict[str, Any]] = {
    # venue_id : {name, lat, lng, roof, pf_runs, pf_hr_l, pf_hr_r}
       1: {"name": "Angel Stadium",         "lat": 33.8003, "lng": -117.8827, "roof": "open",        "pf_runs": 101, "pf_hr_l": 100, "pf_hr_r":  98},
       2: {"name": "Oriole Park",           "lat": 39.2839, "lng":  -76.6217, "roof": "open",        "pf_runs":  97, "pf_hr_l":  92, "pf_hr_r": 105},
       3: {"name": "Fenway Park",           "lat": 42.3467, "lng":  -71.0972, "roof": "open",        "pf_runs": 111, "pf_hr_l":  96, "pf_hr_r":  97},
       4: {"name": "Rate Field",            "lat": 41.8300, "lng":  -87.6339, "roof": "open",        "pf_runs":  98, "pf_hr_l": 109, "pf_hr_r": 108},
       5: {"name": "Progressive Field",     "lat": 41.4962, "lng":  -81.6852, "roof": "open",        "pf_runs":  92, "pf_hr_l":  93, "pf_hr_r":  99},
       7: {"name": "Kauffman Stadium",      "lat": 39.0517, "lng":  -94.4803, "roof": "open",        "pf_runs": 106, "pf_hr_l":  92, "pf_hr_r":  91},
      10: {"name": "Oakland Coliseum",      "lat": 37.7516, "lng": -122.2005, "roof": "open",        "pf_runs":  96, "pf_hr_l":  90, "pf_hr_r":  92},  # historical
      12: {"name": "Tropicana Field",       "lat": 27.7682, "lng":  -82.6534, "roof": "dome",        "pf_runs":  93, "pf_hr_l":  98, "pf_hr_r":  97},  # historical (Rays through 2024)
      14: {"name": "Rogers Centre",         "lat": 43.6414, "lng":  -79.3894, "roof": "retractable", "pf_runs":  98, "pf_hr_l": 104, "pf_hr_r": 106},
      15: {"name": "Chase Field",           "lat": 33.4455, "lng": -112.0667, "roof": "retractable", "pf_runs": 107, "pf_hr_l": 103, "pf_hr_r": 104},
      17: {"name": "Wrigley Field",         "lat": 41.9484, "lng":  -87.6553, "roof": "open",        "pf_runs":  95, "pf_hr_l": 104, "pf_hr_r": 105},
      19: {"name": "Coors Field",           "lat": 39.7559, "lng": -104.9942, "roof": "open",        "pf_runs": 128, "pf_hr_l": 108, "pf_hr_r": 112},
      22: {"name": "Dodger Stadium",        "lat": 34.0739, "lng": -118.2400, "roof": "open",        "pf_runs": 100, "pf_hr_l": 105, "pf_hr_r": 102},
      31: {"name": "PNC Park",              "lat": 40.4469, "lng":  -80.0058, "roof": "open",        "pf_runs": 103, "pf_hr_l":  88, "pf_hr_r":  96},
      32: {"name": "American Family Field", "lat": 43.0280, "lng":  -87.9712, "roof": "retractable", "pf_runs":  96, "pf_hr_l": 100, "pf_hr_r": 102},
     680: {"name": "T-Mobile Park",         "lat": 47.5914, "lng": -122.3325, "roof": "retractable", "pf_runs":  86, "pf_hr_l":  94, "pf_hr_r":  92},
    2392: {"name": "Daikin Park",           "lat": 29.7572, "lng":  -95.3551, "roof": "retractable", "pf_runs":  97, "pf_hr_l":  99, "pf_hr_r": 105},  # Houston (formerly Minute Maid)
    2394: {"name": "Comerica Park",         "lat": 42.3390, "lng":  -83.0485, "roof": "open",        "pf_runs":  94, "pf_hr_l":  91, "pf_hr_r":  92},
    2395: {"name": "Oracle Park",           "lat": 37.7786, "lng": -122.3893, "roof": "open",        "pf_runs":  93, "pf_hr_l":  88, "pf_hr_r":  82},
    2523: {"name": "Steinbrenner Field",    "lat": 27.9799, "lng":  -82.5074, "roof": "open",        "pf_runs": 100, "pf_hr_l": 100, "pf_hr_r": 100},  # Rays' temporary home (no MLB sample yet)
    2529: {"name": "Sutter Health Park",    "lat": 38.5805, "lng": -121.5133, "roof": "open",        "pf_runs": 100, "pf_hr_l": 100, "pf_hr_r": 100},  # Athletics' temporary home (no MLB sample yet)
    2602: {"name": "Great American Ball Park","lat": 39.0975, "lng": -84.5067, "roof": "open",        "pf_runs": 108, "pf_hr_l": 119, "pf_hr_r": 119},
    2680: {"name": "Petco Park",            "lat": 32.7073, "lng": -117.1566, "roof": "open",        "pf_runs":  91, "pf_hr_l":  93, "pf_hr_r":  95},
    2681: {"name": "Citizens Bank Park",    "lat": 39.9061, "lng":  -75.1665, "roof": "open",        "pf_runs": 103, "pf_hr_l": 109, "pf_hr_r": 108},
    2889: {"name": "Busch Stadium",         "lat": 38.6226, "lng":  -90.1928, "roof": "open",        "pf_runs": 100, "pf_hr_l":  93, "pf_hr_r":  95},
    3289: {"name": "Citi Field",            "lat": 40.7571, "lng":  -73.8458, "roof": "open",        "pf_runs":  95, "pf_hr_l":  99, "pf_hr_r":  98},
    3309: {"name": "Nationals Park",        "lat": 38.8730, "lng":  -77.0074, "roof": "open",        "pf_runs": 103, "pf_hr_l": 102, "pf_hr_r":  99},
    3312: {"name": "Target Field",          "lat": 44.9817, "lng":  -93.2776, "roof": "open",        "pf_runs": 100, "pf_hr_l": 100, "pf_hr_r":  98},
    3313: {"name": "Yankee Stadium",        "lat": 40.8296, "lng":  -73.9262, "roof": "open",        "pf_runs":  98, "pf_hr_l": 117, "pf_hr_r": 102},
    4169: {"name": "loanDepot park",        "lat": 25.7780, "lng":  -80.2197, "roof": "retractable", "pf_runs": 102, "pf_hr_l":  91, "pf_hr_r":  92},
    4705: {"name": "Truist Park",           "lat": 33.8908, "lng":  -84.4678, "roof": "open",        "pf_runs": 100, "pf_hr_l": 100, "pf_hr_r": 102},
    5325: {"name": "Globe Life Field",      "lat": 32.7474, "lng":  -97.0844, "roof": "retractable", "pf_runs": 105, "pf_hr_l": 102, "pf_hr_r": 100},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _redact(text: str) -> str:
    """Strip secrets (API keys) out of any string before it is logged/persisted."""
    return re.sub(r"(apiKey=)[^&\s]+", r"\1***", str(text))


_ET = ZoneInfo("America/New_York")


def _et_date(iso: str) -> str:
    """Calendar date (YYYY-MM-DD) of a UTC ISO timestamp in US/Eastern.

    MLB `gameDate` is the UTC first-pitch time. A night game after ~8pm ET rolls
    past 00:00Z, so a naive `gameDate[:10]` slice files it one ET day LATE — which
    skews rest-day / recent-form / usage windows. Converting to ET first fixes it
    (ZoneInfo handles EST/EDT automatically)."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_ET).date().isoformat()
    except (ValueError, AttributeError, TypeError):
        return (iso or "")[:10]


def _get(url: str, params: dict | None = None, retries: int = 3, timeout: int = 30) -> dict:
    """GET JSON with simple retry. 4xx client errors are not retried (a 401/422
    won't change on a re-request), but 5xx / network errors back off and retry."""
    headers = {"User-Agent": USER_AGENT}
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            if status is not None and 400 <= status < 500:
                raise  # client error — retrying won't help (quota, bad market, etc.)
            if i == retries - 1:
                raise
            time.sleep(1.5 ** i)
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(1.5 ** i)
    return {}


# ---------------------------------------------------------------------------
# Odds API key rotation / failover
# ---------------------------------------------------------------------------
# The Odds API sells a fixed monthly request quota per key. To stretch coverage
# across a full month you can configure MULTIPLE keys: the primary is drained
# first, and when it returns 401/429 (quota exhausted) we automatically fail
# over to the next key — even mid-slate. 401/429 responses are NOT charged, so
# re-probing a drained primary on later runs is free.
#
# Configure either way:
#   * ODDS_API_KEY = "key1,key2,key3"        (comma-separated, in priority order)
#   * ODDS_API_KEY="key1"  ODDS_API_KEY_2="key2"  ODDS_API_KEY_3="key3"  ...
# Both forms can be combined; duplicates are ignored.
_ODDS_DEAD_KEYS: set[str] = set()   # keys found exhausted during THIS process run


def _odds_keys() -> list[str]:
    """Ordered list of Odds API keys (primary first, then numbered backups)."""
    keys: list[str] = []
    for k in (os.environ.get("ODDS_API_KEY") or "").split(","):
        k = k.strip()
        if k and k not in keys:
            keys.append(k)
    for i in range(2, 9):  # ODDS_API_KEY_2 .. _8
        k = (os.environ.get(f"ODDS_API_KEY_{i}") or "").strip()
        if k and k not in keys:
            keys.append(k)
    return keys


def _get_odds_json(url: str, params: dict, keys: list[str] | None = None) -> dict:
    """GET against The Odds API, rotating through configured keys on quota
    exhaustion (HTTP 401/429). Tries each live key in order and advances ONLY
    when a key is out of quota; other errors (422 bad-market, network) raise so
    callers can degrade gracefully as before."""
    keys = keys or _odds_keys()
    if not keys:
        raise RuntimeError("no Odds API key configured (set ODDS_API_KEY)")
    live = [k for k in keys if k not in _ODDS_DEAD_KEYS] or keys
    last_exc: Exception | None = None
    for idx, key in enumerate(live):
        try:
            return _get(url, params={**params, "apiKey": key}, retries=2)
        except requests.exceptions.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            if status in (401, 429):
                _ODDS_DEAD_KEYS.add(key)   # skip this key for the rest of the run
                last_exc = e
                if idx < len(live) - 1:
                    continue               # fail over to the next key
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("no Odds API key configured")


def _save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))


# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------

def fetch_schedule(target: date) -> list[dict]:
    """Schedule + probable pitchers for a date. Returns list of game dicts."""
    url = f"{MLB_API}/schedule"
    data = _get(url, params={
        "sportId": 1,
        "date": target.isoformat(),
        "hydrate": "probablePitcher,linescore,team,venue,weather,officials,lineups",
    })
    games = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            games.append({
                "gamePk": g["gamePk"],
                "gameDate": g["gameDate"],
                "status": g["status"]["detailedState"],
                "venue_id": g["venue"]["id"],
                "venue_name": g["venue"]["name"],
                "away": {
                    "team_id": g["teams"]["away"]["team"]["id"],
                    "team_name": g["teams"]["away"]["team"]["name"],
                    "probable_pitcher_id": (g["teams"]["away"].get("probablePitcher") or {}).get("id"),
                    "probable_pitcher_name": (g["teams"]["away"].get("probablePitcher") or {}).get("fullName"),
                },
                "home": {
                    "team_id": g["teams"]["home"]["team"]["id"],
                    "team_name": g["teams"]["home"]["team"]["name"],
                    "probable_pitcher_id": (g["teams"]["home"].get("probablePitcher") or {}).get("id"),
                    "probable_pitcher_name": (g["teams"]["home"].get("probablePitcher") or {}).get("fullName"),
                },
            })
    return games


# Catcher framing runs above/below average (2024 season Statcast leaderboard
# extract — refresh annually). Source: Baseball Savant "Catcher Framing".
# Positive = steals more strikes (good for K projections, lowers run total).
# Approximate: top framers worth +6 to +12 runs/season; bottom -8 to -10.
CATCHER_FRAMING: dict[int, float] = {
    # Elite framers (refresh from baseballsavant.mlb.com/catcher_framing)
    669127: 12.0,  # Patrick Bailey (SFG)
    668939: 9.4,   # Adley Rutschman (BAL)
    641598: 8.5,   # Cal Raleigh (SEA)
    687462: 7.8,   # Austin Wells (NYY)
    669004: 7.4,   # Sean Murphy (ATL)
    656629: 7.2,   # Jonah Heim (TEX)
    669221: 7.0,   # Tyler Heineman / others
    642336: 6.7,   # Iván Herrera
    669911: 6.5,   # Joey Bart
    608348: 6.0,   # J.T. Realmuto (PHI)
    608360: 5.6,   # Logan O'Hoppe (LAA)
    641857: 5.1,   # Travis d'Arnaud
    641941: 4.7,   # James McCann
    643327: 4.5,   # Will Smith (LAD)
    643446: 4.0,   # Carson Kelly
    660688: 3.8,   # Yainer Diaz
    642708: 3.3,   # Christian Vazquez
    641778: 3.0,   # Tomas Nido
    642054: 2.6,   # Christian Bethancourt
    660644: 2.0,   # Francisco Alvarez
    # Below-average framers
    682928: -2.5,  # Bo Naylor
    669456: -3.0,  # Henry Davis
    608986: -3.5,  # Tom Murphy
    572020: -4.0,  # Yan Gomes
    605137: -4.5,  # Salvador Perez
    624431: -5.0,  # Willson Contreras
    605204: -6.0,  # Martin Maldonado
    608841: -7.0,  # Gary Sanchez
    518960: -8.5,  # Kurt Suzuki (retired but stat carries)
    458015: -10.0, # Yasmani Grandal
}


def _starting_catcher(box_teams: dict, side: str) -> int | None:
    """Identify the team's catcher (position code '2') from box-score players."""
    players = (box_teams or {}).get(side, {}).get("players", {})
    for _, p in players.items():
        pos = (p.get("position") or {}).get("code") or (p.get("position") or {}).get("abbreviation")
        if pos == "2" or pos == "C":
            return p.get("person", {}).get("id")
    return None


# Module-level cache for the 60-day schedule pull used by ump-tendency lookups.
# Without this we re-fetch 60 days of schedule 15+ times per slate (once per
# game's HP ump lookup), which was the single biggest scraper bottleneck.
_UMP_SCHEDULE_CACHE: dict[int, dict] = {}


def _ump_schedule(days: int) -> dict:
    """Schedule + linescore + officials for the last N days. Cached per-run."""
    if days in _UMP_SCHEDULE_CACHE:
        return _UMP_SCHEDULE_CACHE[days]
    end = date.today()
    start = end - timedelta(days=days)
    try:
        sched = _get(f"{MLB_API}/schedule", params={
            "sportId": 1,
            "startDate": start.isoformat(), "endDate": end.isoformat(),
            "hydrate": "officials,linescore",
        })
    except Exception:
        sched = {"dates": []}
    _UMP_SCHEDULE_CACHE[days] = sched
    return sched


# Per-ump tendency cache. Populated lazily from the shared schedule pull.
_UMP_TENDENCY_CACHE: dict[tuple[int, int], dict] = {}


def fetch_umpire_recent_tendency(umpire_id: int, days: int = 60) -> dict:
    """Compute K-rate + scoring tendency for a home-plate umpire over recent
    games. Uses the cached shared schedule pull so 15 lookups in one slate
    cost ~one schedule fetch instead of fifteen.
    """
    key = (umpire_id, days)
    if key in _UMP_TENDENCY_CACHE:
        return _UMP_TENDENCY_CACHE[key]

    sched = _ump_schedule(days)
    ump_games = []
    league_runs = []
    for d in sched.get("dates", []):
        for g in d.get("games", []):
            if g.get("status", {}).get("abstractGameState") != "Final": continue
            ls = g.get("linescore") or {}
            home_r = ls.get("teams", {}).get("home", {}).get("runs")
            away_r = ls.get("teams", {}).get("away", {}).get("runs")
            if home_r is None or away_r is None: continue
            league_runs.append(home_r + away_r)
            hp = next((o for o in g.get("officials", []) or []
                       if (o.get("officialType") or "").lower() in
                          ("home plate", "home", "hp", "plate")), None)
            if hp and hp.get("official", {}).get("id") == umpire_id:
                ump_games.append(home_r + away_r)
    if not ump_games or len(ump_games) < 3:
        out = {"available": False, "reason": "small_sample", "n_games": len(ump_games)}
    else:
        league_avg = sum(league_runs) / len(league_runs) if league_runs else 8.8
        ump_avg = sum(ump_games) / len(ump_games)
        out = {
            "available": True,
            "n_games":  len(ump_games),
            "ump_avg_runs":    round(ump_avg, 2),
            "league_avg_runs": round(league_avg, 2),
            "run_delta":       round(ump_avg - league_avg, 2),
        }
    _UMP_TENDENCY_CACHE[key] = out
    return out


def fetch_catcher_framing_for_game(game_pk: int) -> dict:
    """Pull each side's starting catcher (when lineups confirmed) and look up
    their framing run value. Returns a tilt-per-side in runs/game."""
    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
        data = _get(url)
    except Exception as e:
        return {"available": False, "error": str(e)}
    box_teams = data.get("liveData", {}).get("boxscore", {}).get("teams", {})
    out: dict[str, Any] = {"available": True}
    for side in ("home", "away"):
        cid = _starting_catcher(box_teams, side)
        # Per-game framing impact: season runs / ~140 games behind plate
        framing_runs = CATCHER_FRAMING.get(cid, 0.0) if cid else 0.0
        out[side] = {
            "catcher_id":   cid,
            "season_runs":  framing_runs,
            "per_game":     round(framing_runs / 140.0, 3),
        }
    return out


def fetch_lineups_and_umpire(game_pk: int) -> dict:
    """Confirmed lineups + umpires from live feed (only available close to/at game time)."""
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    data = _get(url)
    game_data = data.get("gameData", {})
    box = data.get("liveData", {}).get("boxscore", {})

    def _lineup(side: str) -> list[dict]:
        team = box.get("teams", {}).get(side, {})
        order = team.get("battingOrder", []) or []
        players = team.get("players", {})
        out = []
        for pid in order:
            p = players.get(f"ID{pid}", {})
            person = p.get("person", {})
            pos = p.get("position", {}).get("abbreviation")
            bats = p.get("stats", {})
            out.append({
                "id": person.get("id"),
                "name": person.get("fullName"),
                "position": pos,
                "bat_side": (p.get("batSide") or {}).get("code"),
            })
        return out

    umps = []
    hp_ump_id = None
    for o in game_data.get("officials", []) or []:
        u = {
            "type": o.get("officialType"),
            "id": o.get("official", {}).get("id"),
            "name": o.get("official", {}).get("fullName"),
        }
        umps.append(u)
        if (u["type"] or "").lower() in ("home plate", "home", "hp", "plate"):
            hp_ump_id = u["id"]

    # Pull dynamic tendency for the home plate umpire when known. Falls back
    # to the hardcoded table later in grader if this returns unavailable.
    hp_tendency = None
    if hp_ump_id:
        try:
            hp_tendency = fetch_umpire_recent_tendency(hp_ump_id, days=60)
        except Exception:
            hp_tendency = {"available": False}

    return {
        "lineups_confirmed": bool(box.get("teams", {}).get("home", {}).get("battingOrder")),
        "away_lineup": _lineup("away"),
        "home_lineup": _lineup("home"),
        "umpires": umps,
        "hp_ump_tendency": hp_tendency,
    }


def fetch_pitcher_profile(mlbam_id: int, days: int = 30) -> dict:
    """Statcast pitch-level data for last N days, plus aggregated rate stats."""
    if not PYBASEBALL or mlbam_id is None:
        return {"id": mlbam_id, "available": False}

    end = date.today()
    start = end - timedelta(days=days)
    try:
        df = pyb.statcast_pitcher(start.isoformat(), end.isoformat(), mlbam_id)
    except Exception as e:
        return {"id": mlbam_id, "error": str(e), "available": False}

    if df is None or df.empty:
        return {"id": mlbam_id, "available": False, "reason": "no_recent_pitches"}

    # Per-start rollup — includes K count + estimated batters faced so we can
    # project per-start strikeout totals for prop bets.
    has_events = "events" in df.columns
    agg_kwargs = dict(
        pitches=("pitch_type", "count"),
        avg_velo=("release_speed", "mean"),
        max_velo=("release_speed", "max"),
        csw=("description", lambda s: ((s == "called_strike") | (s == "swinging_strike")).mean()),
        hard_hit=("launch_speed", lambda s: (s >= 95).mean(skipna=True)),
    )
    if has_events:
        # Strikeout-ending pitches mark the K. "strikeout" and "strikeout_double_play"
        # both count as 1 K on the pitcher's stat line.
        agg_kwargs["strikeouts"] = ("events", lambda s: s.isin(["strikeout", "strikeout_double_play"]).sum())
        # Walk-ending events for pitcher-walks prop projection
        agg_kwargs["walks"] = ("events", lambda s: s.isin(["walk", "intent_walk"]).sum())
        # Plate appearances ended = batters faced (any non-null event row)
        agg_kwargs["batters_faced"] = ("events", lambda s: s.notna().sum())
    if "launch_speed_angle" in df.columns:
        agg_kwargs["barrel"] = ("launch_speed_angle", lambda s: (s == 6).mean(skipna=True))
    starts = (
        df.groupby("game_date")
          .agg(**agg_kwargs)
          .reset_index()
          .sort_values("game_date", ascending=False)
    )

    # Pitch mix
    mix = (
        df.groupby("pitch_type").size().div(len(df)).round(3).to_dict()
    )

    # Pitch movement trends — compare last start to window average per pitch
    # type for `pfx_x` (horizontal break) and `pfx_z` (vertical break). A drop
    # of >=1.5 inches in either dimension on a primary pitch type is a
    # red flag — the pitcher's arm slot or stuff has changed.
    movement_flags: list[str] = []
    if {"pitch_type", "pfx_x", "pfx_z", "game_date"}.issubset(df.columns):
        # Average movement per pitch type over the window
        window_mov = df.groupby("pitch_type").agg(
            avg_pfx_x=("pfx_x", "mean"), avg_pfx_z=("pfx_z", "mean"),
            count=("pfx_x", "count"),
        ).reset_index()
        # Last start
        last_date = df["game_date"].max()
        last = df[df["game_date"] == last_date]
        last_mov = last.groupby("pitch_type").agg(
            last_pfx_x=("pfx_x", "mean"), last_pfx_z=("pfx_z", "mean"),
            last_count=("pfx_x", "count"),
        ).reset_index()
        joined = window_mov.merge(last_mov, on="pitch_type", how="inner")
        # Convert from feet → inches (Statcast pfx_x / pfx_z are in feet)
        # Only flag for primary pitches (>=8 in the window AND >=5 last start)
        for _, row in joined.iterrows():
            if row["count"] < 8 or row["last_count"] < 5: continue
            dx_in = (float(row["last_pfx_x"]) - float(row["avg_pfx_x"])) * 12.0
            dz_in = (float(row["last_pfx_z"]) - float(row["avg_pfx_z"])) * 12.0
            if abs(dx_in) >= 1.5 or abs(dz_in) >= 1.5:
                movement_flags.append(
                    f"{row['pitch_type']} movement shift "
                    f"({dx_in:+.1f}\" horiz, {dz_in:+.1f}\" vert) last start"
                )

    # Splits vs LHB / RHB
    splits = {}
    for stand in ("L", "R"):
        sub = df[df["stand"] == stand]
        if not sub.empty:
            splits[stand] = {
                "pitches": int(len(sub)),
                "avg_velo": round(float(sub["release_speed"].mean()), 2),
                "csw": round(float(((sub["description"] == "called_strike") |
                                    (sub["description"] == "swinging_strike")).mean()), 3),
                "xwoba": round(float(sub["estimated_woba_using_speedangle"].mean(skipna=True)), 3) if "estimated_woba_using_speedangle" in sub.columns else None,
                "hard_hit_rate": round(float((sub["launch_speed"] >= 95).mean(skipna=True)), 3),
            }

    # Throw hand (L/R) — needed by the grader's platoon-advantage check.
    throws = None
    if "p_throws" in df.columns:
        vals = df["p_throws"].dropna().unique().tolist()
        if vals:
            throws = vals[0]

    # K/BB aggregates over the window (for prop projections).
    k_total = int(starts["strikeouts"].sum()) if "strikeouts" in starts.columns else None
    bb_total = int(starts["walks"].sum()) if "walks" in starts.columns else None
    bf_total = int(starts["batters_faced"].sum()) if "batters_faced" in starts.columns else None
    n_starts = int(len(starts))
    k_per_start = round(k_total / n_starts, 2) if (k_total is not None and n_starts) else None
    bb_per_start = round(bb_total / n_starts, 2) if (bb_total is not None and n_starts) else None
    k_per_bf = round(k_total / bf_total, 3) if (k_total and bf_total) else None
    bb_per_bf = round(bb_total / bf_total, 3) if (bb_total and bf_total) else None

    return {
        "id": mlbam_id,
        "available": True,
        "window_days": days,
        "throws": throws,
        "total_pitches": int(len(df)),
        "season_avg_velo": round(float(df["release_speed"].mean()), 2),
        "starts": starts.to_dict(orient="records"),
        "pitch_mix": mix,
        "splits": splits,
        "movement_flags": movement_flags,
        # K + BB rate stats for prop tracking
        "k_total_window":   k_total,
        "bb_total_window":  bb_total,
        "k_starts_window":  n_starts,
        "k_per_start":      k_per_start,
        "bb_per_start":     bb_per_start,
        "k_per_bf":         k_per_bf,
        "bb_per_bf":        bb_per_bf,
    }


def fetch_team_offense(team_abbr_or_id: int, season: int) -> dict:
    """Season-to-date team batting splits (vs LHP / RHP) from FanGraphs."""
    if not PYBASEBALL:
        return {"available": False}
    try:
        df = pyb.team_batting(season)
        # team_batting is leaguewide; filter as needed
        return {"available": True, "rows": len(df), "note": "filter columns by team in your model"}
    except Exception as e:
        return {"available": False, "error": str(e)}


# Cache for per-batter 7-day wOBA lookups (called 10x per game in the worst case).
_RECENT_WOBA_CACHE: dict[tuple[int, int, int], dict] = {}


def _fetch_recent_woba(batter_id: int, season: int, days: int = 7) -> dict:
    """Pull recent (last N days) hitter stats and compute a rough wOBA.

    Uses /api/v1/people/{id}/stats?stats=byDateRange. Returns None values
    if no PA in the window (cold or injured)."""
    key = (batter_id, season, days)
    if key in _RECENT_WOBA_CACHE:
        return _RECENT_WOBA_CACHE[key]
    end = date.today()
    start = end - timedelta(days=days)
    try:
        d = _get(f"https://statsapi.mlb.com/api/v1/people/{batter_id}/stats", params={
            "stats": "byDateRange", "group": "hitting",
            "startDate": start.isoformat(), "endDate": end.isoformat(),
            "season": season,
        })
    except Exception:
        return {"available": False}
    stat = None
    for s in d.get("stats", []):
        for split in s.get("splits", []):
            if split.get("stat"):
                stat = split["stat"]; break
        if stat: break
    if not stat:
        return {"available": False}
    try:
        pa = float(stat.get("plateAppearances", 0) or 0)
        ab = float(stat.get("atBats", 0) or 0)
        obp = float(stat.get("obp", 0) or 0)
        slg = float(stat.get("slg", 0) or 0)
        ops = float(stat.get("ops", 0) or 0)
    except (ValueError, TypeError):
        return {"available": False}
    if pa < 12:   # need ~3 games of PA before "recent" is meaningful
        out = {"available": False, "reason": "small_sample", "pa": int(pa)}
        _RECENT_WOBA_CACHE[key] = out
        return out
    woba = round(0.69 * obp + 0.45 * slg, 3)
    out = {"available": True, "days": days, "pa": int(pa), "ab": int(ab),
           "ops": ops, "obp": obp, "slg": slg, "woba": woba}
    _RECENT_WOBA_CACHE[key] = out
    return out


# Cache for team batting splits — called 2× per game (one per side)
# but same key recurs across all games where the team plays.
_TEAM_SPLIT_CACHE: dict[tuple[int, int, str], dict] = {}


def fetch_team_batting_split_vs_hand(team_id: int, season: int,
                                     vs_hand: str | None) -> dict:
    """Season-to-date TEAM batting line vs LHP or RHP. Cached per run."""
    if not vs_hand or vs_hand.upper() not in ("L", "R"):
        return {"available": False, "reason": "unknown_hand"}
    key = (team_id, season, vs_hand.upper())
    if key in _TEAM_SPLIT_CACHE:
        return _TEAM_SPLIT_CACHE[key]
    split_code = "vl" if vs_hand.upper() == "L" else "vr"
    try:
        d = _get(f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats", params={
            "stats": "statSplits", "group": "hitting",
            "sitCodes": split_code, "season": season,
        })
    except Exception as e:
        return {"available": False, "error": str(e)}
    stat = None
    for s in d.get("stats", []):
        for split in s.get("splits", []):
            if split.get("stat"):
                stat = split["stat"]; break
        if stat: break
    if not stat:
        return {"available": False, "reason": "no_data"}
    try:
        pa = int(stat.get("plateAppearances", 0) or 0)
        ab = int(stat.get("atBats", 0) or 0)
        avg = float(stat.get("avg", 0) or 0)
        obp = float(stat.get("obp", 0) or 0)
        slg = float(stat.get("slg", 0) or 0)
        ops = float(stat.get("ops", 0) or 0)
        so = int(stat.get("strikeOuts", 0) or 0)
        bb = int(stat.get("baseOnBalls", 0) or 0)
        hr = int(stat.get("homeRuns", 0) or 0)
    except (ValueError, TypeError):
        return {"available": False, "reason": "parse_error"}
    woba = round(0.69 * obp + 0.45 * slg, 3)
    out = {
        "available": True,
        "vs_hand":   vs_hand.upper(),
        "season":    season,
        "pa":        pa, "ab": ab,
        "avg":       round(avg, 3), "obp": round(obp, 3),
        "slg":       round(slg, 3), "ops": round(ops, 3),
        "woba":      woba, "hr": hr,
        "k_pct":     round(so / pa, 3) if pa else 0.0,
        "bb_pct":    round(bb / pa, 3) if pa else 0.0,
    }
    _TEAM_SPLIT_CACHE[key] = out
    return out


def fetch_top_of_order_quality(lineup: list[dict], season: int,
                                vs_hand: str | None = None,
                                top_n: int = 5) -> dict:
    """Pull season wOBA/OPS/K%/BB% for the top N batters in a lineup.

    `vs_hand` should be 'L' or 'R' to pull split stats vs LHP/RHP. If splits
    aren't available the season aggregate is returned. Used by NRFI/F5/total
    models AND by the batter-walks prop tracker.

    BB% is added so the prop layer can project per-batter walk count.
    """
    if not lineup:
        return {"available": False, "reason": "no_lineup"}
    top3 = lineup[:top_n]
    out = {"available": True, "season": season, "vs_hand": vs_hand,
           "batters": [], "avg_woba": None, "avg_ops": None,
           "avg_k_pct": None, "avg_bb_pct": None}
    wobas: list[float] = []
    opss:  list[float] = []
    kpcts: list[float] = []
    bbpcts: list[float] = []
    for b in top3:
        pid = b.get("id")
        if pid is None: continue
        # Hitting splits per hand:
        # /api/v1/people/{pid}/stats?stats=statSplits&group=hitting&sitCodes=vl,vr&season=YYYY
        try:
            split_code = "vr" if vs_hand and vs_hand.upper() == "R" else \
                         "vl" if vs_hand and vs_hand.upper() == "L" else None
            if split_code:
                d = _get(f"https://statsapi.mlb.com/api/v1/people/{pid}/stats", params={
                    "stats": "statSplits", "group": "hitting",
                    "sitCodes": split_code, "season": season,
                })
            else:
                d = _get(f"https://statsapi.mlb.com/api/v1/people/{pid}/stats", params={
                    "stats": "season", "group": "hitting", "season": season,
                })
        except Exception:
            continue
        # Find the first stat block with numbers
        stat = None
        for s in d.get("stats", []):
            for split in s.get("splits", []):
                if split.get("stat"):
                    stat = split["stat"]; break
            if stat: break
        if not stat:
            continue
        # Available fields: avg, ops, atBats, strikeOuts, plateAppearances
        try:
            ab = float(stat.get("atBats", 0) or 0)
            pa = float(stat.get("plateAppearances", 0) or 0)
            so = float(stat.get("strikeOuts", 0) or 0)
            bb = float(stat.get("baseOnBalls", 0) or 0)
            ops = float(stat.get("ops", 0) or 0)
            avg = float(stat.get("avg", 0) or 0)
            obp = float(stat.get("obp", 0) or 0)
            slg = float(stat.get("slg", 0) or 0)
        except (ValueError, TypeError):
            continue
        if ab < 20:   # too small a sample
            continue
        # wOBA proxy (linear weights): rough approximation
        # wOBA ≈ 0.69·OBP + 0.45·SLG (simplified — real weights have hbp etc.)
        woba = 0.69 * obp + 0.45 * slg
        k_pct = so / pa if pa else 0
        bb_pct = bb / pa if pa else 0
        # 7-day rolling wOBA — catches hot / cold streaks the season aggregate
        # smooths over.
        recent = _fetch_recent_woba(pid, season, days=7)
        out["batters"].append({
            "id": pid, "name": b.get("name"),
            "ab": int(ab), "pa": int(pa),
            "ops": ops, "avg": avg, "obp": obp, "slg": slg,
            "woba": round(woba, 3),
            "k_pct": round(k_pct, 3),
            "bb_pct": round(bb_pct, 3),
            "walks": int(bb),
            "recent_7d": recent,
        })
        wobas.append(woba); opss.append(ops); kpcts.append(k_pct); bbpcts.append(bb_pct)
    if wobas:
        out["avg_woba"] = round(sum(wobas) / len(wobas), 3)
        out["avg_ops"] = round(sum(opss) / len(opss), 3)
        out["avg_k_pct"] = round(sum(kpcts) / len(kpcts), 3)
        out["avg_bb_pct"] = round(sum(bbpcts) / len(bbpcts), 3)
    return out


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in miles between two lat/lng points."""
    import math
    R = 3959.0  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def fetch_team_travel(team_id: int, today_venue_id: int, today_iso: str,
                      lookback_days: int = 5) -> dict:
    """Compute days rest + travel distance since the team's last game.

    Long-distance travel (>1500 mi, especially east<->west cross-country)
    correlates with ~3-5% expected run drop the next game. Days rest matters
    in the opposite direction (extra rest is mildly positive).
    """
    today = date.fromisoformat(today_iso)
    start = today - timedelta(days=lookback_days)
    sched = _get(f"{MLB_API}/schedule", params={
        "sportId": 1, "teamId": team_id,
        "startDate": start.isoformat(), "endDate": (today - timedelta(days=1)).isoformat(),
        "hydrate": "venue",
    })
    last_game = None
    for d in sched.get("dates", []):
        for g in d.get("games", []):
            if g["status"]["abstractGameState"] != "Final": continue
            last_game = g   # keep iterating to find the most recent
    if not last_game:
        return {"available": False, "days_rest": None, "miles_traveled": None,
                "cross_country": False, "notes": []}
    last_date = date.fromisoformat(_et_date(last_game["gameDate"]))
    days_rest = (today - last_date).days
    last_venue_id = last_game.get("venue", {}).get("id")
    miles = None
    cross_country = False
    notes: list[str] = []
    if last_venue_id and today_venue_id:
        from_park = PARKS.get(last_venue_id)
        to_park   = PARKS.get(today_venue_id)
        if from_park and to_park:
            miles = _haversine_miles(from_park["lat"], from_park["lng"],
                                      to_park["lat"], to_park["lng"])
            cross_country = miles >= 1500
            if cross_country:
                notes.append(f"long flight {miles:.0f}mi since last game")
    if days_rest >= 2:
        notes.append(f"{days_rest} days rest")
    elif days_rest == 0:
        notes.append("back-to-back day game after night game")
    return {
        "available": True,
        "days_rest": days_rest,
        "miles_traveled": round(miles, 0) if miles is not None else None,
        "cross_country": cross_country,
        "last_venue_id": last_venue_id,
        "notes": notes,
    }


def fetch_team_recent_form(team_id: int, days: int = 14) -> dict:
    """Pull a team's last-N-days batting performance from MLB Stats API.
    Returns runs/game, OPS, K%, BB%, plus L/R-handed pitcher splits if available."""
    end = date.today()
    start = end - timedelta(days=days)
    sched = _get(f"{MLB_API}/schedule", params={
        "sportId": 1, "teamId": team_id,
        "startDate": start.isoformat(), "endDate": end.isoformat(),
        "hydrate": "linescore",
    })
    games_played = 0; runs_for = 0; runs_against = 0
    wins = losses = 0
    last_results = []
    for d in sched.get("dates", []):
        for g in d.get("games", []):
            if g["status"]["abstractGameState"] != "Final": continue
            home = g["teams"]["home"]
            away = g["teams"]["away"]
            is_home = home["team"]["id"] == team_id
            our = home if is_home else away
            opp = away if is_home else home
            our_runs = our.get("score", 0) or 0
            opp_runs = opp.get("score", 0) or 0
            games_played += 1
            runs_for += our_runs
            runs_against += opp_runs
            if our_runs > opp_runs: wins += 1
            else: losses += 1
            last_results.append({
                "date": _et_date(g["gameDate"]),
                "for": our_runs, "against": opp_runs,
                "won": our_runs > opp_runs,
            })
    return {
        "team_id": team_id, "window_days": days,
        "games_played": games_played,
        "wins": wins, "losses": losses,
        "rpg_for": round(runs_for / games_played, 2) if games_played else None,
        "rpg_against": round(runs_against / games_played, 2) if games_played else None,
        "win_pct": round(wins / games_played, 3) if games_played else None,
        "results": last_results[-7:],   # most recent 7 games
    }


def fetch_bullpen_usage(team_id: int, days: int = 7) -> dict:
    """Rolling reliever workload + quality from box scores of last N days.

    Returns per-reliever appearances/pitches/IP plus recent K%, BB%, and ERA
    so the grader can distinguish a tired-but-elite pen from a fresh-but-bad
    one. Usage flags (back-to-back, pitched_yesterday) are unchanged.
    """
    end = date.today()
    start = end - timedelta(days=days)
    sched = _get(f"{MLB_API}/schedule", params={
        "sportId": 1,
        "teamId": team_id,
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "hydrate": "linescore",
    })
    usage: dict[int, dict] = {}
    # Aggregate quality across the window
    bp_outs = 0      # innings pitched, in outs
    bp_runs = 0
    bp_h = 0
    bp_bb = 0
    bp_so = 0
    bp_bf = 0        # batters faced
    for d in sched.get("dates", []):
        for g in d.get("games", []):
            if g["status"]["abstractGameState"] != "Final":
                continue
            # Use the live feed instead of plain boxscore — gameData.players
            # includes pitchHand which we need for handedness splits.
            live = _get(f"https://statsapi.mlb.com/api/v1.1/game/{g['gamePk']}/feed/live")
            gd_players = live.get("gameData", {}).get("players", {})
            box = live.get("liveData", {}).get("boxscore", {})
            side = "home" if g["teams"]["home"]["team"]["id"] == team_id else "away"
            players = box.get("teams", {}).get(side, {}).get("players", {})
            # Identify the starter (highest IP among pitchers, usually)
            pitcher_rows = []
            for _, p in players.items():
                if p.get("position", {}).get("code") != "1":
                    continue
                pstats = p.get("stats", {}).get("pitching", {})
                if not pstats:
                    continue
                ip = float(pstats.get("inningsPitched", 0) or 0)
                pitcher_rows.append((p, pstats, ip))
            # Sort descending by IP — the top one is the starter, rest are relievers
            pitcher_rows.sort(key=lambda r: -r[2])
            for idx, (p, pstats, ip) in enumerate(pitcher_rows):
                is_starter = (idx == 0 and ip >= 3.0)
                pid = p["person"]["id"]
                if is_starter:
                    continue   # only count bullpen
                # Throw hand from gameData.players (richer than boxscore)
                gd_p = gd_players.get(f"ID{pid}") or {}
                throws = (gd_p.get("pitchHand") or {}).get("code")
                usage.setdefault(pid, {
                    "name": p["person"]["fullName"],
                    "throws": throws,
                    "appearances": 0, "pitches": 0, "ip": 0.0,
                    "dates": [],
                })
                usage[pid]["appearances"] += 1
                usage[pid]["pitches"] += int(pstats.get("numberOfPitches", 0) or 0)
                usage[pid]["ip"] += ip
                usage[pid]["dates"].append(_et_date(g["gameDate"]))
                # Bullpen-wide quality aggregates
                # MLB inningsPitched is e.g. "1.2" = 1 inning + 2 outs
                whole = int(ip)
                frac = round((ip - whole) * 10)
                outs = whole * 3 + frac
                bp_outs += outs
                bp_runs += int(pstats.get("earnedRuns", 0) or 0)
                bp_h    += int(pstats.get("hits", 0) or 0)
                bp_bb   += int(pstats.get("baseOnBalls", 0) or 0)
                bp_so   += int(pstats.get("strikeOuts", 0) or 0)
                bp_bf   += int(pstats.get("battersFaced", 0) or 0)
    # Flag back-to-back
    for pid, info in usage.items():
        info["dates"] = sorted(info["dates"])
        info["back_to_back"] = any(
            (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days == 1
            for a, b in zip(info["dates"], info["dates"][1:])
        )
        info["pitched_yesterday"] = (end - timedelta(days=1)).isoformat() in info["dates"]
    bp_ip = bp_outs / 3.0 if bp_outs else 0.0
    quality = {
        "bp_innings": round(bp_ip, 2),
        "bp_era":     round((bp_runs * 9) / bp_ip, 2) if bp_ip > 0 else None,
        "bp_k_pct":   round(bp_so / bp_bf, 3) if bp_bf else None,
        "bp_bb_pct":  round(bp_bb / bp_bf, 3) if bp_bf else None,
        "bp_whip":    round((bp_h + bp_bb) / bp_ip, 2) if bp_ip > 0 else None,
    }
    # Split by handedness: count fresh-and-recent relievers by L/R so the grader
    # can match availability against the opposing lineup's handedness mix.
    by_hand: dict[str, dict] = {"L": {"count": 0, "pitches": 0, "appearances": 0,
                                       "fresh_count": 0},
                                 "R": {"count": 0, "pitches": 0, "appearances": 0,
                                       "fresh_count": 0}}
    for pid, info in usage.items():
        th = (info.get("throws") or "").upper()
        if th not in ("L", "R"): continue
        b = by_hand[th]
        b["count"]       += 1
        b["pitches"]     += info["pitches"]
        b["appearances"] += info["appearances"]
        # "Fresh" = didn't pitch yesterday AND not back-to-back
        if not info.get("pitched_yesterday") and not info.get("back_to_back"):
            b["fresh_count"] += 1
    quality["by_hand"] = by_hand
    return {"team_id": team_id, "window_days": days, "relievers": usage,
            "quality": quality}


def fetch_weather(venue_id: int, when_iso: str) -> dict:
    """Hourly forecast at first pitch from Open-Meteo (no API key)."""
    park = PARKS.get(venue_id)
    if not park:
        return {"available": False, "reason": "park_not_in_table", "venue_id": venue_id}
    if park["roof"] in ("dome",):
        return {"available": True, "indoor": True, "park": park["name"]}

    target = datetime.fromisoformat(when_iso.replace("Z", "+00:00"))
    target_date = target.date().isoformat()
    data = _get(OPEN_METEO, params={
        "latitude": park["lat"],
        "longitude": park["lng"],
        "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,wind_speed_10m,wind_direction_10m,dew_point_2m",
        "timezone": "America/New_York",
        "start_date": target_date,
        "end_date": target_date,
        "wind_speed_unit": "mph",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
    })
    hours = data.get("hourly", {})
    times = hours.get("time", [])
    if not times:
        return {"available": False, "reason": "no_forecast"}
    # find closest hour to first pitch
    target_h = target.replace(minute=0, second=0, microsecond=0).isoformat()[:13]
    idx = next((i for i, t in enumerate(times) if t.startswith(target_h)), 0)
    wind_mph = hours["wind_speed_10m"][idx]
    wind_dir = hours["wind_direction_10m"][idx]
    wind_effect = wind_relative_to_field(venue_id, wind_dir, wind_mph,
                                          indoor=False)
    return {
        "available": True,
        "indoor": False,
        "park": park["name"],
        "first_pitch_iso": when_iso,
        "temp_f":          hours["temperature_2m"][idx],
        "humidity_pct":    hours["relative_humidity_2m"][idx],
        "dew_point_f":     hours["dew_point_2m"][idx],
        "wind_mph":        wind_mph,
        "wind_dir_deg":    wind_dir,
        "wind_effect":     wind_effect,
        "precip_prob_pct": hours["precipitation_probability"][idx],
    }


def fetch_park_factors(venue_id: int) -> dict:
    p = PARKS.get(venue_id)
    if not p:
        return {"available": False}
    out = {
        "available": True,
        "name": p["name"],
        "roof": p["roof"],
        "pf_runs": p["pf_runs"],
        "pf_hr_lhb": p["pf_hr_l"],
        "pf_hr_rhb": p["pf_hr_r"],
    }
    if "cf_bearing" in p:
        out["cf_bearing"] = p["cf_bearing"]
    return out


# Compass bearing (degrees, 0=N) of each park's centerfield, measured from
# home plate. Used to translate raw wind direction into "out / in / cross"
# at each park. Values are park surveys (approximate, ±10°).
# Wikipedia / "Stadium orientation" lookups; refresh if a park is rebuilt.
PARK_CF_BEARING: dict[int, int] = {
       1:  44,   # Angel Stadium
       2:  39,   # Oriole Park
       3:  46,   # Fenway Park (toward 'The Triangle')
       4:  35,   # Rate Field
       5:   0,   # Progressive Field
       7:  44,   # Kauffman Stadium
      10:  60,   # Oakland Coliseum
      12:   0,   # Tropicana Field (dome — irrelevant)
      14:   0,   # Rogers Centre (retractable — irrelevant when closed)
      15:   0,   # Chase Field (retractable — irrelevant when closed)
      17:  37,   # Wrigley Field
      19:  10,   # Coors Field (close to N)
      22:  22,   # Dodger Stadium
      31: 117,   # PNC Park (faces SE)
      32:   0,   # American Family Field (retractable)
     680:   0,   # T-Mobile Park (retractable)
    2392:   0,   # Daikin Park (retractable)
    2394:   2,   # Comerica Park
    2395:  90,   # Oracle Park (CF roughly E, McCovey Cove R)
    2523:  60,   # Steinbrenner Field
    2529:  35,   # Sutter Health Park
    2602:  20,   # Great American Ball Park
    2680:   0,   # Petco Park (close to N)
    2681:  17,   # Citizens Bank Park
    2889:  60,   # Busch Stadium (faces NE)
    3289:  21,   # Citi Field
    3309:  30,   # Nationals Park
    3312:   0,   # Target Field
    3313:   0,   # Yankee Stadium
    4169:   0,   # loanDepot park (retractable)
    4705:  35,   # Truist Park
    5325:   0,   # Globe Life Field (retractable)
}


def wind_relative_to_field(venue_id: int, wind_dir_deg: float | None,
                           wind_mph: float | None, indoor: bool = False) -> dict:
    """Translate raw wind into baseball-meaningful direction at this park.

    Output: {effect: 'out'|'in'|'cross'|'calm'|'indoor', delta_runs: float,
             angle_off_cf: int}
    delta_runs is a small additive run estimate (cap ±0.4) used by the
    grader's expected_total adjustment.
    """
    if indoor:
        return {"effect": "indoor", "delta_runs": 0.0, "angle_off_cf": None}
    cf = PARK_CF_BEARING.get(venue_id)
    if cf is None or wind_dir_deg is None or wind_mph is None:
        return {"effect": "unknown", "delta_runs": 0.0, "angle_off_cf": None}
    if wind_mph < 5:
        return {"effect": "calm", "delta_runs": 0.0, "angle_off_cf": None}
    # Meteo wind_dir_deg is the direction the wind is COMING FROM (compass).
    # The wind blows toward (wind_dir_deg + 180) % 360. We compare that to
    # the CF bearing: 0° = blowing straight toward CF (out), 180° = toward
    # home plate (in), 90° = crosswind.
    blow_to = (wind_dir_deg + 180) % 360
    diff = abs(blow_to - cf) % 360
    if diff > 180:
        diff = 360 - diff
    angle_off_cf = int(diff)
    # Severity scales with mph above 5
    severity = max(0.0, (wind_mph - 5) / 10.0)
    if angle_off_cf <= 35:
        # Wind blowing OUT — boost runs
        delta = +0.4 * severity
        effect = "out"
    elif angle_off_cf >= 145:
        # Wind blowing IN — suppress runs
        delta = -0.4 * severity
        effect = "in"
    else:
        # Crosswind — minor effect, mostly slice/drift, near zero on totals
        delta = 0.0
        effect = "cross"
    return {"effect": effect,
            "delta_runs": round(max(-0.4, min(0.4, delta)), 3),
            "angle_off_cf": angle_off_cf}


# --------- Bookmaker policy ---------
# User-facing books we actually shop on.
# FanDuel removed 2026-06-03 after empirical analysis showed 41 of 64 settled
# bets fired on FanDuel at -27.7% ROI vs BetMGM +25.8% ROI / DraftKings +2.7%.
# FanDuel's marketing-driven plus-money trap lines kept winning "best price"
# shopping without offering real edge.
TARGET_BOOKS    = ("draftkings", "betmgm", "caesars")
# Sharp anchor used only for devig math (not displayed as a "best book"):
SHARP_ANCHORS   = ("pinnacle",)
# Markets we want for every game:
FULL_MARKETS    = ("h2h", "spreads", "totals")            # full game ML / RL / total
F5_MARKETS      = ("totals_1st_5_innings",)               # F5 totals only
INNING_MARKETS  = ("totals_1st_1_innings",)               # 1st-inning totals → NRFI/YRFI proxy

# Player prop markets — Phase 2 (paper trading)
# Each event requires its own API call (1 unit each). With ~15 games/day this
# costs ~450/month against the 500/month free tier — pair with daily odds
# (~30/month) and we sit just under budget.
PROP_MARKETS    = ("pitcher_strikeouts", "pitcher_walks", "batter_walks")

ALL_MARKETS     = FULL_MARKETS + F5_MARKETS + INNING_MARKETS
ALL_BOOKS       = TARGET_BOOKS + SHARP_ANCHORS


def fetch_event_player_props(event_id: str, api_key: str | None = None,
                              markets: tuple[str, ...] = PROP_MARKETS,
                              books: tuple[str, ...] = ALL_BOOKS) -> dict:
    """Fetch player-prop odds for ONE event (game) from The Odds API.

    Each call costs one API unit regardless of how many markets are listed.
    Returns the raw event payload with bookmakers/markets/outcomes.
    """
    keys = [api_key] if api_key else _odds_keys()
    if not keys:
        return {"available": False, "reason": "no_key"}
    url = f"{ODDS_API}/sports/baseball_mlb/events/{event_id}/odds"
    try:
        data = _get_odds_json(url, {
            "regions":    "us,us2,eu",
            "markets":    ",".join(markets),
            "oddsFormat": "american",
            "bookmakers": ",".join(books),
        }, keys=keys)
        return {"available": True, "event": data, "markets_requested": list(markets)}
    except Exception as e:
        return {"available": False, "error": _redact(str(e))}


def fetch_all_player_props(events_with_ids: list[tuple[str, dict]],
                           api_key: str | None = None) -> dict:
    """Pull props for a list of (event_id, game_meta) tuples.

    Returns a flat dict keyed by event_id with the event payload + a tally of
    how many calls succeeded so the caller can monitor quota usage.
    """
    keys = [api_key] if api_key else _odds_keys()
    if not keys:
        return {"available": False, "reason": "no_key", "events": {}}
    out: dict[str, Any] = {"available": True, "events": {}, "calls": 0,
                            "successes": 0, "errors": []}
    for event_id, meta in events_with_ids:
        out["calls"] += 1
        result = fetch_event_player_props(event_id, api_key=api_key)
        if result.get("available"):
            out["successes"] += 1
            out["events"][event_id] = result["event"]
        else:
            out["errors"].append({"event_id": event_id, "error": result.get("error", "?")})
    return out


def fetch_odds(api_key: str | None = None,
               markets: tuple[str, ...] = ALL_MARKETS,
               books:   tuple[str, ...] = ALL_BOOKS) -> dict:
    """Multi-book MLB odds.

    Returns a single payload covering full-game ML/RL/total, F5 totals,
    and 1st-inning totals (used as the NRFI/YRFI proxy — Over 0.5 = YRFI,
    Under 0.5 = NRFI). Requires The Odds API key (free tier exists).
    """
    # Use the explicit key if one was passed, otherwise the rotation list so the
    # primary key is drained before failing over to backups.
    keys = [api_key] if api_key else _odds_keys()
    if not keys:
        return {"available": False, "reason": "ODDS_API_KEY not set"}
    url = f"{ODDS_API}/sports/baseball_mlb/odds"
    payload: dict[str, Any] = {
        "available": True,
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "books_used": list(books),
        "markets_requested": list(markets),
        "markets_fetched": [],
        "games": [],
        "errors": [],
    }
    # The Odds API rejects (422) certain inning/F5 markets when bundled with the
    # full-game markets for the chosen book+region mix. The old code requested
    # everything in one call, ate the 422 every single run, then fell back to a
    # second call that silently DROPPED F5/NRFI markets — costing 2 requests AND
    # never returning the inning data. Instead we split markets into two groups:
    #   1. core full-game markets  → must succeed (a 422/401 here = real outage)
    #   2. inning / F5 markets      → isolated, so their failure can't blank the
    #                                 slate and the data is recovered when it IS
    #                                 supported.
    core_markets  = tuple(m for m in markets if m in FULL_MARKETS) or FULL_MARKETS
    extra_markets = tuple(m for m in markets if m not in FULL_MARKETS)

    games_by_id: dict[str, dict] = {}

    def _merge(games: list[dict]) -> None:
        """Merge a games list into games_by_id, combining markets per bookmaker."""
        for g in games or []:
            gid = g.get("id")
            if not gid:
                continue
            if gid not in games_by_id:
                games_by_id[gid] = g
                continue
            dst = games_by_id[gid]
            dst_books = {b.get("key"): b for b in dst.get("bookmakers", [])}
            for b in g.get("bookmakers", []):
                k = b.get("key")
                if k in dst_books:
                    dst_books[k].setdefault("markets", []).extend(b.get("markets", []))
                else:
                    dst.setdefault("bookmakers", []).append(b)
                    dst_books[k] = b

    # 1) Core full-game markets — required. Failure here is a genuine outage.
    try:
        core_data = _get_odds_json(url, {
            "regions":   "us,us2,eu",
            "markets":   ",".join(core_markets),
            "oddsFormat": "american",
            "bookmakers": ",".join(books),
        }, keys=keys)
        _merge(core_data)
        payload["markets_fetched"].extend(core_markets)
    except Exception as e:
        payload["available"] = False
        payload["errors"].append(_redact(f"core full-game markets call failed: {e}"))
        payload["games"] = list(games_by_id.values())
        return payload

    # 2) Inning / F5 markets — best-effort, isolated from the core slate.
    if extra_markets:
        try:
            extra_data = _get_odds_json(url, {
                "regions":   "us,us2,eu",
                "markets":   ",".join(extra_markets),
                "oddsFormat": "american",
                "bookmakers": ",".join(books),
            }, keys=keys)
            _merge(extra_data)
            payload["markets_fetched"].extend(extra_markets)
        except Exception as e:
            payload["errors"].append(_redact(
                f"inning/F5 markets unavailable (F5/NRFI skipped this run): {e}"))

    payload["games"] = list(games_by_id.values())
    return payload


# ---------------------------------------------------------------------------
# Devig + fair odds helper (use anywhere)
# ---------------------------------------------------------------------------

def american_to_prob(odds: int) -> float:
    return (-odds) / ((-odds) + 100) if odds < 0 else 100 / (odds + 100)


def prob_to_american(p: float) -> int:
    if p <= 0 or p >= 1:
        return 0
    return int(round(-100 * p / (1 - p))) if p >= 0.5 else int(round(100 * (1 - p) / p))


def devig_two_way(price_a: int, price_b: int) -> tuple[float, float]:
    pa, pb = american_to_prob(price_a), american_to_prob(price_b)
    s = pa + pb
    return pa / s, pb / s


def edge_pct(your_prob: float, offered_american: int) -> float:
    """Edge as a fraction. 0.045 == 4.5% edge."""
    decimal = (offered_american / 100 + 1) if offered_american > 0 else (100 / -offered_american + 1)
    return your_prob * decimal - 1


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def assemble_game_payload(game: dict, fetch_pitchers: bool = True,
                          fetch_pen: bool = True) -> dict:
    pk = game["gamePk"]
    payload = {
        "gamePk": pk,
        "gameDate": game["gameDate"],
        "venue": fetch_park_factors(game["venue_id"]),
        "weather": fetch_weather(game["venue_id"], game["gameDate"]),
        "away": dict(game["away"]),
        "home": dict(game["home"]),
        "lineups": fetch_lineups_and_umpire(pk),
    }
    if fetch_pitchers:
        payload["away"]["pitcher_profile"] = fetch_pitcher_profile(game["away"]["probable_pitcher_id"])
        payload["home"]["pitcher_profile"] = fetch_pitcher_profile(game["home"]["probable_pitcher_id"])
    if fetch_pen:
        payload["away"]["bullpen_usage"] = fetch_bullpen_usage(game["away"]["team_id"])
        payload["home"]["bullpen_usage"] = fetch_bullpen_usage(game["home"]["team_id"])
    # Recent form for both teams
    payload["away"]["recent_form"] = fetch_team_recent_form(game["away"]["team_id"])
    payload["home"]["recent_form"] = fetch_team_recent_form(game["home"]["team_id"])
    # Travel + rest since last game
    today_iso = _et_date(game["gameDate"])
    payload["away"]["travel"] = fetch_team_travel(game["away"]["team_id"], game["venue_id"], today_iso)
    payload["home"]["travel"] = fetch_team_travel(game["home"]["team_id"], game["venue_id"], today_iso)
    # Catcher framing (per game framing run impact, when lineups confirmed)
    payload["catcher_framing"] = fetch_catcher_framing_for_game(pk)
    # Top-of-order quality vs opposing starter's hand (uses confirmed lineups)
    season = datetime.fromisoformat(game["gameDate"].replace("Z", "+00:00")).year
    home_lineup = (payload["lineups"] or {}).get("home_lineup") or []
    away_lineup = (payload["lineups"] or {}).get("away_lineup") or []
    home_starter_throws = (payload["home"].get("pitcher_profile") or {}).get("throws")
    away_starter_throws = (payload["away"].get("pitcher_profile") or {}).get("throws")
    payload["home"]["top_of_order"] = fetch_top_of_order_quality(
        home_lineup, season, vs_hand=away_starter_throws)
    payload["away"]["top_of_order"] = fetch_top_of_order_quality(
        away_lineup, season, vs_hand=home_starter_throws)
    # Full-team batting split vs opposing starter's hand
    payload["home"]["team_split_vs_opp_hand"] = fetch_team_batting_split_vs_hand(
        game["home"]["team_id"], season, vs_hand=away_starter_throws)
    payload["away"]["team_split_vs_opp_hand"] = fetch_team_batting_split_vs_hand(
        game["away"]["team_id"], season, vs_hand=home_starter_throws)
    return payload


def run(target: date, out_root: Path, single_game_pk: int | None = None,
        fetch_odds_flag: bool = True) -> None:
    print(f"[+] Fetching slate for {target.isoformat()}")
    schedule = fetch_schedule(target)
    if single_game_pk:
        schedule = [g for g in schedule if g["gamePk"] == single_game_pk]
    print(f"[+] {len(schedule)} game(s) found")

    out_dir = out_root / target.isoformat()
    games_dir = out_dir / "games"
    games_dir.mkdir(parents=True, exist_ok=True)

    _save_json(out_dir / "slate.json", schedule)

    for g in schedule:
        pk = g["gamePk"]
        print(f"  → game {pk}: {g['away']['team_name']} @ {g['home']['team_name']}")
        try:
            payload = assemble_game_payload(g)
            _save_json(games_dir / f"{pk}.json", payload)
        except Exception as e:
            print(f"    [error] {e}")

    if fetch_odds_flag:
        odds = fetch_odds()
        _save_json(out_dir / "odds.json", odds)
        print(f"[+] Odds: {'OK' if odds.get('available') else 'skipped (' + odds.get('reason','') + ')'}")

        # Player props — Phase 2 paper trading. One API call per event.
        # Stays well within quota (~450 calls/month + 30 for daily odds).
        if odds.get("available"):
            events_with_ids = []
            seen_team_pairs = set()
            for og in odds.get("games", []):
                eid = og.get("id")
                home = og.get("home_team")
                away = og.get("away_team")
                key = (home, away)
                if not eid or key in seen_team_pairs:
                    continue
                seen_team_pairs.add(key)
                events_with_ids.append((eid, {"home": home, "away": away}))
            print(f"[+] Fetching player props for {len(events_with_ids)} event(s)...")
            props = fetch_all_player_props(events_with_ids)
            _save_json(out_dir / "prop_odds.json", props)
            print(f"    {props.get('successes', 0)}/{props.get('calls', 0)} successful")

    print(f"[done] Wrote data to {out_dir}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="MLB Sharp Betting data scraper")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today, US/Eastern)")
    ap.add_argument("--game-pk", type=int, help="restrict to a single game")
    ap.add_argument("--out", default="./mlb_data", help="output root directory")
    ap.add_argument("--no-odds", action="store_true", help="skip The Odds API call")
    args = ap.parse_args(argv)

    target = date.fromisoformat(args.date) if args.date else date.today()
    out_root = Path(args.out).expanduser().resolve()
    run(target, out_root, single_game_pk=args.game_pk, fetch_odds_flag=not args.no_odds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
