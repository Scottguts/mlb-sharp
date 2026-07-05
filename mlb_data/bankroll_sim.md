# Bankroll Simulation

_Generated 2026-07-05 11:13_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  210 | 104-105- 1 | $10,000.00 | $  9,338.59 |    -6.61% |   -3.32% |  13.18% |
| flat_2u        |  210 | 104-105- 1 | $10,000.00 | $  8,539.97 |   -14.60% |   -3.90% |  25.42% |
| current_ladder |  210 | 104-105- 1 | $10,000.00 | $  9,376.28 |    -6.24% |   -3.54% |  11.38% |
| half_kelly     |  210 | 104-105- 1 | $10,000.00 | $  6,087.58 |   -39.12% |   -6.67% |  49.82% |
| quarter_kelly  |  210 | 104-105- 1 | $10,000.00 | $  6,856.85 |   -31.43% |   -7.54% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   85 |  39- 46- 0 | $10,000.00 | $  9,392.64 |    -6.07% |  -10.40% |   9.10% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   51 |  25- 25- 1 | $10,000.00 | $  9,936.14 |    -0.64% |   -1.85% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   85 |  39- 46- 0 | $10,000.00 | $  8,425.56 |   -15.74% |   -6.16% |  38.25% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   51 |  25- 25- 1 | $10,000.00 | $  8,731.87 |   -12.68% |   -6.60% |  24.42% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|     8 | $ 9,616.91 |
|    16 | $ 9,976.22 |
|    24 | $ 9,770.36 |
|    32 | $ 9,797.64 |
|    40 | $ 9,807.98 |
|    48 | $ 9,691.24 |
|    56 | $ 9,558.72 |
|    64 | $ 9,921.20 |
|    72 | $ 9,724.39 |
|    80 | $ 9,406.97 |
|    88 | $ 9,517.03 |
|    96 | $ 9,505.11 |
|   104 | $ 9,210.74 |
|   112 | $ 9,388.69 |
|   120 | $ 9,269.09 |
|   128 | $ 9,452.71 |
|   136 | $ 9,147.20 |
|   144 | $ 8,965.30 |
|   152 | $ 9,317.91 |
|   160 | $ 9,941.01 |
|   168 | $10,308.76 |
|   176 | $ 9,879.16 |
|   184 | $ 9,649.31 |
|   192 | $ 9,561.17 |
|   200 | $ 9,258.61 |
|   208 | $ 9,284.13 |
|   210 | $ 9,376.28 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
