# Model Calibration Backtest

_Generated 2026-04-27 19:58_  
_22,793 games across 10 seasons_


## Per-season RMSE (lower is better)

| Season | Games | RMSE total (baseline) | RMSE total (park-adj) | Δ | RMSE F5 | Brier NRFI | Brier ML |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015 | 2433 | 4.428 | 4.39 | +0.038 | 3.375 | 0.2499 | 0.2483 |
| 2016 | 2429 | 4.485 | 4.437 | +0.048 | 3.451 | 0.2498 | 0.2491 |
| 2017 | 2430 | 4.534 | 4.533 | +0.001 | 3.456 | 0.2497 | 0.2485 |
| 2018 | 2433 | 4.544 | 4.533 | +0.011 | 3.384 | 0.25 | 0.2492 |
| 2019 | 2433 | 4.802 | 4.763 | +0.039 | 3.557 | 0.2498 | 0.2491 |
| 2020 | 900 | 4.556 | 4.501 | +0.055 | 3.54 | 0.25 | 0.2479 |
| 2021 | 2437 | 4.514 | 4.484 | +0.031 | 3.357 | 0.25 | 0.2486 |
| 2022 | 2431 | 4.414 | 4.353 | +0.061 | 3.314 | 0.2502 | 0.2489 |
| 2023 | 2437 | 4.586 | 4.534 | +0.053 | 3.505 | 0.25 | 0.2497 |
| 2024 | 2430 | 4.317 | 4.281 | +0.036 | 3.233 | 0.2504 | 0.2497 |

## Aggregate (full window)

- League mean total runs: **9.005**
- League mean F5 runs: **5.12**
- League NRFI rate: **49.50%**
- Home win pct: **53.21%**
- RMSE total — naive: **4.517**
- RMSE total — park-adjusted: **4.481**
- **Park-adj improvement: +0.036 RMSE**
- RMSE F5 (naive): **3.41**
- Brier NRFI: **0.25** (0.25 = always-50/50)
- Brier ML: **0.249** (0.25 = always-50/50)

## Constants drift check

| Constant | In code | Actual | Drift |
|---|---:|---:|---:|
| LEAGUE_AVG_TOTAL | 8.86 | 9.005 | -0.1450 |
| F5_LEAGUE_AVG | 4.99 | 5.12 | -0.1300 |
| LEAGUE_NRFI_RATE | 0.516 | 0.495 | +0.0210 |
| HOME_FIELD_PROB | 0.025 | 0.0321 | -0.0071 |

## Interpretation

- **Park-adj improvement** must be **positive** for park factors to add value. If it's near zero or negative, the `pf_runs` numbers in PARKS are stale — re-run `historical_validate.py`.

- **Brier NRFI ~0.246** is the perfect-uninformed baseline (Brier of predicting league rate for every game). Any per-game model needs to beat this on a held-out year to add value.

- **RMSE total ~4.3-4.6** is the irreducible variance of MLB scoring. Even a perfect pre-game model can't go below ~3.7-3.8 — that's the noise floor (random variation in per-game outcomes).

- **Drift** in constants > 0.1 (totals) or > 1pp (NRFI) means the codebase needs a refresh from `historical_validate.py`.
