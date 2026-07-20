# Bankroll Simulation

_Generated 2026-07-20 11:12_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  244 | 123-120- 1 | $10,000.00 | $  9,650.32 |    -3.50% |   -1.51% |  13.18% |
| flat_2u        |  244 | 123-120- 1 | $10,000.00 | $  9,089.13 |    -9.11% |   -2.10% |  25.42% |
| current_ladder |  244 | 123-120- 1 | $10,000.00 | $  9,846.71 |    -1.53% |   -0.72% |  11.84% |
| half_kelly     |  244 | 123-120- 1 | $10,000.00 | $  7,272.82 |   -27.27% |   -4.08% |  49.82% |
| quarter_kelly  |  244 | 123-120- 1 | $10,000.00 | $  7,656.62 |   -23.43% |   -4.96% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   92 |  42- 50- 0 | $10,000.00 | $  9,374.02 |    -6.26% |   -9.99% |   9.10% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   53 |  25- 27- 1 | $10,000.00 | $  9,837.02 |    -1.63% |   -4.58% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   92 |  42- 50- 0 | $10,000.00 | $  8,336.93 |   -16.63% |   -6.30% |  38.25% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   53 |  25- 27- 1 | $10,000.00 | $  8,437.66 |   -15.62% |   -8.00% |  24.42% |

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
|   234 | $ 9,667.53 |
|   243 | $ 9,896.19 |
|   244 | $ 9,846.71 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
