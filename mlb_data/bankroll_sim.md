# Bankroll Simulation

_Generated 2026-04-26 13:47_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |   42 |  19- 22- 1 | $10,000.00 | $  9,349.27 |    -6.51% |  -16.00% |   6.51% |
| flat_2u        |   42 |  19- 22- 1 | $10,000.00 | $  8,710.02 |   -12.90% |  -16.41% |  12.90% |
| current_ladder |   42 |  19- 22- 1 | $10,000.00 | $  9,501.71 |    -4.98% |  -14.58% |   7.83% |
| half_kelly     |   42 |  19- 22- 1 | $10,000.00 | $  6,855.04 |   -31.45% |  -18.72% |  31.45% |
| quarter_kelly  |   42 |  19- 22- 1 | $10,000.00 | $  6,481.12 |   -35.19% |  -25.12% |  35.19% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |    3 |   1-  2- 0 | $10,000.00 | $  9,846.12 |    -1.54% |  -61.87% |   1.54% |
| runline       |   16 |   6- 10- 0 | $10,000.00 | $  9,586.81 |    -4.13% |  -35.22% |   4.13% |
| total         |   23 |  12- 10- 1 | $10,000.00 | $ 10,066.12 |    +0.66% |   +3.19% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |    3 |   1-  2- 0 | $10,000.00 | $  9,248.95 |    -7.51% |  -60.50% |   7.51% |
| runline       |   16 |   6- 10- 0 | $10,000.00 | $  7,146.34 |   -28.54% |  -41.42% |  28.54% |
| total         |   23 |  12- 10- 1 | $10,000.00 | $ 10,371.32 |    +3.71% |   +3.49% |  14.67% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|     1 | $10,000.00 |
|     2 | $ 9,850.00 |
|     3 | $ 9,702.25 |
|     4 | $ 9,653.74 |
|     5 | $ 9,508.93 |
|     6 | $ 9,644.77 |
|     7 | $ 9,500.10 |
|     8 | $ 9,357.60 |
|     9 | $ 9,217.24 |
|    10 | $ 9,296.24 |
|    11 | $ 9,375.92 |
|    12 | $ 9,414.99 |
|    13 | $ 9,537.79 |
|    14 | $ 9,665.53 |
|    15 | $ 9,855.05 |
|    16 | $ 9,707.23 |
|    17 | $ 9,658.69 |
|    18 | $ 9,703.41 |
|    19 | $ 9,749.18 |
|    20 | $ 9,700.43 |
|    21 | $ 9,748.93 |
|    22 | $ 9,700.19 |
|    23 | $ 9,651.69 |
|    24 | $ 9,677.36 |
|    25 | $ 9,704.85 |
|    26 | $ 9,656.33 |
|    27 | $ 9,608.05 |
|    28 | $ 9,636.99 |
|    29 | $ 9,685.17 |
|    30 | $ 9,727.28 |
|    31 | $ 9,678.64 |
|    32 | $ 9,720.72 |
|    33 | $ 9,672.12 |
|    34 | $ 9,623.76 |
|    35 | $ 9,669.59 |
|    36 | $ 9,621.24 |
|    37 | $ 9,645.91 |
|    38 | $ 9,597.68 |
|    39 | $ 9,549.69 |
|    40 | $ 9,597.44 |
|    41 | $ 9,549.45 |
|    42 | $ 9,501.71 |
|    42 | $ 9,501.71 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
