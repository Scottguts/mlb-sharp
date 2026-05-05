# Bankroll Simulation

_Generated 2026-05-05 13:12_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |   89 |  42- 46- 1 | $10,000.00 | $  9,576.33 |    -4.24% |   -4.94% |   8.42% |
| flat_2u        |   89 |  42- 46- 1 | $10,000.00 | $  9,083.64 |    -9.16% |   -5.56% |  16.50% |
| current_ladder |   89 |  42- 46- 1 | $10,000.00 | $  9,583.65 |    -4.16% |   -6.94% |   6.69% |
| half_kelly     |   89 |  42- 46- 1 | $10,000.00 | $  7,118.17 |   -28.82% |   -8.94% |  37.28% |
| quarter_kelly  |   89 |  42- 46- 1 | $10,000.00 | $  6,610.32 |   -33.90% |  -13.02% |  41.17% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   30 |  15- 15- 0 | $10,000.00 | $ 10,028.67 |    +0.29% |   +1.60% |   4.84% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   37 |  17- 19- 1 | $10,000.00 | $  9,846.22 |    -1.54% |   -5.55% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   30 |  15- 15- 0 | $10,000.00 | $ 11,344.51 |   +13.45% |  +11.14% |  23.26% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   37 |  17- 19- 1 | $10,000.00 | $  8,460.19 |   -15.40% |   -9.11% |  22.99% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|     3 | $ 9,702.25 |
|     6 | $ 9,644.77 |
|     9 | $ 9,472.65 |
|    12 | $ 9,491.20 |
|    15 | $ 9,784.37 |
|    18 | $ 9,777.45 |
|    21 | $ 9,819.70 |
|    24 | $ 9,770.36 |
|    27 | $ 9,775.05 |
|    30 | $ 9,804.25 |
|    33 | $ 9,840.24 |
|    36 | $ 9,788.48 |
|    39 | $ 9,857.27 |
|    42 | $ 9,807.74 |
|    45 | $ 9,661.36 |
|    48 | $ 9,691.24 |
|    51 | $ 9,619.55 |
|    54 | $ 9,566.89 |
|    57 | $ 9,510.92 |
|    60 | $ 9,699.97 |
|    63 | $ 9,813.25 |
|    66 | $ 9,822.23 |
|    69 | $ 9,767.67 |
|    72 | $ 9,724.39 |
|    75 | $ 9,531.11 |
|    78 | $ 9,400.52 |
|    81 | $ 9,446.16 |
|    84 | $ 9,499.88 |
|    87 | $ 9,564.85 |
|    89 | $ 9,583.65 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
