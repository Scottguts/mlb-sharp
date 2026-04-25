# MLB Sharp Betting — Data Scraper

Companion to `MLB_Sharp_Betting_System.md`. Pulls every input the grading
formula needs into JSON files you can feed into your model.

## What it scrapes

| Source | Data | Auth |
|---|---|---|
| MLB Stats API | schedule, probables, lineups, umpires, box scores, bullpen usage | none |
| Baseball Savant (via `pybaseball`) | per-pitch Statcast for each starter — velo trend, pitch mix, splits, CSW%, hard-hit, xwOBA | none |
| FanGraphs (via `pybaseball`) | season team batting / pitching, optional rate stats | none |
| Open-Meteo | first-pitch temp, humidity, dew point, wind speed/dir, precip prob — looked up by park lat/lng | none |
| Static park table (in script) | run/HR factors per ballpark, roof type | n/a |
| The Odds API | multi-book ML, run line, totals across Pinnacle, FanDuel, DK, MGM, Caesars, ESPN BET | free key (set `ODDS_API_KEY`) |

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
# Today's slate, full pull
python mlb_data_scraper.py

# Specific date
python mlb_data_scraper.py --date 2026-04-25

# Single game
python mlb_data_scraper.py --game-pk 745432

# Skip odds (if you don't have a key yet)
python mlb_data_scraper.py --no-odds

# Custom output dir
python mlb_data_scraper.py --out ~/mlb_data
```

## Output layout

```
mlb_data/
└── 2026-04-25/
    ├── slate.json                  # schedule + probables (summary)
    ├── odds.json                   # raw multi-book odds snapshot
    └── games/
        ├── 745432.json             # full per-game payload
        ├── 745433.json
        └── ...
```

Each per-game JSON contains:

```jsonc
{
  "gamePk": 745432,
  "gameDate": "2026-04-25T23:05:00Z",
  "venue":   { "name": "...", "roof": "...", "pf_runs": 102, ... },
  "weather": { "temp_f": 74, "wind_mph": 8, "wind_dir_deg": 200, ... },
  "lineups": { "lineups_confirmed": true, "away_lineup": [...], "home_lineup": [...], "umpires": [...] },
  "away": {
      "team_id": 139, "team_name": "Tampa Bay Rays",
      "probable_pitcher_id": 663556, "probable_pitcher_name": "Shane McClanahan",
      "pitcher_profile": { "season_avg_velo": 95.8, "starts": [...], "splits": {"L": {...}, "R": {...}}, "pitch_mix": {...} },
      "bullpen_usage":   { "relievers": { "664143": { "pitches": 22, "back_to_back": true, "pitched_yesterday": true, ... } } }
  },
  "home": { ... }
}
```

## Helpers included

The script also exposes pure utility functions you can import into a model:

```python
from mlb_data_scraper import (
    american_to_prob, prob_to_american,
    devig_two_way, edge_pct,
)

# Example: devig Pinnacle to get fair price, then check edge at FanDuel
fair_a, fair_b = devig_two_way(-115, +105)   # Pinnacle two-way
my_edge = edge_pct(fair_a, +110)             # do you have 3%+ vs FanDuel +110?
```

## Notes & gotchas

- **Lineups + umpires** only populate close to first pitch. Re-run within ~2h of game time to capture them.
- **`pybaseball` first run** caches a Chadwick player ID lookup file (~30s). Subsequent runs are fast.
- **The Odds API free tier** is ~500 requests/month — one slate pull per day fits easily.
- **Park factors** in the script are a starting point. Refresh annually with current Statcast values.
- **Rate limit politeness**: this script does basic exponential backoff. Don't hammer the MLB API in tight loops.
- **Time zones**: schedule timestamps are UTC; weather lookup converts internally. If you want first-pitch ET printed, format `gameDate` after fetch.
- **Live betting**: the live feed endpoint (`/feed/live`) used for lineups is also where you'd poll in-game state for live-bet automation.

## Suggested next steps

1. Wire the per-game JSON into a Python class that produces the 0–100 grade per the system doc.
2. Compare your model's fair odds vs `odds.json` and emit a betting card.
3. Append every bet + closing line to a Google Sheet or Postgres table for CLV tracking.
