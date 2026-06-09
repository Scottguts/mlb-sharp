# Bankroll Simulation

_Generated 2026-06-09 11:10_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  163 |  81- 81- 1 | $10,000.00 | $  9,653.80 |    -3.46% |   -2.24% |  13.18% |
| flat_2u        |  163 |  81- 81- 1 | $10,000.00 | $  9,166.21 |    -8.34% |   -2.87% |  25.42% |
| current_ladder |  163 |  81- 81- 1 | $10,000.00 | $  9,925.91 |    -0.74% |   -0.63% |  11.24% |
| half_kelly     |  163 |  81- 81- 1 | $10,000.00 | $  7,321.84 |   -26.78% |   -5.88% |  49.82% |
| quarter_kelly  |  163 |  81- 81- 1 | $10,000.00 | $  7,178.18 |   -28.22% |   -8.42% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   80 |  37- 43- 0 | $10,000.00 | $  9,408.35 |    -5.92% |  -10.74% |   9.10% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   47 |  22- 24- 1 | $10,000.00 | $  9,845.51 |    -1.54% |   -4.73% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   80 |  37- 43- 0 | $10,000.00 | $  8,472.50 |   -15.27% |   -6.11% |  38.25% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   47 |  22- 24- 1 | $10,000.00 | $  8,458.95 |   -15.41% |   -8.25% |  24.42% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|     6 | $ 9,644.77 |
|    12 | $ 9,491.20 |
|    18 | $ 9,777.45 |
|    24 | $ 9,770.36 |
|    30 | $ 9,804.25 |
|    36 | $ 9,788.48 |
|    42 | $ 9,807.74 |
|    48 | $ 9,691.24 |
|    54 | $ 9,566.89 |
|    60 | $ 9,699.97 |
|    66 | $ 9,822.23 |
|    72 | $ 9,724.39 |
|    78 | $ 9,400.52 |
|    84 | $ 9,499.88 |
|    90 | $ 9,639.23 |
|    96 | $ 9,505.11 |
|   102 | $ 9,175.33 |
|   108 | $ 9,222.98 |
|   114 | $ 9,558.30 |
|   120 | $ 9,269.09 |
|   126 | $ 9,460.13 |
|   132 | $ 9,332.47 |
|   138 | $ 9,055.96 |
|   144 | $ 8,965.30 |
|   150 | $ 9,408.07 |
|   156 | $ 9,539.58 |
|   162 | $ 9,820.69 |
|   163 | $ 9,925.91 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
