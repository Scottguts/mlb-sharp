# Bankroll Simulation

_Generated 2026-07-06 11:08_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  213 | 105-107- 1 | $10,000.00 | $  9,256.18 |    -7.44% |   -3.68% |  13.18% |
| flat_2u        |  213 | 105-107- 1 | $10,000.00 | $  8,387.15 |   -16.13% |   -4.26% |  25.42% |
| current_ladder |  213 | 105-107- 1 | $10,000.00 | $  9,148.50 |    -8.52% |   -4.75% |  11.84% |
| half_kelly     |  213 | 105-107- 1 | $10,000.00 | $  5,551.48 |   -44.49% |   -7.50% |  49.82% |
| quarter_kelly  |  213 | 105-107- 1 | $10,000.00 | $  6,472.14 |   -35.28% |   -8.38% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   86 |  40- 46- 0 | $10,000.00 | $  9,445.71 |    -5.54% |   -9.42% |   9.10% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   51 |  25- 25- 1 | $10,000.00 | $  9,936.14 |    -0.64% |   -1.85% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   86 |  40- 46- 0 | $10,000.00 | $  8,513.64 |   -14.86% |   -5.80% |  38.25% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   51 |  25- 25- 1 | $10,000.00 | $  8,731.87 |   -12.68% |   -6.60% |  24.42% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|     8 | $ 9,616.91 |
|    16 | $ 9,976.22 |
|    24 | $ 9,770.36 |
|    32 | $ 9,797.64 |
|    40 | $ 9,807.98 |
|    48 | $ 9,691.24 |
|    56 | $ 9,558.72 |
|    64 | $ 9,921.20 |
|    72 | $ 9,724.39 |
|    80 | $ 9,406.97 |
|    88 | $ 9,517.03 |
|    96 | $ 9,505.11 |
|   104 | $ 9,210.74 |
|   112 | $ 9,388.69 |
|   120 | $ 9,269.09 |
|   128 | $ 9,452.71 |
|   136 | $ 9,147.20 |
|   144 | $ 8,965.30 |
|   152 | $ 9,317.91 |
|   160 | $ 9,941.01 |
|   168 | $10,308.76 |
|   176 | $ 9,879.16 |
|   184 | $ 9,649.31 |
|   192 | $ 9,561.17 |
|   200 | $ 9,258.61 |
|   208 | $ 9,284.13 |
|   213 | $ 9,148.50 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
