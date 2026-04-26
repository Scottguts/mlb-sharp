# Bankroll Simulation

_Generated 2026-04-25 22:25_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |   28 |  13- 14- 1 | $10,000.00 | $  9,630.66 |    -3.69% |  -13.55% |   4.96% |
| flat_2u        |   28 |  13- 14- 1 | $10,000.00 | $  9,253.82 |    -7.46% |  -14.08% |   9.73% |
| current_ladder |   28 |  13- 14- 1 | $10,000.00 | $  9,654.20 |    -3.46% |  -13.48% |   6.42% |
| half_kelly     |   28 |  13- 14- 1 | $10,000.00 | $  8,051.90 |   -19.48% |  -17.20% |  22.11% |
| quarter_kelly  |   28 |  13- 14- 1 | $10,000.00 | $  7,991.84 |   -20.08% |  -20.51% |  21.58% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |    2 |   1-  1- 0 | $10,000.00 | $  9,895.60 |    -1.04% |  -52.40% |   1.50% |
| runline       |   11 |   5-  6- 0 | $10,000.00 | $  9,755.96 |    -2.44% |  -26.21% |   3.46% |
| total         |   15 |   7-  7- 1 | $10,000.00 | $ 10,000.10 |    +0.00% |   +0.01% |   3.07% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |    2 |   1-  1- 0 | $10,000.00 | $  9,735.74 |    -2.64% |  -35.02% |   5.00% |
| runline       |   11 |   5-  6- 0 | $10,000.00 | $  8,554.48 |   -14.46% |  -29.52% |  14.46% |
| total         |   15 |   7-  7- 1 | $10,000.00 | $  9,667.98 |    -3.32% |   -4.94% |  14.26% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|     1 | $10,000.00 |
|     2 | $ 9,850.00 |
|     3 | $ 9,702.25 |
|     4 | $ 9,653.74 |
|     5 | $ 9,508.93 |
|     6 | $ 9,644.77 |
|     7 | $ 9,500.10 |
|     8 | $ 9,357.60 |
|     9 | $ 9,437.81 |
|    10 | $ 9,518.70 |
|    11 | $ 9,558.37 |
|    12 | $ 9,683.04 |
|    13 | $ 9,872.90 |
|    14 | $ 9,724.81 |
|    15 | $ 9,676.19 |
|    16 | $ 9,720.98 |
|    17 | $ 9,766.84 |
|    18 | $ 9,718.00 |
|    19 | $ 9,766.59 |
|    20 | $ 9,717.76 |
|    21 | $ 9,669.17 |
|    22 | $ 9,694.89 |
|    23 | $ 9,722.43 |
|    24 | $ 9,673.82 |
|    25 | $ 9,625.45 |
|    26 | $ 9,654.44 |
|    27 | $ 9,702.71 |
|    28 | $ 9,654.20 |
|    28 | $ 9,654.20 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
