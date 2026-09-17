# Bankroll Simulation

_Generated 2026-09-17 11:13_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  358 | 178-179- 1 | $10,000.00 | $  9,019.08 |    -9.81% |   -2.92% |  13.18% |
| flat_2u        |  358 | 178-179- 1 | $10,000.00 | $  7,850.98 |   -21.49% |   -3.45% |  25.42% |
| current_ladder |  358 | 178-179- 1 | $10,000.00 | $  8,773.08 |   -12.27% |   -3.62% |  14.98% |
| half_kelly     |  358 | 178-179- 1 | $10,000.00 | $  4,796.05 |   -52.04% |   -5.62% |  52.83% |
| quarter_kelly  |  358 | 178-179- 1 | $10,000.00 | $  6,344.66 |   -36.55% |   -5.61% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |  119 |  56- 63- 0 | $10,000.00 | $  9,508.12 |    -4.92% |   -6.30% |   9.66% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   57 |  28- 28- 1 | $10,000.00 | $  9,927.58 |    -0.72% |   -1.93% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |  119 |  56- 63- 0 | $10,000.00 | $  8,393.67 |   -16.06% |   -5.35% |  39.16% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   57 |  28- 28- 1 | $10,000.00 | $  8,761.26 |   -12.39% |   -6.16% |  24.42% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|    14 | $ 9,655.06 |
|    28 | $ 9,726.18 |
|    42 | $ 9,807.74 |
|    56 | $ 9,558.72 |
|    70 | $ 9,822.37 |
|    84 | $ 9,499.88 |
|    98 | $ 9,408.43 |
|   112 | $ 9,388.69 |
|   126 | $ 9,460.13 |
|   140 | $ 8,875.52 |
|   154 | $ 9,364.04 |
|   168 | $10,308.76 |
|   182 | $ 9,495.16 |
|   196 | $ 9,520.14 |
|   210 | $ 9,376.28 |
|   224 | $ 9,309.68 |
|   238 | $ 9,759.05 |
|   252 | $ 9,875.02 |
|   266 | $ 9,422.99 |
|   280 | $ 9,495.34 |
|   294 | $ 9,055.54 |
|   308 | $ 9,145.96 |
|   322 | $ 9,035.54 |
|   336 | $ 8,972.07 |
|   350 | $ 9,114.37 |
|   358 | $ 8,773.08 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
