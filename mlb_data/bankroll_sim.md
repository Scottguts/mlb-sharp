# Bankroll Simulation

_Generated 2026-06-23 11:11_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  194 |  95- 98- 1 | $10,000.00 | $  9,220.15 |    -7.80% |   -4.23% |  13.18% |
| flat_2u        |  194 |  95- 98- 1 | $10,000.00 | $  8,337.20 |   -16.63% |   -4.79% |  25.42% |
| current_ladder |  194 |  95- 98- 1 | $10,000.00 | $  9,276.49 |    -7.24% |   -4.57% |  11.24% |
| half_kelly     |  194 |  95- 98- 1 | $10,000.00 | $  5,744.87 |   -42.55% |   -7.71% |  49.82% |
| quarter_kelly  |  194 |  95- 98- 1 | $10,000.00 | $  6,488.81 |   -35.11% |   -8.89% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   82 |  38- 44- 0 | $10,000.00 | $  9,417.48 |    -5.83% |  -10.40% |   9.10% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   49 |  23- 25- 1 | $10,000.00 | $  9,844.30 |    -1.56% |   -4.63% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   82 |  38- 44- 0 | $10,000.00 | $  8,443.88 |   -15.56% |   -6.18% |  38.25% |
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
|   189 | $ 9,743.03 |
|   194 | $ 9,276.49 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
