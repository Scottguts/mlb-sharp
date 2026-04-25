# Bankroll Simulation

_Generated 2026-04-25 13:37_  
_Replays every SETTLED bet in `bet_log.csv` against five sizing strategies._

_Starting bankroll: **$10,000.00** (1u = 1%)._
_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._


## Overall Comparison

| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| flat_1u        |    0 |   0-  0- 0 | $10,000.00 | $ 10,000.00 |    +0.00% |   +0.00% |   0.00% |
| flat_2u        |    0 |   0-  0- 0 | $10,000.00 | $ 10,000.00 |    +0.00% |   +0.00% |   0.00% |
| current_ladder |    0 |   0-  0- 0 | $10,000.00 | $ 10,000.00 |    +0.00% |   +0.00% |   0.00% |
| half_kelly     |    0 |   0-  0- 0 | $10,000.00 | $ 10,000.00 |    +0.00% |   +0.00% |   0.00% |
| quarter_kelly  |    0 |   0-  0- 0 | $10,000.00 | $ 10,000.00 |    +0.00% |   +0.00% |   0.00% |

## Per Category, Current Ladder

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |    0 |   0-  0- 0 | $10,000.00 | $ 10,000.00 |    +0.00% |   +0.00% |   0.00% |
| runline       |    0 |   0-  0- 0 | $10,000.00 | $ 10,000.00 |    +0.00% |   +0.00% |   0.00% |
| total         |    0 |   0-  0- 0 | $10,000.00 | $ 10,000.00 |    +0.00% |   +0.00% |   0.00% |

## Per Category, Half-Kelly

| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |
|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|
| moneyline     |    0 |   0-  0- 0 | $10,000.00 | $ 10,000.00 |    +0.00% |   +0.00% |   0.00% |
| runline       |    0 |   0-  0- 0 | $10,000.00 | $ 10,000.00 |    +0.00% |   +0.00% |   0.00% |
| total         |    0 |   0-  0- 0 | $10,000.00 | $ 10,000.00 |    +0.00% |   +0.00% |   0.00% |

## Bankroll Curve (Current Ladder)


## Strategy notes

- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.
- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.
- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.
- **Quarter-Kelly** is the conservative default many sharps use.
- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.
- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.
