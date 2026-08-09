# Bankroll Simulation

_Generated 2026-08-09 11:10_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  286 | 142-143- 1 | $10,000.00 | $  9,170.91 |    -8.29% |   -3.06% |  13.18% |
| flat_2u        |  286 | 142-143- 1 | $10,000.00 | $  8,175.13 |   -18.25% |   -3.61% |  25.42% |
| current_ladder |  286 | 142-143- 1 | $10,000.00 | $  9,198.93 |    -8.01% |   -3.09% |  11.84% |
| half_kelly     |  286 | 142-143- 1 | $10,000.00 | $  5,647.82 |   -43.52% |   -5.61% |  49.82% |
| quarter_kelly  |  286 | 142-143- 1 | $10,000.00 | $  6,671.81 |   -33.28% |   -6.13% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |  101 |  46- 55- 0 | $10,000.00 | $  9,316.78 |    -6.83% |  -10.22% |   9.66% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   56 |  27- 28- 1 | $10,000.00 | $  9,879.15 |    -1.21% |   -3.26% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |  101 |  46- 55- 0 | $10,000.00 | $  8,150.86 |   -18.49% |   -6.74% |  39.16% |
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
|   286 | $ 9,198.93 |
|   286 | $ 9,198.93 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
