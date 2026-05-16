# Bankroll Simulation

_Generated 2026-05-16 11:43_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  105 |  48- 56- 1 | $10,000.00 | $  9,103.87 |    -8.96% |   -8.87% |   9.15% |
| flat_2u        |  105 |  48- 56- 1 | $10,000.00 | $  8,197.04 |   -18.03% |   -9.32% |  18.03% |
| current_ladder |  105 |  48- 56- 1 | $10,000.00 | $  9,164.69 |    -8.35% |  -11.62% |   8.35% |
| half_kelly     |  105 |  48- 56- 1 | $10,000.00 | $  6,253.07 |   -37.47% |  -10.63% |  37.47% |
| quarter_kelly  |  105 |  48- 56- 1 | $10,000.00 | $  6,260.91 |   -37.39% |  -13.55% |  41.17% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   45 |  21- 24- 0 | $10,000.00 | $  9,638.45 |    -3.62% |  -12.11% |   5.70% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   38 |  17- 20- 1 | $10,000.00 | $  9,796.99 |    -2.03% |   -7.20% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   45 |  21- 24- 0 | $10,000.00 | $ 10,217.68 |    +2.18% |   +1.31% |  23.26% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   38 |  17- 20- 1 | $10,000.00 | $  8,251.60 |   -17.48% |  -10.21% |  24.42% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|     4 | $ 9,653.74 |
|     8 | $ 9,616.91 |
|    12 | $ 9,491.20 |
|    16 | $ 9,976.22 |
|    20 | $ 9,869.05 |
|    24 | $ 9,770.36 |
|    28 | $ 9,726.18 |
|    32 | $ 9,797.64 |
|    36 | $ 9,788.48 |
|    40 | $ 9,807.98 |
|    44 | $ 9,709.91 |
|    48 | $ 9,691.24 |
|    52 | $ 9,571.46 |
|    56 | $ 9,558.72 |
|    60 | $ 9,699.97 |
|    64 | $ 9,921.20 |
|    68 | $ 9,724.26 |
|    72 | $ 9,724.39 |
|    76 | $ 9,388.15 |
|    80 | $ 9,406.97 |
|    84 | $ 9,499.88 |
|    88 | $ 9,517.03 |
|    92 | $ 9,692.22 |
|    96 | $ 9,505.11 |
|   100 | $ 9,267.77 |
|   104 | $ 9,210.74 |
|   105 | $ 9,164.69 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
