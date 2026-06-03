# Bankroll Simulation

_Generated 2026-06-03 14:38_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  145 |  66- 78- 1 | $10,000.00 | $  8,786.87 |   -12.13% |   -8.80% |  13.18% |
| flat_2u        |  145 |  66- 78- 1 | $10,000.00 | $  7,604.21 |   -23.96% |   -9.20% |  25.42% |
| current_ladder |  145 |  66- 78- 1 | $10,000.00 | $  8,920.48 |   -10.80% |  -10.98% |  11.24% |
| half_kelly     |  145 |  66- 78- 1 | $10,000.00 | $  5,161.69 |   -48.38% |  -11.76% |  49.82% |
| quarter_kelly  |  145 |  66- 78- 1 | $10,000.00 | $  5,707.77 |   -42.92% |  -14.03% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   78 |  35- 43- 0 | $10,000.00 | $  9,329.45 |    -6.71% |  -12.38% |   9.10% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   45 |  21- 23- 1 | $10,000.00 | $  9,851.77 |    -1.48% |   -4.68% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   78 |  35- 43- 0 | $10,000.00 | $  8,231.01 |   -17.69% |   -7.16% |  38.25% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   45 |  21- 23- 1 | $10,000.00 | $  8,455.43 |   -15.45% |   -8.38% |  24.42% |

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
|   135 | $ 9,286.50 |
|   140 | $ 8,875.52 |
|   145 | $ 8,920.48 |
|   145 | $ 8,920.48 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
