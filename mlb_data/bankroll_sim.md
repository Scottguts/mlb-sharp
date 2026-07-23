# Bankroll Simulation

_Generated 2026-07-23 11:09_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |  253 | 128-124- 1 | $10,000.00 | $  9,737.67 |    -2.62% |   -1.09% |  13.18% |
| flat_2u        |  253 | 128-124- 1 | $10,000.00 | $  9,246.18 |    -7.54% |   -1.68% |  25.42% |
| current_ladder |  253 | 128-124- 1 | $10,000.00 | $ 10,033.52 |    +0.34% |   +0.15% |  11.84% |
| half_kelly     |  253 | 128-124- 1 | $10,000.00 | $  7,620.79 |   -23.79% |   -3.43% |  49.82% |
| quarter_kelly  |  253 | 128-124- 1 | $10,000.00 | $  7,817.46 |   -21.83% |   -4.46% |  43.74% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   93 |  42- 51- 0 | $10,000.00 | $  9,327.15 |    -6.73% |  -10.66% |   9.10% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  9,705.50 |    -2.95% |  -18.70% |   3.35% |
| total         |   54 |  26- 27- 1 | $10,000.00 | $  9,883.87 |    -1.16% |   -3.22% |   4.52% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |   93 |  42- 51- 0 | $10,000.00 | $  8,235.29 |   -17.65% |   -6.66% |  38.25% |
| runline       |   22 |  10- 12- 0 | $10,000.00 | $  7,416.56 |   -25.83% |  -27.27% |  28.80% |
| total         |   54 |  26- 27- 1 | $10,000.00 | $  8,574.43 |   -14.26% |   -7.25% |  24.42% |

## Bankroll Curve (Current Ladder)

Sampled every ~10 bets:

| Bet # |  Bankroll  |
|------:|-----------:|
|     0 | $10,000.00 |
|    10 | $ 9,330.56 |
|    20 | $ 9,869.05 |
|    30 | $ 9,804.25 |
|    40 | $ 9,807.98 |
|    50 | $ 9,667.89 |
|    60 | $ 9,699.97 |
|    70 | $ 9,822.37 |
|    80 | $ 9,406.97 |
|    90 | $ 9,639.23 |
|   100 | $ 9,267.77 |
|   110 | $ 9,302.57 |
|   120 | $ 9,269.09 |
|   130 | $ 9,474.11 |
|   140 | $ 8,875.52 |
|   150 | $ 9,408.07 |
|   160 | $ 9,941.01 |
|   170 | $10,319.07 |
|   180 | $ 9,688.19 |
|   190 | $ 9,854.59 |
|   200 | $ 9,258.61 |
|   210 | $ 9,376.28 |
|   220 | $ 9,361.73 |
|   230 | $ 9,644.74 |
|   240 | $ 9,892.33 |
|   250 | $ 9,977.89 |
|   253 | $10,033.52 |   _(final)_

## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
