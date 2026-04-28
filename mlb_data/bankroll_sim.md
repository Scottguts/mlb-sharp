# Bankroll Simulation

_Generated 2026-04-28 14:18_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |   72 |  34- 37- 1 | $10,000.00 | $  9,624.75 |    -3.75% |   -5.38% |   7.87% |
| flat_2u        |   72 |  34- 37- 1 | $10,000.00 | $  9,193.11 |    -8.07% |   -5.98% |  15.55% |
| current_ladder |   72 |  34- 37- 1 | $10,000.00 | $  9,724.39 |    -2.76% |   -5.51% |   6.69% |
| half_kelly     |   72 |  34- 37- 1 | $10,000.00 | $  7,599.75 |   -24.00% |   -8.26% |  37.28% |
| quarter_kelly  |   72 |  34- 37- 1 | $10,000.00 | $  6,818.04 |   -31.82% |  -12.97% |  41.17% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   15 |   7-  8- 0 | $10,000.00 | $ 10,074.44 |    +0.74% |   +8.74% |   1.50% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   35 |  17- 17- 1 | $10,000.00 | $  9,945.43 |    -0.55% |   -2.04% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   15 |   7-  8- 0 | $10,000.00 | $ 11,290.48 |   +12.90% |  +16.26% |  14.26% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   35 |  17- 17- 1 | $10,000.00 | $  9,075.78 |    -9.24% |   -5.67% |  22.99% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|     2 | $ 9,850.00 |
|     4 | $ 9,653.74 |
|     6 | $ 9,644.77 |
|     8 | $ 9,616.91 |
|    10 | $ 9,330.56 |
|    12 | $ 9,491.20 |
|    14 | $ 9,655.06 |
|    16 | $ 9,976.22 |
|    18 | $ 9,777.45 |
|    20 | $ 9,869.05 |
|    22 | $ 9,868.80 |
|    24 | $ 9,770.36 |
|    26 | $ 9,824.17 |
|    28 | $ 9,726.18 |
|    30 | $ 9,804.25 |
|    32 | $ 9,797.64 |
|    34 | $ 9,791.04 |
|    36 | $ 9,788.48 |
|    38 | $ 9,832.06 |
|    40 | $ 9,807.98 |
|    42 | $ 9,807.74 |
|    44 | $ 9,709.91 |
|    46 | $ 9,693.78 |
|    48 | $ 9,691.24 |
|    50 | $ 9,667.89 |
|    52 | $ 9,571.46 |
|    54 | $ 9,566.89 |
|    56 | $ 9,558.72 |
|    58 | $ 9,610.31 |
|    60 | $ 9,699.97 |
|    62 | $ 9,706.48 |
|    64 | $ 9,921.20 |
|    66 | $ 9,822.23 |
|    68 | $ 9,724.26 |
|    70 | $ 9,822.37 |
|    72 | $ 9,724.39 |
|    72 | $ 9,724.39 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
