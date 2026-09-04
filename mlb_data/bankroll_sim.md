# Bankroll Simulation

_Generated 2026-09-04 11:19_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  327 | 163-163- 1 | $10,000.00 | $  9,244.02 |    -7.56% |   -2.45% |  13.18% |
| flat_2u        |  327 | 163-163- 1 | $10,000.00 | $  8,271.39 |   -17.29% |   -3.02% |  25.42% |
| current_ladder |  327 | 163-163- 1 | $10,000.00 | $  9,209.00 |    -7.91% |   -2.60% |  13.96% |
| half_kelly     |  327 | 163-163- 1 | $10,000.00 | $  5,398.52 |   -46.01% |   -5.35% |  51.74% |
| quarter_kelly  |  327 | 163-163- 1 | $10,000.00 | $  6,629.31 |   -33.71% |   -5.61% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |  114 |  54- 60- 0 | $10,000.00 | $  9,550.18 |    -4.50% |   -5.94% |   9.66% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   56 |  27- 28- 1 | $10,000.00 | $  9,879.15 |    -1.21% |   -3.26% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |  114 |  54- 60- 0 | $10,000.00 | $  8,583.60 |   -14.16% |   -4.84% |  39.16% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   56 |  27- 28- 1 | $10,000.00 | $  8,595.71 |   -14.04% |   -7.04% |  24.42% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|    13 | $ 9,530.75 |
|    26 | $ 9,824.17 |
|    39 | $ 9,857.27 |
|    52 | $ 9,571.46 |
|    65 | $ 9,871.59 |
|    78 | $ 9,400.52 |
|    91 | $ 9,669.74 |
|   104 | $ 9,210.74 |
|   117 | $ 9,413.13 |
|   130 | $ 9,474.11 |
|   143 | $ 9,010.36 |
|   156 | $ 9,539.58 |
|   169 | $10,205.67 |
|   182 | $ 9,495.16 |
|   195 | $ 9,386.05 |
|   208 | $ 9,284.13 |
|   221 | $ 9,268.12 |
|   234 | $ 9,667.53 |
|   247 | $ 9,801.35 |
|   260 | $ 9,891.03 |
|   273 | $ 9,149.30 |
|   286 | $ 9,198.93 |
|   299 | $ 9,197.00 |
|   312 | $ 9,377.99 |
|   325 | $ 9,193.41 |
|   327 | $ 9,209.00 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
