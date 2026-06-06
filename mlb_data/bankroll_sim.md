# Bankroll Simulation

_Generated 2026-06-06 12:15_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  157 |  76- 80- 1 | $10,000.00 | $  9,381.47 |    -6.19% |   -4.16% |  13.18% |
| flat_2u        |  157 |  76- 80- 1 | $10,000.00 | $  8,659.87 |   -13.40% |   -4.78% |  25.42% |
| current_ladder |  157 |  76- 80- 1 | $10,000.00 | $  9,649.65 |    -3.50% |   -3.15% |  11.24% |
| half_kelly     |  157 |  76- 80- 1 | $10,000.00 | $  6,695.22 |   -33.05% |   -7.53% |  49.82% |
| quarter_kelly  |  157 |  76- 80- 1 | $10,000.00 | $  6,835.89 |   -31.64% |   -9.71% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   79 |  36- 43- 0 | $10,000.00 | $  9,380.76 |    -6.19% |  -11.34% |   9.10% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   46 |  21- 24- 1 | $10,000.00 | $  9,802.51 |    -1.97% |   -6.14% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   79 |  36- 43- 0 | $10,000.00 | $  8,378.88 |   -16.21% |   -6.53% |  38.25% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   46 |  21- 24- 1 | $10,000.00 | $  8,343.13 |   -16.57% |   -8.94% |  24.42% |

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
|   157 | $ 9,649.65 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
