# Bankroll Simulation

_Generated 2026-06-18 11:09_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  184 |  91- 92- 1 | $10,000.00 | $  9,388.54 |    -6.11% |   -3.50% |  13.18% |
| flat_2u        |  184 |  91- 92- 1 | $10,000.00 | $  8,653.71 |   -13.46% |   -4.09% |  25.42% |
| current_ladder |  184 |  91- 92- 1 | $10,000.00 | $  9,649.31 |    -3.51% |   -2.42% |  11.24% |
| half_kelly     |  184 |  91- 92- 1 | $10,000.00 | $  6,581.89 |   -34.18% |   -6.53% |  49.82% |
| quarter_kelly  |  184 |  91- 92- 1 | $10,000.00 | $  6,928.38 |   -30.72% |   -8.12% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   81 |  37- 44- 0 | $10,000.00 | $  9,361.31 |    -6.39% |  -11.50% |   9.10% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   49 |  23- 25- 1 | $10,000.00 | $  9,844.30 |    -1.56% |   -4.63% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   81 |  37- 44- 0 | $10,000.00 | $  8,347.88 |   -16.52% |   -6.58% |  38.25% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   49 |  23- 25- 1 | $10,000.00 | $  8,453.02 |   -15.47% |   -8.17% |  24.42% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|     7 | $ 9,763.36 |
|    14 | $ 9,655.06 |
|    21 | $ 9,819.70 |
|    28 | $ 9,726.18 |
|    35 | $ 9,742.08 |
|    42 | $ 9,807.74 |
|    49 | $ 9,642.78 |
|    56 | $ 9,558.72 |
|    63 | $ 9,813.25 |
|    70 | $ 9,822.37 |
|    77 | $ 9,447.76 |
|    84 | $ 9,499.88 |
|    91 | $ 9,669.74 |
|    98 | $ 9,408.43 |
|   105 | $ 9,164.69 |
|   112 | $ 9,388.69 |
|   119 | $ 9,410.24 |
|   126 | $ 9,460.13 |
|   133 | $ 9,380.06 |
|   140 | $ 8,875.52 |
|   147 | $ 9,106.21 |
|   154 | $ 9,364.04 |
|   161 | $ 9,970.25 |
|   168 | $10,308.76 |
|   175 | $ 9,847.39 |
|   182 | $ 9,495.16 |
|   184 | $ 9,649.31 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
