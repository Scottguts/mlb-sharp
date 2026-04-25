"""
bankroll_sim.py — replay the historical bet log under multiple sizing rules

Loads bet_log.csv, walks through every SETTLED bet in chronological order,
and reports what your bankroll would have done under five different
position-sizing strategies:

  1. Flat 1u            — bet exactly 1u on every play
  2. Flat 2u            — bet exactly 2u (riskier; tests bankroll volatility)
  3. Current Ladder     — sized exactly as the cards recommended
  4. Half-Kelly         — bet 0.5 × Kelly fraction (capped at 5% of bankroll)
  5. Quarter-Kelly      — bet 0.25 × Kelly (most conservative)

Outputs:
  bankroll_sim.md — overall comparison + per-category breakdown +
                    max drawdown, ending bankroll growth, ROI per strategy.

Run:
    python bankroll_sim.py                          # default data root
    python bankroll_sim.py --start-bankroll 5000    # default 100u = $10k
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from bet_tracker import (
    DATA_ROOT_DEFAULT, LOG_FILENAME, _ensure_log, _read_log, _f, _i,
)

DEFAULT_START_BANKROLL = 10000.0   # $10,000 starting bankroll
DEFAULT_UNIT_PCT       = 0.01      # 1u = 1%
KELLY_CAP              = 0.05      # never bet more than 5% of bankroll
MIN_KELLY_BET          = 0.001     # below this fraction, treat as no-bet


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def _decimal_odds(american: int) -> float:
    return (american / 100 + 1) if american >= 100 else (100 / -american + 1)

def _kelly_fraction(fair_prob: float, american: int) -> float:
    """Kelly fraction as a share of bankroll. Negative if -EV."""
    if not (0 < fair_prob < 1): return 0.0
    d = _decimal_odds(american)
    b = d - 1
    return (fair_prob * d - 1) / b


@dataclass
class StrategyResult:
    name: str
    starting: float
    ending: float
    total_risked: float
    total_pnl: float
    bets: int
    won: int
    lost: int
    push: int
    max_drawdown_pct: float    # peak-to-trough drawdown %
    bankroll_curve: list[float]   # per-bet running bankroll

    @property
    def roi(self) -> float:
        return (self.total_pnl / self.total_risked) if self.total_risked else 0.0
    @property
    def growth_pct(self) -> float:
        return (self.ending - self.starting) / self.starting if self.starting else 0.0


def _simulate(rows: list[dict], strategy: str, start: float) -> StrategyResult:
    bankroll = start
    peak = start
    max_dd = 0.0
    risked = pnl = 0.0
    bets = won = lost = push = 0
    curve = [start]

    for r in rows:
        if r.get("status") not in ("won", "lost", "push"): continue
        price = _i(r.get("price"))
        if price is None: continue
        units_in_log = _f(r.get("units_risked"), 0.0)
        fair_prob = _f(r.get("fair_prob"))

        # Determine bet size (in dollars) for this strategy
        if strategy == "flat_1u":
            bet_size = bankroll * DEFAULT_UNIT_PCT
        elif strategy == "flat_2u":
            bet_size = bankroll * DEFAULT_UNIT_PCT * 2
        elif strategy == "current_ladder":
            bet_size = bankroll * DEFAULT_UNIT_PCT * units_in_log
        elif strategy == "half_kelly":
            if fair_prob is None: bet_size = 0
            else:
                f = max(0.0, _kelly_fraction(fair_prob, price)) * 0.5
                f = min(f, KELLY_CAP)
                bet_size = bankroll * f if f >= MIN_KELLY_BET else 0
        elif strategy == "quarter_kelly":
            if fair_prob is None: bet_size = 0
            else:
                f = max(0.0, _kelly_fraction(fair_prob, price)) * 0.25
                f = min(f, KELLY_CAP)
                bet_size = bankroll * f if f >= MIN_KELLY_BET else 0
        else:
            bet_size = 0

        if bet_size <= 0: continue
        # Cannot bet more than bankroll
        bet_size = min(bet_size, bankroll * 0.10)   # safety cap 10% even if math says higher

        bets += 1
        risked += bet_size
        st = r["status"]
        if st == "won":
            profit = bet_size * (price / 100.0 if price > 0 else 100.0 / -price)
            bankroll += profit; pnl += profit; won += 1
        elif st == "lost":
            bankroll -= bet_size; pnl -= bet_size; lost += 1
        else:  # push
            push += 1
        # Drawdown
        peak = max(peak, bankroll)
        if peak > 0:
            dd = (peak - bankroll) / peak
            if dd > max_dd: max_dd = dd
        curve.append(bankroll)

    return StrategyResult(
        name=strategy, starting=start, ending=bankroll,
        total_risked=risked, total_pnl=pnl, bets=bets,
        won=won, lost=lost, push=push,
        max_drawdown_pct=max_dd, bankroll_curve=curve,
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _row(r: StrategyResult) -> str:
    return (f"| {r.name:14s} | {r.bets:4d} | {r.won:3d}-{r.lost:3d}-{r.push:2d} | "
            f"${r.starting:>9,.2f} | ${r.ending:>10,.2f} | "
            f"{r.growth_pct*100:+8.2f}% | {r.roi*100:+7.2f}% | {r.max_drawdown_pct*100:6.2f}% |")


def _per_cat(rows: list[dict], strategy: str, start: float) -> dict[str, StrategyResult]:
    out: dict[str, StrategyResult] = {}
    for cat in ("moneyline", "runline", "total", "f5_total", "nrfi"):
        sub = [r for r in rows if r.get("market") == cat]
        if not sub: continue
        out[cat] = _simulate(sub, strategy, start)
    return out


def build(data_root: Path, start_bankroll: float) -> Path:
    log = _ensure_log(data_root)
    rows = _read_log(log)
    rows = sorted(rows, key=lambda r: (r.get("date") or "", _i(r.get("bet_id"), 0)))

    strategies = ["flat_1u", "flat_2u", "current_ladder", "half_kelly", "quarter_kelly"]
    results = {s: _simulate(rows, s, start_bankroll) for s in strategies}

    md: list[str] = [
        f"# Bankroll Simulation\n",
        f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}_  ",
        f"_Replays every SETTLED bet in `{LOG_FILENAME}` against five sizing strategies._\n",
        f"_Starting bankroll: **${start_bankroll:,.2f}** (1u = 1%)._",
        f"_Half-Kelly / quarter-Kelly require a model `fair_prob`; rows without it are skipped for those strategies._\n",
    ]

    md.append(
        "\n## Overall Comparison\n\n"
        "| Strategy       | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |\n"
        "|---             |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|"
    )
    for s in strategies:
        md.append(_row(results[s]))

    # Per-category, per-strategy
    md.append("\n## Per Category, Current Ladder\n")
    md.append("| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |\n"
              "|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|")
    by_cat = _per_cat(rows, "current_ladder", start_bankroll)
    for cat, res in by_cat.items():
        md.append(f"| {cat:13s} | {res.bets:4d} | {res.won:3d}-{res.lost:3d}-{res.push:2d} | "
                  f"${res.starting:>9,.2f} | ${res.ending:>10,.2f} | "
                  f"{res.growth_pct*100:+8.2f}% | {res.roi*100:+7.2f}% | {res.max_drawdown_pct*100:6.2f}% |")

    md.append("\n## Per Category, Half-Kelly\n")
    md.append("| Market        | Bets |   W-L-P  |   Starting   |   Ending     |  Growth  |   ROI    |  Max DD |\n"
              "|---            |-----:|:--------:|-------------:|-------------:|---------:|---------:|--------:|")
    for cat, res in _per_cat(rows, "half_kelly", start_bankroll).items():
        md.append(f"| {cat:13s} | {res.bets:4d} | {res.won:3d}-{res.lost:3d}-{res.push:2d} | "
                  f"${res.starting:>9,.2f} | ${res.ending:>10,.2f} | "
                  f"{res.growth_pct*100:+8.2f}% | {res.roi*100:+7.2f}% | {res.max_drawdown_pct*100:6.2f}% |")

    # Bankroll curve at sample points (so the file isn't huge)
    md.append("\n## Bankroll Curve (Current Ladder)\n")
    curve = results["current_ladder"].bankroll_curve
    if len(curve) > 1:
        md.append("Sampled every ~10 bets:\n")
        md.append("| Bet # |  Bankroll  |")
        md.append("|------:|-----------:|")
        step = max(1, len(curve) // 25)
        for i in range(0, len(curve), step):
            md.append(f"| {i:5d} | ${curve[i]:>9,.2f} |")
        md.append(f"| {len(curve)-1:5d} | ${curve[-1]:>9,.2f} |   _(final)_")

    md.append("\n## Strategy notes\n")
    md.append(
        "- **Flat 1u** is the simplest sanity check. If your edge is real, this curve should grind up.\n"
        "- **Current Ladder** is what you actually bet. Compare its growth to flat 1u to see if your sizing helps or hurts.\n"
        "- **Half-Kelly** maximizes long-run growth at acceptable variance — but only if `fair_prob` is well-calibrated.\n"
        "- **Quarter-Kelly** is the conservative default many sharps use.\n"
        "- **Max DD** is peak-to-trough drawdown. Above ~25% is psychologically very hard to ride out.\n"
        "- All simulations use percentage-of-current-bankroll sizing so they auto-rebalance over time.\n"
    )
    out = data_root / "bankroll_sim.md"
    out.write_text("\n".join(md))
    print(f"[bankroll] wrote {out}")
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=str(DATA_ROOT_DEFAULT))
    ap.add_argument("--start-bankroll", type=float, default=DEFAULT_START_BANKROLL)
    args = ap.parse_args(argv)
    build(Path(args.data_root).expanduser().resolve(), args.start_bankroll)
    return 0


if __name__ == "__main__":
    sys.exit(main())
