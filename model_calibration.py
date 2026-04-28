"""
model_calibration.py — backtest the predictive model against the cached
historical game outcomes pulled by historical_validate.py.

What this answers
-----------------
Does the system's *prediction layer* (expected_total_runs, NRFI prob,
F5 prob) actually beat the naive "always predict the league mean"
baseline? If we can't beat that, no betting strategy on top can work.

What this can NOT answer
------------------------
P/L. We have no historical odds — that's the trade-off of the free data
plan. The CLV tracker (closing_snapshot.py) is the *forward-looking* P/L
proof.

Method
------
For each season we have, walk through every game and compute what a
*minimal pre-game-only* model would predict using ONLY:
  * The park's pf_runs (from PARKS dict at run time)
  * League average for the season

We then compare against actual outcomes and report:
  * Total runs RMSE (vs the naive league-mean baseline)
  * F5 runs RMSE
  * NRFI prediction calibration (Brier score)
  * Park-factor sanity check: do high-PF parks score more?

This is intentionally a SIMPLE pre-game-only model. The full system
includes pitcher / bullpen / lineup / weather signals that would
require pulling per-game data we don't cache. The point is to verify
the *baseline calibration* is good; the in-game adjustments stack
on top of that.

Usage
-----
    python model_calibration.py                       # 2015-2024 default
    python model_calibration.py --start 2020 --end 2024
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("[error] pandas required."); sys.exit(1)

# Reuse the PARKS dict so we always score with the latest pf_runs values.
from mlb_data_scraper import PARKS
from mlb_grader import (
    LEAGUE_AVG_TOTAL, F5_LEAGUE_AVG, LEAGUE_NRFI_RATE, HOME_FIELD_PROB,
)


def _load(start: int, end: int, data_root: Path) -> pd.DataFrame:
    p = data_root / "_history" / f"games_{start}_{end}.parquet"
    if p.exists():
        return pd.read_parquet(p)
    csv = data_root / "_history" / f"games_{start}_{end}.csv"
    if csv.exists():
        return pd.read_csv(csv)
    raise FileNotFoundError(
        f"No cached history at {p}. Run `python historical_validate.py "
        f"--start {start} --end {end}` first."
    )


def _rmse(pred, actual) -> float:
    return float(((pred - actual) ** 2).mean() ** 0.5)


def _brier(pred_prob, actual_binary) -> float:
    """Brier score: 0 = perfect, 0.25 = always-50/50, 1 = always-wrong."""
    return float(((pred_prob - actual_binary) ** 2).mean())


def baseline_predict_total(df: pd.DataFrame, league_mean: float) -> pd.Series:
    """Naive baseline: every game = league mean. RMSE floor."""
    return pd.Series([league_mean] * len(df), index=df.index)


def park_adjusted_predict(df: pd.DataFrame, league_mean: float,
                          metric: str = "pf_runs") -> pd.Series:
    """Adjusts league mean by current PARKS pf_runs. This is what the
    system would predict on a no-info day with no market line."""
    pf_lookup = {vid: p["pf_runs"] for vid, p in PARKS.items()}
    pf_factors = df["venue_id"].map(pf_lookup).fillna(100) / 100.0
    return pf_factors * league_mean


def home_field_predict_winner(df: pd.DataFrame, p_home: float) -> pd.Series:
    """Naive home-field-only ML predictor — predict P(home wins) = p_home."""
    return pd.Series([p_home] * len(df), index=df.index)


def evaluate(df: pd.DataFrame) -> dict:
    """Run the calibration suite. Returns a dict of per-season results
    plus an aggregate row across the full window."""
    out: dict = {"per_season": [], "totals": {}}
    league_mean_total = float(df["total_runs"].mean())
    league_mean_f5    = float(df["f5_runs"].mean())
    nrfi_rate         = float((df["first_inn"] == 0).mean())
    home_win_pct      = float((df["home_runs"] > df["away_runs"]).mean())

    for season in sorted(df["season"].unique()):
        sub = df[df["season"] == season]
        # Total runs prediction
        baseline = baseline_predict_total(sub, league_mean_total)
        park_adj = park_adjusted_predict(sub, league_mean_total)
        rmse_baseline = _rmse(baseline, sub["total_runs"])
        rmse_park     = _rmse(park_adj, sub["total_runs"])
        # F5 runs
        baseline_f5 = baseline_predict_total(sub, league_mean_f5)
        rmse_f5     = _rmse(baseline_f5, sub["f5_runs"])
        # NRFI Brier
        nrfi_actual = (sub["first_inn"] == 0).astype(int)
        brier_nrfi  = _brier(pd.Series([nrfi_rate] * len(sub), index=sub.index), nrfi_actual)
        # Home win pct (naive predictor)
        home_won = (sub["home_runs"] > sub["away_runs"]).astype(int)
        brier_ml = _brier(pd.Series([home_win_pct] * len(sub), index=sub.index), home_won)
        out["per_season"].append({
            "season": int(season),
            "games": len(sub),
            "rmse_total_baseline": round(rmse_baseline, 3),
            "rmse_total_parkadj":  round(rmse_park, 3),
            "delta_park_vs_baseline": round(rmse_baseline - rmse_park, 3),
            "rmse_f5_baseline":    round(rmse_f5, 3),
            "brier_nrfi":          round(brier_nrfi, 4),
            "brier_ml":            round(brier_ml, 4),
        })
    # Aggregate (weighted by games)
    total_games = len(df)
    total_baseline = _rmse(baseline_predict_total(df, league_mean_total), df["total_runs"])
    total_parkadj  = _rmse(park_adjusted_predict(df, league_mean_total), df["total_runs"])
    total_f5       = _rmse(baseline_predict_total(df, league_mean_f5), df["f5_runs"])
    nrfi_actual_all = (df["first_inn"] == 0).astype(int)
    brier_nrfi_all  = _brier(pd.Series([nrfi_rate] * len(df), index=df.index), nrfi_actual_all)
    home_won_all    = (df["home_runs"] > df["away_runs"]).astype(int)
    brier_ml_all    = _brier(pd.Series([home_win_pct] * len(df), index=df.index), home_won_all)
    out["totals"] = {
        "games":                total_games,
        "league_mean_total":    round(league_mean_total, 3),
        "league_mean_f5":       round(league_mean_f5, 3),
        "league_nrfi_rate":     round(nrfi_rate, 4),
        "home_win_pct":         round(home_win_pct, 4),
        "rmse_total_baseline":  round(total_baseline, 3),
        "rmse_total_parkadj":   round(total_parkadj, 3),
        "park_adj_improvement": round(total_baseline - total_parkadj, 3),
        "rmse_f5_baseline":     round(total_f5, 3),
        "brier_nrfi":           round(brier_nrfi_all, 4),
        "brier_ml":             round(brier_ml_all, 4),
        "vs_constants_in_code": {
            "LEAGUE_AVG_TOTAL_in_code": LEAGUE_AVG_TOTAL,
            "LEAGUE_AVG_TOTAL_actual":  round(league_mean_total, 3),
            "drift":                    round(LEAGUE_AVG_TOTAL - league_mean_total, 3),
            "F5_LEAGUE_AVG_in_code":    F5_LEAGUE_AVG,
            "F5_LEAGUE_AVG_actual":     round(league_mean_f5, 3),
            "LEAGUE_NRFI_RATE_in_code": LEAGUE_NRFI_RATE,
            "LEAGUE_NRFI_RATE_actual":  round(nrfi_rate, 4),
            "HOME_FIELD_PROB_in_code":  HOME_FIELD_PROB,
            "HOME_FIELD_PROB_actual":   round(home_win_pct - 0.5, 4),
        },
    }
    return out


def render(results: dict) -> str:
    md: list[str] = []
    md.append(f"# Model Calibration Backtest\n")
    md.append(f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}_  ")
    md.append(f"_{results['totals']['games']:,} games across "
              f"{len(results['per_season'])} seasons_\n")

    md.append("\n## Per-season RMSE (lower is better)\n")
    md.append("| Season | Games | RMSE total (baseline) | RMSE total (park-adj) | Δ | RMSE F5 | Brier NRFI | Brier ML |")
    md.append("|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in results["per_season"]:
        md.append(f"| {r['season']} | {r['games']} | {r['rmse_total_baseline']} | "
                  f"{r['rmse_total_parkadj']} | {r['delta_park_vs_baseline']:+.3f} | "
                  f"{r['rmse_f5_baseline']} | {r['brier_nrfi']} | {r['brier_ml']} |")

    md.append("\n## Aggregate (full window)\n")
    t = results["totals"]
    md.append(f"- League mean total runs: **{t['league_mean_total']}**")
    md.append(f"- League mean F5 runs: **{t['league_mean_f5']}**")
    md.append(f"- League NRFI rate: **{t['league_nrfi_rate']*100:.2f}%**")
    md.append(f"- Home win pct: **{t['home_win_pct']*100:.2f}%**")
    md.append(f"- RMSE total — naive: **{t['rmse_total_baseline']}**")
    md.append(f"- RMSE total — park-adjusted: **{t['rmse_total_parkadj']}**")
    md.append(f"- **Park-adj improvement: {t['park_adj_improvement']:+.3f} RMSE**")
    md.append(f"- RMSE F5 (naive): **{t['rmse_f5_baseline']}**")
    md.append(f"- Brier NRFI: **{t['brier_nrfi']}** (0.25 = always-50/50)")
    md.append(f"- Brier ML: **{t['brier_ml']}** (0.25 = always-50/50)")

    md.append("\n## Constants drift check\n")
    drift = t["vs_constants_in_code"]
    md.append("| Constant | In code | Actual | Drift |")
    md.append("|---|---:|---:|---:|")
    for label, code_key, actual_key in (
        ("LEAGUE_AVG_TOTAL",  "LEAGUE_AVG_TOTAL_in_code",  "LEAGUE_AVG_TOTAL_actual"),
        ("F5_LEAGUE_AVG",     "F5_LEAGUE_AVG_in_code",     "F5_LEAGUE_AVG_actual"),
        ("LEAGUE_NRFI_RATE",  "LEAGUE_NRFI_RATE_in_code",  "LEAGUE_NRFI_RATE_actual"),
        ("HOME_FIELD_PROB",   "HOME_FIELD_PROB_in_code",   "HOME_FIELD_PROB_actual"),
    ):
        d = drift[code_key] - drift[actual_key]
        md.append(f"| {label} | {drift[code_key]} | {drift[actual_key]} | {d:+.4f} |")

    md.append("\n## Interpretation\n")
    md.append("- **Park-adj improvement** must be **positive** for park factors to add "
              "value. If it's near zero or negative, the `pf_runs` numbers in PARKS "
              "are stale — re-run `historical_validate.py`.\n")
    md.append("- **Brier NRFI ~0.246** is the perfect-uninformed baseline (Brier of "
              "predicting league rate for every game). Any per-game model needs to "
              "beat this on a held-out year to add value.\n")
    md.append("- **RMSE total ~4.3-4.6** is the irreducible variance of MLB scoring. "
              "Even a perfect pre-game model can't go below ~3.7-3.8 — that's the "
              "noise floor (random variation in per-game outcomes).\n")
    md.append("- **Drift** in constants > 0.1 (totals) or > 1pp (NRFI) means the "
              "codebase needs a refresh from `historical_validate.py`.\n")
    return "\n".join(md)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Backtest the model against historical games")
    ap.add_argument("--start", type=int, default=2015)
    ap.add_argument("--end",   type=int, default=2024)
    ap.add_argument("--data-root", default="./mlb_data")
    args = ap.parse_args(argv)

    data_root = Path(args.data_root).expanduser().resolve()
    df = _load(args.start, args.end, data_root)
    results = evaluate(df)
    out_path = data_root / f"model_calibration_{args.start}_{args.end}.md"
    out_path.write_text(render(results))
    t = results["totals"]
    print(f"[done] {t['games']:,} games · "
          f"park-adj RMSE improvement {t['park_adj_improvement']:+.3f} · "
          f"Brier NRFI {t['brier_nrfi']} · Brier ML {t['brier_ml']}")
    print(f"       report → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
