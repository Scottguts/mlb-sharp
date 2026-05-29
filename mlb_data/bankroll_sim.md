# Bankroll Simulation

_Generated 2026-05-29 14:24_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  130 |  62- 67- 1 | $10,000.00 | $  9,427.07 |    -5.73% |   -4.61% |  10.05% |
| flat_2u        |  130 |  62- 67- 1 | $10,000.00 | $  8,766.03 |   -12.34% |   -5.22% |  19.67% |
| current_ladder |  130 |  62- 67- 1 | $10,000.00 | $  9,474.11 |    -5.26% |   -5.90% |   8.81% |
| half_kelly     |  130 |  62- 67- 1 | $10,000.00 | $  6,235.12 |   -37.65% |   -9.60% |  41.33% |
| quarter_kelly  |  130 |  62- 67- 1 | $10,000.00 | $  6,266.05 |   -37.34% |  -12.63% |  41.17% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   67 |  33- 34- 0 | $10,000.00 | $  9,917.33 |    -0.83% |   -1.78% |   6.92% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   41 |  19- 21- 1 | $10,000.00 | $  9,842.96 |    -1.57% |   -5.29% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   67 |  33- 34- 0 | $10,000.00 | $ 10,071.75 |    +0.72% |   +0.32% |  29.82% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   41 |  19- 21- 1 | $10,000.00 | $  8,347.12 |   -16.53% |   -9.34% |  24.42% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|     5 | $ 9,508.93 |
|    10 | $ 9,330.56 |
|    15 | $ 9,784.37 |
|    20 | $ 9,869.05 |
|    25 | $ 9,796.34 |
|    30 | $ 9,804.25 |
|    35 | $ 9,742.08 |
|    40 | $ 9,807.98 |
|    45 | $ 9,661.36 |
|    50 | $ 9,667.89 |
|    55 | $ 9,519.05 |
|    60 | $ 9,699.97 |
|    65 | $ 9,871.59 |
|    70 | $ 9,822.37 |
|    75 | $ 9,531.11 |
|    80 | $ 9,406.97 |
|    85 | $ 9,573.03 |
|    90 | $ 9,639.23 |
|    95 | $ 9,649.86 |
|   100 | $ 9,267.77 |
|   105 | $ 9,164.69 |
|   110 | $ 9,302.57 |
|   115 | $ 9,462.72 |
|   120 | $ 9,269.09 |
|   125 | $ 9,295.59 |
|   130 | $ 9,474.11 |
|   130 | $ 9,474.11 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
