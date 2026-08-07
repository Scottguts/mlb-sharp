# Bankroll Simulation

_Generated 2026-08-07 11:28_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  280 | 140-139- 1 | $10,000.00 | $  9,373.35 |    -6.27% |   -2.36% |  13.18% |
| flat_2u        |  280 | 140-139- 1 | $10,000.00 | $  8,544.94 |   -14.55% |   -2.94% |  25.42% |
| current_ladder |  280 | 140-139- 1 | $10,000.00 | $  9,495.34 |    -5.05% |   -2.00% |  11.84% |
| half_kelly     |  280 | 140-139- 1 | $10,000.00 | $  6,297.71 |   -37.02% |   -4.86% |  49.82% |
| quarter_kelly  |  280 | 140-139- 1 | $10,000.00 | $  7,140.76 |   -28.59% |   -5.36% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   99 |  45- 54- 0 | $10,000.00 | $  9,321.98 |    -6.78% |  -10.29% |   9.66% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   56 |  27- 28- 1 | $10,000.00 | $  9,879.15 |    -1.21% |   -3.26% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   99 |  45- 54- 0 | $10,000.00 | $  8,163.55 |   -18.36% |   -6.75% |  39.16% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   56 |  27- 28- 1 | $10,000.00 | $  8,595.71 |   -14.04% |   -7.04% |  24.42% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|    11 | $ 9,410.54 |
|    22 | $ 9,868.80 |
|    33 | $ 9,840.24 |
|    44 | $ 9,709.91 |
|    55 | $ 9,519.05 |
|    66 | $ 9,822.23 |
|    77 | $ 9,447.76 |
|    88 | $ 9,517.03 |
|    99 | $ 9,361.39 |
|   110 | $ 9,302.57 |
|   121 | $ 9,319.14 |
|   132 | $ 9,332.47 |
|   143 | $ 9,010.36 |
|   154 | $ 9,364.04 |
|   165 | $ 9,916.70 |
|   176 | $ 9,879.16 |
|   187 | $ 9,832.41 |
|   198 | $ 9,283.56 |
|   209 | $ 9,237.71 |
|   220 | $ 9,361.73 |
|   231 | $ 9,500.07 |
|   242 | $ 9,787.44 |
|   253 | $10,033.52 |
|   264 | $ 9,453.05 |
|   275 | $ 9,356.89 |
|   280 | $ 9,495.34 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
