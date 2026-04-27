# Bankroll Simulation

_Generated 2026-04-27 13:16_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |   67 |  32- 34- 1 | $10,000.00 | $  9,722.69 |    -2.77% |   -4.27% |   7.87% |
| flat_2u        |   67 |  32- 34- 1 | $10,000.00 | $  9,385.91 |    -6.14% |   -4.89% |  15.55% |
| current_ladder |   67 |  32- 34- 1 | $10,000.00 | $  9,773.12 |    -2.27% |   -4.77% |   6.69% |
| half_kelly     |   67 |  32- 34- 1 | $10,000.00 | $  8,035.20 |   -19.65% |   -7.26% |  37.28% |
| quarter_kelly  |   67 |  32- 34- 1 | $10,000.00 | $  7,307.24 |   -26.93% |  -11.74% |  41.17% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   12 |   6-  6- 0 | $10,000.00 | $ 10,119.28 |    +1.19% |  +17.04% |   1.50% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   33 |  16- 16- 1 | $10,000.00 | $  9,950.98 |    -0.49% |   -1.91% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   12 |   6-  6- 0 | $10,000.00 | $ 11,846.80 |   +18.47% |  +29.85% |   9.75% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   33 |  16- 16- 1 | $10,000.00 | $  9,145.19 |    -8.55% |   -5.57% |  22.99% |

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
|    67 | $ 9,773.12 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
