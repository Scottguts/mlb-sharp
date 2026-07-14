# Bankroll Simulation

_Generated 2026-07-14 11:07_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  233 | 116-116- 1 | $10,000.00 | $  9,409.09 |    -5.91% |   -2.68% |  13.18% |
| flat_2u        |  233 | 116-116- 1 | $10,000.00 | $  8,649.42 |   -13.51% |   -3.27% |  25.42% |
| current_ladder |  233 | 116-116- 1 | $10,000.00 | $  9,617.04 |    -3.83% |   -1.89% |  11.84% |
| half_kelly     |  233 | 116-116- 1 | $10,000.00 | $  6,564.67 |   -34.35% |   -5.37% |  49.82% |
| quarter_kelly  |  233 | 116-116- 1 | $10,000.00 | $  7,303.21 |   -26.97% |   -5.95% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   91 |  41- 50- 0 | $10,000.00 | $  9,332.36 |    -6.68% |  -10.74% |   9.10% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   51 |  25- 25- 1 | $10,000.00 | $  9,936.14 |    -0.64% |   -1.85% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   91 |  41- 50- 0 | $10,000.00 | $  8,232.54 |   -17.67% |   -6.73% |  38.25% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   51 |  25- 25- 1 | $10,000.00 | $  8,731.87 |   -12.68% |   -6.60% |  24.42% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|     9 | $ 9,472.65 |
|    18 | $ 9,777.45 |
|    27 | $ 9,775.05 |
|    36 | $ 9,788.48 |
|    45 | $ 9,661.36 |
|    54 | $ 9,566.89 |
|    63 | $ 9,813.25 |
|    72 | $ 9,724.39 |
|    81 | $ 9,446.16 |
|    90 | $ 9,639.23 |
|    99 | $ 9,361.39 |
|   108 | $ 9,222.98 |
|   117 | $ 9,413.13 |
|   126 | $ 9,460.13 |
|   135 | $ 9,286.50 |
|   144 | $ 8,965.30 |
|   153 | $ 9,411.09 |
|   162 | $ 9,820.69 |
|   171 | $10,164.28 |
|   180 | $ 9,688.19 |
|   189 | $ 9,743.03 |
|   198 | $ 9,283.56 |
|   207 | $ 9,425.51 |
|   216 | $ 9,120.88 |
|   225 | $ 9,431.63 |
|   233 | $ 9,617.04 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
