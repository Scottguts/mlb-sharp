"""
historical_validate.py — pull a multi-year MLB outcome dataset and use it to
validate / calibrate the constants in the Sharp Betting System.

What this answers
-----------------
1. Are the league baselines correct? (LEAGUE_AVG_TOTAL, F5_LEAGUE_AVG,
   LEAGUE_NRFI_RATE in mlb_grader.py)
2. Are the park factors in mlb_data_scraper.py PARKS still in line with
   actual run scoring at each venue over the last N years?
3. How big is the year-to-year variance in those baselines? (informs how
   often constants need a refresh)

Why no historical-odds backtest?
-------------------------------
Free historical MLB odds with closing-line + alternate-market detail
don't exist at scale. We can only backtest the *model* — predicted vs
actual total runs, F5 runs, NRFI rate — not the full P/L of a betting
strategy. The CLV tracker in closing_snapshot.py is the right *forward*
proof-of-edge measurement; backtesting the model against 10 years of
outcomes is the right *backward* one.

Data source
-----------
statsapi.mlb.com — free, no API key, returns full schedule + linescore
detail per day. We hit one /schedule call per day and parse inning-by-
inning runs from the embedded linescore.

Caching
-------
Results are cached as parquet (or CSV if pyarrow is missing) at
./mlb_data/_history/games_<startYr>_<endYr>.parquet so re-runs are fast.

CLI
---
    python historical_validate.py                       # 2015-2024 default
    python historical_validate.py --start 2014 --end 2024
    python historical_validate.py --refresh             # force re-pull
    python historical_validate.py --years-only          # skip park-factor table
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

try:
    import pandas as pd
except ImportError:
    print("[error] pandas required. pip install pandas")
    sys.exit(1)

MLB_API = "https://statsapi.mlb.com/api/v1"
USER_AGENT = "mlb-sharp-historical-validate/1.0"

# Default backfill window — 10 full seasons ending last completed year.
DEFAULT_START_YEAR = 2015
DEFAULT_END_YEAR   = 2024


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------

def _get(url: str, params: dict, retries: int = 3) -> dict:
    headers = {"User-Agent": USER_AGENT}
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            time.sleep(1.5 ** i)
    raise RuntimeError(f"GET failed after retries: {last}")


def _parse_day(date_iso: str, payload: dict) -> list[dict]:
    """Parse one /schedule day into per-game rows we care about."""
    rows: list[dict] = []
    for d in payload.get("dates", []):
        for g in d.get("games", []):
            if g.get("gameType") != "R":           # regular season only
                continue
            status = g.get("status", {}).get("abstractGameState")
            if status != "Final":
                continue
            ls = g.get("linescore") or {}
            innings = ls.get("innings") or []
            if not innings:
                continue
            home_runs = ls.get("teams", {}).get("home", {}).get("runs")
            away_runs = ls.get("teams", {}).get("away", {}).get("runs")
            if home_runs is None or away_runs is None:
                continue
            f5 = 0
            first_inn = 0
            for i, inn in enumerate(innings):
                h = (inn.get("home") or {}).get("runs", 0) or 0
                a = (inn.get("away") or {}).get("runs", 0) or 0
                if i == 0: first_inn = h + a
                if i < 5:  f5 += h + a
            rows.append({
                "date":        date_iso,
                "season":      int(date_iso[:4]),
                "gamePk":      g["gamePk"],
                "venue_id":    g.get("venue", {}).get("id"),
                "venue_name":  g.get("venue", {}).get("name"),
                "home_team":   g["teams"]["home"]["team"]["name"],
                "away_team":   g["teams"]["away"]["team"]["name"],
                "home_runs":   home_runs,
                "away_runs":   away_runs,
                "total_runs":  home_runs + away_runs,
                "f5_runs":     f5,
                "first_inn":   first_inn,
                "innings":     len(innings),
            })
    return rows


def fetch_year(year: int, on_progress=None) -> list[dict]:
    """Pull every regular-season final game in a year.

    We hit /schedule once per day, hydrate=linescore, which gives us inning
    detail in a single call. Pacing: ~0.05s sleep between days to be polite.
    """
    out: list[dict] = []
    # Wide window — Mar 1 to Nov 5 covers the regular season + buffer.
    start = date(year, 3, 1)
    end = date(year, 11, 5)
    cur = start
    days = (end - start).days
    seen = 0
    while cur <= end:
        try:
            payload = _get(f"{MLB_API}/schedule", params={
                "sportId":  1,
                "date":     cur.isoformat(),
                "hydrate":  "linescore,team,venue",
            })
            out.extend(_parse_day(cur.isoformat(), payload))
        except Exception as e:
            print(f"  [warn] {cur}: {e}", file=sys.stderr)
        seen += 1
        if on_progress and seen % 30 == 0:
            on_progress(seen, days, len(out))
        cur += timedelta(days=1)
        time.sleep(0.05)
    return out


def load_or_fetch(start_year: int, end_year: int, cache_dir: Path,
                  refresh: bool = False) -> pd.DataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"games_{start_year}_{end_year}.parquet"
    csv_path   = cache_dir / f"games_{start_year}_{end_year}.csv"
    if not refresh:
        if cache_path.exists():
            try:
                return pd.read_parquet(cache_path)
            except Exception:
                pass
        if csv_path.exists():
            return pd.read_csv(csv_path)
    all_rows: list[dict] = []
    for year in range(start_year, end_year + 1):
        print(f"[fetch] year {year} …", flush=True)
        def progress(done, total, n):
            print(f"    {done}/{total} days, {n} games so far", flush=True)
        rows = fetch_year(year, progress)
        print(f"  → {year}: {len(rows)} regular-season finals")
        all_rows.extend(rows)
    df = pd.DataFrame(all_rows)
    try:
        df.to_parquet(cache_path, index=False)
        print(f"[cache] wrote {cache_path}")
    except Exception as e:
        df.to_csv(csv_path, index=False)
        print(f"[cache] parquet failed ({e}); wrote {csv_path}")
    return df


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def yearly_baselines(df: pd.DataFrame) -> pd.DataFrame:
    """Per-season league averages — answers 'is LEAGUE_AVG_TOTAL still right?'"""
    g = df.groupby("season").agg(
        games=("gamePk", "count"),
        total_runs=("total_runs", "mean"),
        f5_runs=("f5_runs", "mean"),
        nrfi_rate=("first_inn", lambda s: (s == 0).mean()),
        home_win_pct=("home_runs", lambda s: (s > df.loc[s.index, "away_runs"]).mean()),
    )
    return g.round(4)


def park_factors(df: pd.DataFrame, min_games: int = 200) -> pd.DataFrame:
    """Compute park run factors normalized vs league mean.

    pf_runs = (avg total at this park / avg total across all parks) * 100
    Result is comparable to the static numbers in mlb_data_scraper.PARKS.
    """
    league_avg = df["total_runs"].mean()
    grp = df.groupby(["venue_id", "venue_name"]).agg(
        games=("gamePk", "count"),
        avg_total=("total_runs", "mean"),
        avg_f5=("f5_runs", "mean"),
        nrfi_rate=("first_inn", lambda s: (s == 0).mean()),
    ).reset_index()
    grp = grp[grp["games"] >= min_games].copy()
    grp["pf_runs"] = (grp["avg_total"] / league_avg * 100).round(0).astype(int)
    grp = grp.sort_values("pf_runs", ascending=False)
    return grp


def calibration_check(df: pd.DataFrame, leagues: dict[int, dict]) -> str:
    """For each season, compute the RMSE of using that season's league mean
    as the only predictor of total runs. This is the *floor* — any model
    needs to beat this on out-of-sample years."""
    lines: list[str] = []
    lines.append("\n## Naive-predictor RMSE per season\n")
    lines.append("This is the RMSE you'd get predicting **the season's league mean** for every game. ")
    lines.append("Any actual model needs to beat this number on a held-out year to provide value.\n")
    lines.append("| Season | Games | League μ_total | RMSE if predicting μ |")
    lines.append("|---:|---:|---:|---:|")
    for season, sub in df.groupby("season"):
        mean_t = sub["total_runs"].mean()
        rmse = ((sub["total_runs"] - mean_t) ** 2).mean() ** 0.5
        lines.append(f"| {season} | {len(sub)} | {mean_t:.2f} | {rmse:.2f} |")
    return "\n".join(lines)


def render_report(df: pd.DataFrame, out_path: Path) -> Path:
    md: list[str] = []
    md.append(f"# Historical MLB Validation\n")
    md.append(f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}_  ")
    md.append(f"_Source: statsapi.mlb.com (regular-season finals only)_  ")
    md.append(f"_Window: {df['season'].min()}–{df['season'].max()}, "
              f"{len(df):,} games, {df['venue_id'].nunique()} unique venues_\n")

    md.append("\n## Yearly League Baselines\n")
    md.append("Use these to refresh the constants in `mlb_grader.py`. The "
              "trailing average across the window is the safest default.\n")
    yb = yearly_baselines(df)
    md.append("| Season | Games | μ Total | μ F5 | NRFI rate | Home win % |")
    md.append("|---:|---:|---:|---:|---:|---:|")
    for season, row in yb.iterrows():
        md.append(f"| {season} | {int(row['games'])} | {row['total_runs']:.2f} | "
                  f"{row['f5_runs']:.2f} | {row['nrfi_rate']*100:.1f}% | "
                  f"{row['home_win_pct']*100:.1f}% |")

    # Trailing window average — the recommended baseline for the constants
    recent = df[df["season"] >= df["season"].max() - 2]
    avg_total_recent = recent["total_runs"].mean()
    avg_f5_recent    = recent["f5_runs"].mean()
    nrfi_recent      = (recent["first_inn"] == 0).mean()
    home_win_recent  = (recent["home_runs"] > recent["away_runs"]).mean()
    md.append(f"\n**Recommended constants** (last 3 seasons, "
              f"{recent['season'].min()}–{recent['season'].max()}):\n")
    md.append("```python")
    md.append(f"LEAGUE_AVG_TOTAL = {avg_total_recent:.2f}    # mlb_grader.py")
    md.append(f"F5_LEAGUE_AVG    = {avg_f5_recent:.2f}")
    md.append(f"LEAGUE_NRFI_RATE = {nrfi_recent:.4f}")
    md.append(f"HOME_FIELD_PROB  = {home_win_recent - 0.50:+.4f}  # "
              f"home win pct minus 50%; current code uses 0.030")
    md.append("```")

    md.append("\n## Park Factors (last 3 seasons)\n")
    md.append("Computed as `(avg_total_at_park / league_avg_total) × 100`. ")
    md.append("Compare these to the `pf_runs` values in `PARKS` (mlb_data_scraper.py).\n")
    pf = park_factors(recent, min_games=60)
    md.append("| venue_id | Park | Games | avg total | avg F5 | NRFI rate | pf_runs |")
    md.append("|---:|---|---:|---:|---:|---:|---:|")
    for _, row in pf.iterrows():
        md.append(f"| {int(row['venue_id'])} | {row['venue_name']} | {int(row['games'])} | "
                  f"{row['avg_total']:.2f} | {row['avg_f5']:.2f} | {row['nrfi_rate']*100:.1f}% | "
                  f"{int(row['pf_runs'])} |")

    md.append(calibration_check(df, {}))

    md.append("\n## How to apply this report\n")
    md.append("1. Open `mlb_grader.py` and update `LEAGUE_AVG_TOTAL`, `F5_LEAGUE_AVG`, "
              "and `LEAGUE_NRFI_RATE` to match the **Recommended constants** block "
              "above. These are only used as fallback when the market line is "
              "unavailable, but keeping them current avoids weird grades on rare "
              "no-odds days.\n")
    md.append("2. Open `mlb_data_scraper.py` and compare each park's `pf_runs` "
              "to the table above. If any park is off by more than 3 points, "
              "update it in the `PARKS` dict.\n")
    md.append("3. The system's *forward-looking* proof-of-edge is CLV "
              "(`closing_snapshot.py` → `record.md`). This historical report "
              "validates the *baseline calibration*, not the betting strategy "
              "itself. Pair the two to spot drift.\n")

    out_path.write_text("\n".join(md))
    print(f"[report] wrote {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def auto_refit(data_root: Path, df: pd.DataFrame, dry_run: bool = False) -> dict:
    """Update LEAGUE_AVG_TOTAL / F5_LEAGUE_AVG / LEAGUE_NRFI_RATE /
    HOME_FIELD_PROB in mlb_grader.py and PARKS pf_runs in mlb_data_scraper.py
    to match the trailing 3-season averages from `df`.

    Idempotent: if the constants in code already match the recommended
    values (within tolerance), this writes nothing. Returns a summary dict
    of what changed.
    """
    import re
    repo = data_root.parent
    grader   = repo / "mlb_grader.py"
    scraper  = repo / "mlb_data_scraper.py"
    if not grader.exists() or not scraper.exists():
        return {"changed": [], "skipped": [], "error":
                f"can't find grader/scraper at {repo}"}

    recent = df[df["season"] >= df["season"].max() - 2]
    avg_total = round(float(recent["total_runs"].mean()), 2)
    avg_f5    = round(float(recent["f5_runs"].mean()), 2)
    nrfi_rate = round(float((recent["first_inn"] == 0).mean()), 4)
    home_pct  = round(float((recent["home_runs"] > recent["away_runs"]).mean()), 4)
    home_fp   = round(home_pct - 0.50, 4)

    summary: dict = {"changed": [], "skipped": [], "recommended": {
        "LEAGUE_AVG_TOTAL": avg_total, "F5_LEAGUE_AVG": avg_f5,
        "LEAGUE_NRFI_RATE": nrfi_rate, "HOME_FIELD_PROB": home_fp,
    }}

    # ----- Update grader constants -----
    grader_text = grader.read_text()
    grader_new = grader_text
    patterns = [
        ("LEAGUE_AVG_TOTAL", avg_total, r"LEAGUE_AVG_TOTAL\s*=\s*([\d.]+)", 0.05),
        ("F5_LEAGUE_AVG",    avg_f5,    r"F5_LEAGUE_AVG\s*=\s*([\d.]+)",    0.05),
        ("LEAGUE_NRFI_RATE", nrfi_rate, r"LEAGUE_NRFI_RATE\s*=\s*([\d.]+)", 0.005),
        ("HOME_FIELD_PROB",  home_fp,   r"HOME_FIELD_PROB\s*=\s*([\d.+-]+)", 0.005),
    ]
    for name, new_val, pat, tol in patterns:
        m = re.search(pat, grader_new)
        if not m:
            summary["skipped"].append(f"{name}: regex didn't match")
            continue
        old_val = float(m.group(1))
        if abs(old_val - new_val) < tol:
            summary["skipped"].append(f"{name}: in tolerance ({old_val} vs {new_val})")
            continue
        # Replace just the value, keep any trailing comment
        grader_new = re.sub(
            pat,
            f"{name} = {new_val}",
            grader_new, count=1)
        # Restore the comment at end of the original line if any (best effort)
        summary["changed"].append(f"{name}: {old_val} → {new_val}")

    if grader_new != grader_text and not dry_run:
        grader.write_text(grader_new)

    # ----- Update PARKS pf_runs (only when off by >= 3 from 3-yr data) -----
    league_avg = float(recent["total_runs"].mean())
    park_grp = recent.groupby("venue_id").agg(
        games=("gamePk", "count"),
        avg_total=("total_runs", "mean"),
    ).reset_index()
    park_grp["pf_new"] = (park_grp["avg_total"] / league_avg * 100).round(0).astype(int)
    park_grp = park_grp[park_grp["games"] >= 60]   # need a sample

    scraper_text = scraper.read_text()
    scraper_new = scraper_text
    park_changes: list[str] = []
    for _, row in park_grp.iterrows():
        vid = int(row["venue_id"])
        new_pf = int(row["pf_new"])
        # Find the "<vid>: {...}" line in PARKS dict
        line_re = re.compile(
            rf"(\b{vid}\s*:\s*\{{[^}}]*?\"pf_runs\"\s*:\s*)(\d+)",
            re.DOTALL,
        )
        m = line_re.search(scraper_new)
        if not m:
            continue
        old_pf = int(m.group(2))
        if abs(old_pf - new_pf) < 3:
            continue
        scraper_new = line_re.sub(rf"\g<1>{new_pf}", scraper_new, count=1)
        park_changes.append(f"venue {vid}: pf_runs {old_pf} → {new_pf}")

    if scraper_new != scraper_text and not dry_run:
        scraper.write_text(scraper_new)
    if park_changes:
        summary["changed"].append({"parks_updated": len(park_changes),
                                   "details": park_changes})
    summary["dry_run"] = dry_run
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Historical MLB outcome validator")
    ap.add_argument("--start", type=int, default=DEFAULT_START_YEAR,
                    help=f"first season to include (default {DEFAULT_START_YEAR})")
    ap.add_argument("--end",   type=int, default=DEFAULT_END_YEAR,
                    help=f"last season to include  (default {DEFAULT_END_YEAR})")
    ap.add_argument("--data-root", default="./mlb_data")
    ap.add_argument("--refresh", action="store_true",
                    help="force re-fetch (ignore cache)")
    ap.add_argument("--auto-refit", action="store_true",
                    help="rewrite mlb_grader.py constants and PARKS pf_runs in place")
    ap.add_argument("--dry-run", action="store_true",
                    help="with --auto-refit, only report what would change")
    args = ap.parse_args(argv)

    if args.start > args.end:
        print("[error] --start must be <= --end"); return 2
    data_root = Path(args.data_root).expanduser().resolve()
    cache = data_root / "_history"
    df = load_or_fetch(args.start, args.end, cache, refresh=args.refresh)
    if df.empty:
        print("[error] no rows fetched"); return 1
    out = data_root / f"historical_report_{args.start}_{args.end}.md"
    render_report(df, out)
    print(f"[done] {len(df):,} games across {df['season'].nunique()} seasons.")

    if args.auto_refit:
        result = auto_refit(data_root, df, dry_run=args.dry_run)
        prefix = "[dry-run]" if args.dry_run else "[auto-refit]"
        if result.get("error"):
            print(f"{prefix} error: {result['error']}")
            return 1
        for c in result.get("changed", []):
            print(f"{prefix} changed: {c}")
        for s in result.get("skipped", []):
            print(f"{prefix} skipped: {s}")
        if not result.get("changed"):
            print(f"{prefix} no changes — constants already in tolerance")
    return 0


if __name__ == "__main__":
    sys.exit(main())
