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
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, date, timezone
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

def _get(url: str, params: dict | None = None, retries: int = 3, timeout: int = 30) -> dict:
    """GET JSON with simple retry."""
    headers = {"User-Agent": USER_AGENT}
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(1.5 ** i)
    return {}


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
    for o in game_data.get("officials", []) or []:
        umps.append({
            "type": o.get("officialType"),
            "id": o.get("official", {}).get("id"),
            "name": o.get("official", {}).get("fullName"),
        })

    return {
        "lineups_confirmed": bool(box.get("teams", {}).get("home", {}).get("battingOrder")),
        "away_lineup": _lineup("away"),
        "home_lineup": _lineup("home"),
        "umpires": umps,
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

    # Per-start rollup
    starts = (
        df.groupby("game_date")
          .agg(
              pitches=("pitch_type", "count"),
              avg_velo=("release_speed", "mean"),
              max_velo=("release_speed", "max"),
              csw=("description", lambda s: ((s == "called_strike") | (s == "swinging_strike")).mean()),
              hard_hit=("launch_speed", lambda s: (s >= 95).mean(skipna=True)),
              barrel=("launch_speed_angle", lambda s: (s == 6).mean(skipna=True)) if "launch_speed_angle" in df.columns else None,
          )
          .reset_index()
          .sort_values("game_date", ascending=False)
    )

    # Pitch mix
    mix = (
        df.groupby("pitch_type").size().div(len(df)).round(3).to_dict()
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


def fetch_top_of_order_quality(lineup: list[dict], season: int,
                                vs_hand: str | None = None) -> dict:
    """Pull season wOBA/OPS/K% for the top 3 batters in a lineup.

    `vs_hand` should be 'L' or 'R' to pull split stats vs LHP/RHP. If splits
    aren't available the season aggregate is returned. Used by NRFI/F5/total
    models since the top of the order is what scores in early innings.
    """
    if not lineup:
        return {"available": False, "reason": "no_lineup"}
    top3 = lineup[:3]
    out = {"available": True, "season": season, "vs_hand": vs_hand,
           "batters": [], "avg_woba": None, "avg_ops": None, "avg_k_pct": None}
    wobas: list[float] = []
    opss:  list[float] = []
    kpcts: list[float] = []
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
        out["batters"].append({
            "id": pid, "name": b.get("name"),
            "ab": int(ab), "ops": ops, "avg": avg,
            "obp": obp, "slg": slg, "woba": round(woba, 3),
            "k_pct": round(k_pct, 3),
        })
        wobas.append(woba); opss.append(ops); kpcts.append(k_pct)
    if wobas:
        out["avg_woba"] = round(sum(wobas) / len(wobas), 3)
        out["avg_ops"] = round(sum(opss) / len(opss), 3)
        out["avg_k_pct"] = round(sum(kpcts) / len(kpcts), 3)
    return out


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
                "date": g["gameDate"][:10],
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
            box = _get(f"{MLB_API}/game/{g['gamePk']}/boxscore")
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
                # Per-pitcher usage
                usage.setdefault(pid, {
                    "name": p["person"]["fullName"],
                    "appearances": 0, "pitches": 0, "ip": 0.0,
                    "dates": [],
                })
                usage[pid]["appearances"] += 1
                usage[pid]["pitches"] += int(pstats.get("numberOfPitches", 0) or 0)
                usage[pid]["ip"] += ip
                usage[pid]["dates"].append(g["gameDate"][:10])
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
# User-facing books we actually shop on:
TARGET_BOOKS    = ("fanduel", "draftkings", "betmgm", "caesars")
# Sharp anchor used only for devig math (not displayed as a "best book"):
SHARP_ANCHORS   = ("pinnacle",)
# Markets we want for every game:
FULL_MARKETS    = ("h2h", "spreads", "totals")            # full game ML / RL / total
F5_MARKETS      = ("totals_1st_5_innings",)               # F5 totals only
INNING_MARKETS  = ("totals_1st_1_innings",)               # 1st-inning totals → NRFI/YRFI proxy

ALL_MARKETS     = FULL_MARKETS + F5_MARKETS + INNING_MARKETS
ALL_BOOKS       = TARGET_BOOKS + SHARP_ANCHORS


def fetch_odds(api_key: str | None = None,
               markets: tuple[str, ...] = ALL_MARKETS,
               books:   tuple[str, ...] = ALL_BOOKS) -> dict:
    """Multi-book MLB odds.

    Returns a single payload covering full-game ML/RL/total, F5 totals,
    and 1st-inning totals (used as the NRFI/YRFI proxy — Over 0.5 = YRFI,
    Under 0.5 = NRFI). Requires The Odds API key (free tier exists).
    """
    api_key = api_key or os.environ.get("ODDS_API_KEY")
    if not api_key:
        return {"available": False, "reason": "ODDS_API_KEY not set"}
    url = f"{ODDS_API}/sports/baseball_mlb/odds"
    # Note: alternate / inning markets often require multiple calls per
    # The Odds API quota policy. We try the combined call first; if a market
    # is rejected we degrade gracefully and fetch what we can.
    payload: dict[str, Any] = {
        "available": True,
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "books_used": list(books),
        "markets_requested": list(markets),
        "games": [],
        "errors": [],
    }
    try:
        data = _get(url, params={
            "apiKey":    api_key,
            "regions":   "us,us2,eu",
            "markets":   ",".join(markets),
            "oddsFormat": "american",
            "bookmakers": ",".join(books),
        })
        payload["games"] = data
    except Exception as e:
        payload["errors"].append(f"combined call failed: {e}")
        # Fall back to the core full-game markets that are always supported
        try:
            data = _get(url, params={
                "apiKey":    api_key,
                "regions":   "us,us2,eu",
                "markets":   ",".join(FULL_MARKETS),
                "oddsFormat": "american",
                "bookmakers": ",".join(books),
            })
            payload["games"] = data
            payload["errors"].append("fell back to full-game markets only")
        except Exception as e2:
            payload["available"] = False
            payload["errors"].append(f"fallback failed: {e2}")
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
