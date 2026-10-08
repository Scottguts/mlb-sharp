# Bankroll Simulation

_Generated 2026-10-08 11:08_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  381 | 191-189- 1 | $10,000.00 | $  9,110.29 |    -8.90% |   -2.49% |  14.59% |
| flat_2u        |  381 | 191-189- 1 | $10,000.00 | $  7,994.69 |   -20.05% |   -3.05% |  29.40% |
| current_ladder |  381 | 191-189- 1 | $10,000.00 | $  8,622.85 |   -13.77% |   -3.81% |  20.91% |
| half_kelly     |  381 | 191-189- 1 | $10,000.00 | $  4,963.92 |   -50.36% |   -5.20% |  61.26% |
| quarter_kelly  |  381 | 191-189- 1 | $10,000.00 | $  6,206.20 |   -37.94% |   -5.54% |  45.77% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |  121 |  56- 65- 0 | $10,000.00 | $  9,365.97 |    -6.34% |   -7.97% |   9.66% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   57 |  28- 28- 1 | $10,000.00 | $  9,927.58 |    -0.72% |   -1.93% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |  121 |  56- 65- 0 | $10,000.00 | $  8,140.12 |   -18.60% |   -6.14% |  39.16% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   57 |  28- 28- 1 | $10,000.00 | $  8,761.26 |   -12.39% |   -6.16% |  24.42% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|    15 | $ 9,784.37 |
|    30 | $ 9,804.25 |
|    45 | $ 9,661.36 |
|    60 | $ 9,699.97 |
|    75 | $ 9,531.11 |
|    90 | $ 9,639.23 |
|   105 | $ 9,164.69 |
|   120 | $ 9,269.09 |
|   135 | $ 9,286.50 |
|   150 | $ 9,408.07 |
|   165 | $ 9,916.70 |
|   180 | $ 9,688.19 |
|   195 | $ 9,386.05 |
|   210 | $ 9,376.28 |
|   225 | $ 9,431.63 |
|   240 | $ 9,892.33 |
|   255 | $ 9,833.60 |
|   270 | $ 9,394.23 |
|   285 | $ 9,339.01 |
|   300 | $ 9,151.01 |
|   315 | $ 9,297.18 |
|   330 | $ 8,800.78 |
|   345 | $ 8,873.01 |
|   360 | $ 8,745.18 |
|   375 | $ 8,271.86 |
|   381 | $ 8,622.85 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
