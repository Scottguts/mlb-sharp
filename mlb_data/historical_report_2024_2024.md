# Historical MLB Validation

_Generated 2026-04-27 19:37_  
_Source: statsapi.mlb.com (regular-season finals only)_  
_Window: 2024–2024, 2,430 games, 35 unique venues_


## Yearly League Baselines

Use these to refresh the constants in `mlb_grader.py`. The trailing average across the window is the safest default.

| Season | Games | μ Total | μ F5 | NRFI rate | Home win % |
|---:|---:|---:|---:|---:|---:|
| 2024 | 2430 | 8.78 | 4.94 | 53.3% | 52.1% |

**Recommended constants** (last 3 seasons, 2024–2024):

```python
LEAGUE_AVG_TOTAL = 8.78    # mlb_grader.py
F5_LEAGUE_AVG    = 4.94
LEAGUE_NRFI_RATE = 0.5329
HOME_FIELD_PROB  = +0.0214  # home win pct minus 50%; current code uses 0.030
```

## Park Factors (last 3 seasons)

Computed as `(avg_total_at_park / league_avg_total) × 100`. 
Compare these to the `pf_runs` values in `PARKS` (mlb_data_scraper.py).

| venue_id | Park | Games | avg total | avg F5 | NRFI rate | pf_runs |
|---:|---|---:|---:|---:|---:|---:|
| 15 | Chase Field | 81 | 10.73 | 6.31 | 51.9% | 122 |
| 4169 | loanDepot park | 81 | 10.27 | 5.64 | 42.0% | 117 |
| 3312 | Target Field | 80 | 9.51 | 5.31 | 47.5% | 108 |
| 3 | Fenway Park | 82 | 9.37 | 5.16 | 48.8% | 107 |
| 2602 | Great American Ball Park | 81 | 9.19 | 5.19 | 60.5% | 105 |
| 3313 | Yankee Stadium | 81 | 9.21 | 5.23 | 55.6% | 105 |
| 2681 | Citizens Bank Park | 80 | 9.01 | 4.92 | 51.2% | 103 |
| 7 | Kauffman Stadium | 81 | 9.04 | 4.58 | 50.6% | 103 |
| 31 | PNC Park | 81 | 9.02 | 5.00 | 53.1% | 103 |
| 1 | Angel Stadium | 81 | 8.96 | 5.38 | 51.9% | 102 |
| 2 | Oriole Park at Camden Yards | 81 | 8.95 | 5.47 | 49.4% | 102 |
| 14 | Rogers Centre | 81 | 9.00 | 4.86 | 53.1% | 102 |
| 2392 | Minute Maid Park | 80 | 8.85 | 4.71 | 55.0% | 101 |
| 22 | Dodger Stadium | 80 | 8.89 | 5.17 | 46.2% | 101 |
| 3289 | Citi Field | 80 | 8.84 | 4.81 | 65.0% | 101 |
| 2680 | Petco Park | 80 | 8.75 | 4.71 | 51.2% | 100 |
| 3309 | Nationals Park | 81 | 8.69 | 5.00 | 61.7% | 99 |
| 5 | Progressive Field | 80 | 8.66 | 5.28 | 50.0% | 99 |
| 10 | Oakland Coliseum | 81 | 8.64 | 4.93 | 50.6% | 98 |
| 32 | American Family Field | 81 | 8.52 | 5.04 | 48.1% | 97 |
| 2889 | Busch Stadium | 81 | 8.35 | 4.70 | 65.4% | 95 |
| 2395 | Oracle Park | 81 | 8.28 | 4.59 | 53.1% | 94 |
| 2394 | Comerica Park | 80 | 8.16 | 4.39 | 48.8% | 93 |
| 5325 | Globe Life Field | 81 | 8.04 | 4.43 | 55.6% | 91 |
| 12 | Tropicana Field | 81 | 7.79 | 4.16 | 60.5% | 89 |
| 4 | Guaranteed Rate Field | 82 | 7.83 | 4.26 | 57.3% | 89 |
| 4705 | Truist Park | 81 | 7.79 | 4.74 | 46.9% | 89 |
| 17 | Wrigley Field | 81 | 7.35 | 4.25 | 60.5% | 84 |
| 680 | T-Mobile Park | 81 | 6.93 | 3.65 | 66.7% | 79 |

## Naive-predictor RMSE per season

This is the RMSE you'd get predicting **the season's league mean** for every game. 
Any actual model needs to beat this number on a held-out year to provide value.

| Season | Games | League μ_total | RMSE if predicting μ |
|---:|---:|---:|---:|
| 2024 | 2430 | 8.78 | 4.31 |

## How to apply this report

1. Open `mlb_grader.py` and update `LEAGUE_AVG_TOTAL`, `F5_LEAGUE_AVG`, and `LEAGUE_NRFI_RATE` to match the **Recommended constants** block above. These are only used as fallback when the market line is unavailable, but keeping them current avoids weird grades on rare no-odds days.

2. Open `mlb_data_scraper.py` and compare each park's `pf_runs` to the table above. If any park is off by more than 3 points, update it in the `PARKS` dict.

3. The system's *forward-looking* proof-of-edge is CLV (`closing_snapshot.py` → `record.md`). This historical report validates the *baseline calibration*, not the betting strategy itself. Pair the two to spot drift.
