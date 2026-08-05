# Bankroll Simulation

_Generated 2026-08-05 11:27_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  273 | 135-137- 1 | $10,000.00 | $  9,075.22 |    -9.25% |   -3.58% |  13.18% |
| flat_2u        |  273 | 135-137- 1 | $10,000.00 | $  8,016.11 |   -19.84% |   -4.10% |  25.42% |
| current_ladder |  273 | 135-137- 1 | $10,000.00 | $  9,149.30 |    -8.51% |   -3.46% |  11.84% |
| half_kelly     |  273 | 135-137- 1 | $10,000.00 | $  5,657.13 |   -43.43% |   -5.81% |  49.82% |
| quarter_kelly  |  273 | 135-137- 1 | $10,000.00 | $  6,659.81 |   -33.40% |   -6.38% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   96 |  43- 53- 0 | $10,000.00 | $  9,269.36 |    -7.31% |  -11.33% |   9.66% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   56 |  27- 28- 1 | $10,000.00 | $  9,879.15 |    -1.21% |   -3.26% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   96 |  43- 53- 0 | $10,000.00 | $  8,086.73 |   -19.13% |   -7.12% |  39.16% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   56 |  27- 28- 1 | $10,000.00 | $  8,595.71 |   -14.04% |   -7.04% |  24.42% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|    10 | $ 9,330.56 |
|    20 | $ 9,869.05 |
|    30 | $ 9,804.25 |
|    40 | $ 9,807.98 |
|    50 | $ 9,667.89 |
|    60 | $ 9,699.97 |
|    70 | $ 9,822.37 |
|    80 | $ 9,406.97 |
|    90 | $ 9,639.23 |
|   100 | $ 9,267.77 |
|   110 | $ 9,302.57 |
|   120 | $ 9,269.09 |
|   130 | $ 9,474.11 |
|   140 | $ 8,875.52 |
|   150 | $ 9,408.07 |
|   160 | $ 9,941.01 |
|   170 | $10,319.07 |
|   180 | $ 9,688.19 |
|   190 | $ 9,854.59 |
|   200 | $ 9,258.61 |
|   210 | $ 9,376.28 |
|   220 | $ 9,361.73 |
|   230 | $ 9,644.74 |
|   240 | $ 9,892.33 |
|   250 | $ 9,977.89 |
|   260 | $ 9,891.03 |
|   270 | $ 9,394.23 |
|   273 | $ 9,149.30 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
