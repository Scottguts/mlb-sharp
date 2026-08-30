# Bankroll Simulation

_Generated 2026-08-30 11:10_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  320 | 159-160- 1 | $10,000.00 | $  9,133.11 |    -8.67% |   -2.87% |  13.18% |
| flat_2u        |  320 | 159-160- 1 | $10,000.00 | $  8,080.17 |   -19.20% |   -3.43% |  25.42% |
| current_ladder |  320 | 159-160- 1 | $10,000.00 | $  9,088.20 |    -9.12% |   -3.09% |  13.96% |
| half_kelly     |  320 | 159-160- 1 | $10,000.00 | $  5,264.20 |   -47.36% |   -5.61% |  51.74% |
| quarter_kelly  |  320 | 159-160- 1 | $10,000.00 | $  6,504.55 |   -34.95% |   -5.93% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |  113 |  53- 60- 0 | $10,000.00 | $  9,461.75 |    -5.38% |   -7.20% |   9.66% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   56 |  27- 28- 1 | $10,000.00 | $  9,879.15 |    -1.21% |   -3.26% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |  113 |  53- 60- 0 | $10,000.00 | $  8,415.97 |   -15.84% |   -5.45% |  39.16% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   56 |  27- 28- 1 | $10,000.00 | $  8,595.71 |   -14.04% |   -7.04% |  24.42% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|    12 | $ 9,491.20 |
|    24 | $ 9,770.36 |
|    36 | $ 9,788.48 |
|    48 | $ 9,691.24 |
|    60 | $ 9,699.97 |
|    72 | $ 9,724.39 |
|    84 | $ 9,499.88 |
|    96 | $ 9,505.11 |
|   108 | $ 9,222.98 |
|   120 | $ 9,269.09 |
|   132 | $ 9,332.47 |
|   144 | $ 8,965.30 |
|   156 | $ 9,539.58 |
|   168 | $10,308.76 |
|   180 | $ 9,688.19 |
|   192 | $ 9,561.17 |
|   204 | $ 9,317.15 |
|   216 | $ 9,120.88 |
|   228 | $ 9,591.10 |
|   240 | $ 9,892.33 |
|   252 | $ 9,875.02 |
|   264 | $ 9,453.05 |
|   276 | $ 9,216.54 |
|   288 | $ 9,229.85 |
|   300 | $ 9,151.01 |
|   312 | $ 9,377.99 |
|   320 | $ 9,088.20 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
