# Bankroll Simulation

_Generated 2026-05-26 00:25_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  122 |  58- 63- 1 | $10,000.00 | $  9,368.86 |    -6.31% |   -5.40% |  10.05% |
| flat_2u        |  122 |  58- 63- 1 | $10,000.00 | $  8,666.40 |   -13.34% |   -5.99% |  19.67% |
| current_ladder |  122 |  58- 63- 1 | $10,000.00 | $  9,225.95 |    -7.74% |   -9.26% |   8.81% |
| half_kelly     |  122 |  58- 63- 1 | $10,000.00 | $  6,193.07 |   -38.07% |  -10.00% |  38.84% |
| quarter_kelly  |  122 |  58- 63- 1 | $10,000.00 | $  6,240.57 |   -37.59% |  -12.97% |  41.17% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   60 |  29- 31- 0 | $10,000.00 | $  9,609.28 |    -3.91% |   -9.50% |   6.17% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   40 |  19- 20- 1 | $10,000.00 | $  9,892.42 |    -1.08% |   -3.69% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   60 |  29- 31- 0 | $10,000.00 | $  9,725.55 |    -2.74% |   -1.32% |  25.91% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   40 |  19- 20- 1 | $10,000.00 | $  8,585.96 |   -14.14% |   -8.10% |  24.42% |

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
|   116 | $ 9,508.21 |
|   120 | $ 9,269.09 |
|   122 | $ 9,225.95 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
