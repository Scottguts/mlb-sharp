# Bankroll Simulation

_Generated 2026-05-22 13:02_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  113 |  54- 58- 1 | $10,000.00 | $  9,440.66 |    -5.59% |   -5.16% |  10.05% |
| flat_2u        |  113 |  54- 58- 1 | $10,000.00 | $  8,808.26 |   -11.92% |   -5.77% |  19.67% |
| current_ladder |  113 |  54- 58- 1 | $10,000.00 | $  9,435.64 |    -5.64% |   -7.38% |   8.81% |
| half_kelly     |  113 |  54- 58- 1 | $10,000.00 | $  6,753.12 |   -32.47% |   -8.92% |  38.84% |
| quarter_kelly  |  113 |  54- 58- 1 | $10,000.00 | $  6,509.85 |   -34.90% |  -12.38% |  41.17% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   52 |  26- 26- 0 | $10,000.00 | $  9,874.03 |    -1.26% |   -3.68% |   6.17% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   39 |  18- 20- 1 | $10,000.00 | $  9,845.98 |    -1.54% |   -5.37% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   52 |  26- 26- 0 | $10,000.00 | $ 10,791.95 |    +7.92% |   +4.33% |  23.87% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   39 |  18- 20- 1 | $10,000.00 | $  8,437.26 |   -15.63% |   -9.03% |  24.42% |

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
|   108 | $ 9,222.98 |
|   112 | $ 9,388.69 |
|   113 | $ 9,435.64 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
