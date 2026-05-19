# Bankroll Simulation

_Generated 2026-05-19 13:36_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  109 |  50- 58- 1 | $10,000.00 | $  9,102.86 |    -8.97% |   -8.58% |  10.05% |
| flat_2u        |  109 |  50- 58- 1 | $10,000.00 | $  8,191.91 |   -18.08% |   -9.05% |  19.67% |
| current_ladder |  109 |  50- 58- 1 | $10,000.00 | $  9,264.90 |    -7.35% |   -9.85% |   8.81% |
| half_kelly     |  109 |  50- 58- 1 | $10,000.00 | $  6,260.78 |   -37.39% |  -10.43% |  38.84% |
| quarter_kelly  |  109 |  50- 58- 1 | $10,000.00 | $  6,266.91 |   -37.33% |  -13.37% |  41.17% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   49 |  23- 26- 0 | $10,000.00 | $  9,743.84 |    -2.56% |   -7.82% |   6.17% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   38 |  17- 20- 1 | $10,000.00 | $  9,796.99 |    -2.03% |   -7.20% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   49 |  23- 26- 0 | $10,000.00 | $ 10,230.27 |    +2.30% |   +1.30% |  23.87% |
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
|   108 | $ 9,222.98 |
|   109 | $ 9,264.90 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
