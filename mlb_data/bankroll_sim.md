# Bankroll Simulation

_Generated 2026-08-12 11:34_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  301 | 149-151- 1 | $10,000.00 | $  9,011.57 |    -9.88% |   -3.48% |  13.18% |
| flat_2u        |  301 | 149-151- 1 | $10,000.00 | $  7,882.38 |   -21.18% |   -4.00% |  25.42% |
| current_ladder |  301 | 149-151- 1 | $10,000.00 | $  9,013.75 |    -9.86% |   -3.62% |  12.78% |
| half_kelly     |  301 | 149-151- 1 | $10,000.00 | $  5,080.41 |   -49.20% |   -6.12% |  49.82% |
| quarter_kelly  |  301 | 149-151- 1 | $10,000.00 | $  6,420.39 |   -35.80% |   -6.37% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |  108 |  50- 58- 0 | $10,000.00 | $  9,479.14 |    -5.21% |   -7.24% |   9.66% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   56 |  27- 28- 1 | $10,000.00 | $  9,879.15 |    -1.21% |   -3.26% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |  108 |  50- 58- 0 | $10,000.00 | $  8,399.35 |   -16.01% |   -5.62% |  39.16% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   56 |  27- 28- 1 | $10,000.00 | $  8,595.71 |   -14.04% |   -7.04% |  24.42% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|    12 | $ 9,491.20 |
|    24 | $ 9,770.36 |
|    36 | $ 9,788.48 |
|    48 | $ 9,691.24 |
|    60 | $ 9,699.97 |
|    72 | $ 9,724.39 |
|    84 | $ 9,499.88 |
|    96 | $ 9,505.11 |
|   108 | $ 9,222.98 |
|   120 | $ 9,269.09 |
|   132 | $ 9,332.47 |
|   144 | $ 8,965.30 |
|   156 | $ 9,539.58 |
|   168 | $10,308.76 |
|   180 | $ 9,688.19 |
|   192 | $ 9,561.17 |
|   204 | $ 9,317.15 |
|   216 | $ 9,120.88 |
|   228 | $ 9,591.10 |
|   240 | $ 9,892.33 |
|   252 | $ 9,875.02 |
|   264 | $ 9,453.05 |
|   276 | $ 9,216.54 |
|   288 | $ 9,229.85 |
|   300 | $ 9,151.01 |
|   301 | $ 9,013.75 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
