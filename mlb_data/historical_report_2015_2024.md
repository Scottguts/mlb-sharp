# Historical MLB Validation

_Generated 2026-04-27 19:59_  
_Source: statsapi.mlb.com (regular-season finals only)_  
_Window: 2015–2024, 22,793 games, 45 unique venues_


## Yearly League Baselines

Use these to refresh the constants in `mlb_grader.py`. The trailing average across the window is the safest default.

| Season | Games | μ Total | μ F5 | NRFI rate | Home win % |
|---:|---:|---:|---:|---:|---:|
| 2015 | 2433 | 8.50 | 4.87 | 49.2% | 54.2% |
| 2016 | 2429 | 8.95 | 5.13 | 47.8% | 53.0% |
| 2017 | 2430 | 9.29 | 5.38 | 46.9% | 53.9% |
| 2018 | 2433 | 8.89 | 5.00 | 49.7% | 52.8% |
| 2019 | 2433 | 9.66 | 5.45 | 47.4% | 52.9% |
| 2020 | 900 | 9.29 | 5.43 | 49.9% | 54.9% |
| 2021 | 2437 | 9.06 | 5.15 | 49.6% | 53.8% |
| 2022 | 2431 | 8.57 | 4.82 | 51.8% | 53.3% |
| 2023 | 2437 | 9.22 | 5.23 | 49.7% | 52.1% |
| 2024 | 2430 | 8.78 | 4.94 | 53.3% | 52.1% |

**Recommended constants** (last 3 seasons, 2022–2024):

```python
LEAGUE_AVG_TOTAL = 8.86    # mlb_grader.py
F5_LEAGUE_AVG    = 4.99
LEAGUE_NRFI_RATE = 0.5160
HOME_FIELD_PROB  = +0.0249  # home win pct minus 50%; current code uses 0.030
```

## Park Factors (last 3 seasons)

Computed as `(avg_total_at_park / league_avg_total) × 100`. 
Compare these to the `pf_runs` values in `PARKS` (mlb_data_scraper.py).

| venue_id | Park | Games | avg total | avg F5 | NRFI rate | pf_runs |
|---:|---|---:|---:|---:|---:|---:|
| 19 | Coors Field | 241 | 11.34 | 6.27 | 44.4% | 128 |
| 3 | Fenway Park | 245 | 9.80 | 5.54 | 47.8% | 111 |
| 2602 | Great American Ball Park | 243 | 9.59 | 5.56 | 54.3% | 108 |
| 15 | Chase Field | 243 | 9.51 | 5.37 | 47.7% | 107 |
| 7 | Kauffman Stadium | 243 | 9.41 | 4.88 | 51.9% | 106 |
| 5325 | Globe Life Field | 243 | 9.28 | 5.35 | 51.9% | 105 |
| 3309 | Nationals Park | 243 | 9.14 | 5.41 | 52.7% | 103 |
| 2681 | Citizens Bank Park | 242 | 9.12 | 5.05 | 49.6% | 103 |
| 31 | PNC Park | 243 | 9.08 | 4.93 | 53.9% | 103 |
| 4169 | loanDepot park | 243 | 9.01 | 4.94 | 56.0% | 102 |
| 1 | Angel Stadium | 243 | 8.93 | 5.01 | 50.6% | 101 |
| 3312 | Target Field | 243 | 8.88 | 5.04 | 51.0% | 100 |
| 4705 | Truist Park | 243 | 8.89 | 5.16 | 49.4% | 100 |
| 22 | Dodger Stadium | 242 | 8.90 | 5.14 | 47.5% | 100 |
| 2889 | Busch Stadium | 242 | 8.88 | 5.02 | 52.1% | 100 |
| 4 | Guaranteed Rate Field | 244 | 8.70 | 4.58 | 53.7% | 98 |
| 14 | Rogers Centre | 243 | 8.70 | 4.91 | 54.3% | 98 |
| 3313 | Yankee Stadium | 243 | 8.69 | 4.84 | 49.0% | 98 |
| 2 | Oriole Park at Camden Yards | 242 | 8.63 | 5.19 | 51.7% | 97 |
| 2392 | Minute Maid Park | 242 | 8.57 | 4.91 | 50.0% | 97 |
| 32 | American Family Field | 243 | 8.53 | 4.93 | 49.8% | 96 |
| 10 | Oakland Coliseum | 242 | 8.51 | 4.66 | 56.2% | 96 |
| 3289 | Citi Field | 243 | 8.40 | 4.71 | 55.6% | 95 |
| 17 | Wrigley Field | 243 | 8.45 | 4.86 | 50.6% | 95 |
| 2394 | Comerica Park | 244 | 8.36 | 4.66 | 50.0% | 94 |
| 2395 | Oracle Park | 243 | 8.23 | 4.63 | 57.2% | 93 |
| 12 | Tropicana Field | 243 | 8.21 | 4.60 | 53.5% | 93 |
| 5 | Progressive Field | 243 | 8.18 | 4.67 | 49.0% | 92 |
| 2680 | Petco Park | 240 | 8.06 | 4.52 | 52.1% | 91 |
| 680 | T-Mobile Park | 243 | 7.60 | 4.32 | 56.8% | 86 |

## Naive-predictor RMSE per season

This is the RMSE you'd get predicting **the season's league mean** for every game. 
Any actual model needs to beat this number on a held-out year to provide value.

| Season | Games | League μ_total | RMSE if predicting μ |
|---:|---:|---:|---:|
| 2015 | 2433 | 8.50 | 4.40 |
| 2016 | 2429 | 8.95 | 4.49 |
| 2017 | 2430 | 9.29 | 4.52 |
| 2018 | 2433 | 8.89 | 4.54 |
| 2019 | 2433 | 9.66 | 4.76 |
| 2020 | 900 | 9.29 | 4.55 |
| 2021 | 2437 | 9.06 | 4.51 |
| 2022 | 2431 | 8.57 | 4.39 |
| 2023 | 2437 | 9.22 | 4.58 |
| 2024 | 2430 | 8.78 | 4.31 |

## How to apply this report

1. Open `mlb_grader.py` and update `LEAGUE_AVG_TOTAL`, `F5_LEAGUE_AVG`, and `LEAGUE_NRFI_RATE` to match the **Recommended constants** block above. These are only used as fallback when the market line is unavailable, but keeping them current avoids weird grades on rare no-odds days.

2. Open `mlb_data_scraper.py` and compare each park's `pf_runs` to the table above. If any park is off by more than 3 points, update it in the `PARKS` dict.

3. The system's *forward-looking* proof-of-edge is CLV (`closing_snapshot.py` → `record.md`). This historical report validates the *baseline calibration*, not the betting strategy itself. Pair the two to spot drift.
