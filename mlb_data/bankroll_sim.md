# Bankroll Simulation

_Generated 2026-07-02 11:08_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  201 |  98-102- 1 | $10,000.00 | $  9,124.24 |    -8.76% |   -4.59% |  13.18% |
| flat_2u        |  201 |  98-102- 1 | $10,000.00 | $  8,158.84 |   -18.41% |   -5.13% |  25.42% |
| current_ladder |  201 |  98-102- 1 | $10,000.00 | $  9,166.03 |    -8.34% |   -5.00% |  11.38% |
| half_kelly     |  201 |  98-102- 1 | $10,000.00 | $  5,556.71 |   -44.43% |   -7.83% |  49.82% |
| quarter_kelly  |  201 |  98-102- 1 | $10,000.00 | $  6,456.33 |   -35.44% |   -8.76% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   84 |  39- 45- 0 | $10,000.00 | $  9,439.84 |    -5.60% |   -9.67% |   9.10% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   49 |  23- 25- 1 | $10,000.00 | $  9,844.30 |    -1.56% |   -4.63% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   84 |  39- 45- 0 | $10,000.00 | $  8,492.11 |   -15.08% |   -5.92% |  38.25% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   49 |  23- 25- 1 | $10,000.00 | $  8,453.02 |   -15.47% |   -8.17% |  24.42% |

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
|   201 | $ 9,166.03 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
