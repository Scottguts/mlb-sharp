"""
bet_tracker.py — bet log + settlement + record reporting
=========================================================

Maintains an append-only bet log (`bet_log.csv`) and a generated
record file (`record.md`) showing the overall record AND a separate
record per market category.

Three commands:

    python bet_tracker.py append   --date YYYY-MM-DD   # add today's recs as pending
    python bet_tracker.py settle                       # settle anything pending whose game has ended
    python bet_tracker.py report                       # rebuild record.md

Or in one shot at end-of-day:

    python bet_tracker.py daily    --date YYYY-MM-DD   # append + settle + report

Schema (one row per recommended bet):

    bet_id              str — sequential
    recommended_at      ISO timestamp
    date                YYYY-MM-DD
    gamePk              MLB Stats API game id
    matchup             "Away @ Home"
    first_pitch         ISO
    market              moneyline | runline | total | f5_total | nrfi
    side                home | away | over | under | nrfi | yrfi
    line                float (or empty)
    book                fanduel | draftkings | betmgm | caesars
    price               American odds at recommendation
    fair_prob           model fair prob
    fair_american       model fair price
    edge_pred           predicted edge (e.g. 0.045 = 4.5%)
    confidence          1-10
    units_risked        e.g. 1.5
    status              pending | won | lost | push | void
    units_pl            settled P/L in units (negative = loss)
    final_runs_h        from settled box score
    final_runs_a
    f5_runs             total runs through 5 innings
    first_inn_runs      runs scored in 1st
    settled_at          ISO
    notes               free text
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Paths & schema
# ---------------------------------------------------------------------------

DATA_ROOT_DEFAULT = Path("./mlb_data")
LOG_FILENAME      = "bet_log.csv"
REPORT_FILENAME   = "record.md"

CSV_FIELDS = [
    "bet_id", "recommended_at", "date", "gamePk", "matchup", "first_pitch",
    "market", "side", "line", "book", "price",
    "fair_prob", "fair_american", "edge_pred", "confidence", "units_risked",
    "status", "units_pl",
    "final_runs_h", "final_runs_a", "f5_runs", "first_inn_runs",
    "settled_at",
    # Player-prop fields — populated for market in
    # ('pitcher_strikeouts', 'pitcher_walks', 'batter_walks')
    "player_id", "player_name", "actual_result",
    # CLV (closing line value) — populated by closing_snapshot.py
    "closing_price", "closing_fair_prob", "clv_pct", "beat_close",
    "notes",
]


def _ensure_log_schema(log: Path) -> None:
    """Migrate existing CSVs to include any new columns. Idempotent."""
    if not log.exists(): return
    rows = _read_log(log)
    if not rows: return
    existing_cols = set(rows[0].keys())
    needed = set(CSV_FIELDS) - existing_cols
    if not needed: return
    # Re-write with full schema; missing values become empty strings
    _write_log(log, rows)

MLB_API = "https://statsapi.mlb.com/api/v1.1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_log(data_root: Path) -> Path:
    data_root.mkdir(parents=True, exist_ok=True)
    log = data_root / LOG_FILENAME
    if not log.exists():
        with log.open("w", newline="") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()
    else:
        _ensure_log_schema(log)
    return log

def _read_log(log: Path) -> list[dict]:
    if not log.exists(): return []
    with log.open() as f:
        return list(csv.DictReader(f))

def _write_log(log: Path, rows: list[dict]) -> None:
    # Atomic write so a crash mid-write can't truncate the whole bet log.
    log.parent.mkdir(parents=True, exist_ok=True)
    tmp = log.with_suffix(log.suffix + ".tmp")
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows: w.writerow({k: r.get(k, "") for k in CSV_FIELDS})
    os.replace(tmp, log)

def _next_id(rows: list[dict]) -> int:
    # Guard against a corrupted/blank bet_id cell crashing the whole append.
    ids = []
    for r in rows:
        try:
            ids.append(int(r.get("bet_id")))
        except (TypeError, ValueError):
            continue
    return (max(ids) + 1) if ids else 1

def _f(x, default=None):
    """float or default if blank/None"""
    if x is None or x == "": return default
    try: return float(x)
    except (ValueError, TypeError): return default

def _i(x, default=None):
    if x is None or x == "": return default
    try: return int(x)
    except (ValueError, TypeError): return default

def _payout_units(price_american: int, units_risked: float) -> float:
    """Profit in units when bet wins (excluding the stake)."""
    if price_american >= 100:
        return units_risked * (price_american / 100.0)
    else:
        return units_risked * (100.0 / -price_american)


# ---------------------------------------------------------------------------
# Append today's recommended bets
# ---------------------------------------------------------------------------

def append_pending(target_date: str, data_root: Path) -> int:
    grades_path = data_root / target_date / "grades.json"
    if not grades_path.exists():
        print(f"[append] no grades.json at {grades_path}; nothing to append")
        return 0
    grades = json.loads(grades_path.read_text())
    log = _ensure_log(data_root)
    rows = _read_log(log)
    existing_keys = {(r["date"], str(r["gamePk"]), r["market"], r["side"],
                      r["line"], r["book"]) for r in rows}
    next_id = _next_id(rows)
    added = 0
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for g in grades:
        for c in g.get("bet_cards", []):
            line = "" if c.get("line") is None else str(c["line"])
            key = (target_date, str(g["gamePk"]), c["market"], c["side"],
                   line, c["book"])
            if key in existing_keys: continue
            rows.append({
                "bet_id": str(next_id),
                "recommended_at": now,
                "date": target_date,
                "gamePk": str(g["gamePk"]),
                "matchup": g["matchup"],
                "first_pitch": g.get("gameDate", ""),
                "market": c["market"],
                "side": c["side"],
                "line": line,
                "book": c["book"],
                "price": str(c["price_american"]),
                "fair_prob": f"{c['fair_prob']:.4f}",
                "fair_american": str(c["fair_american"]),
                "edge_pred": f"{c['edge']:.4f}",
                "confidence": str(c["confidence"]),
                "units_risked": str(c["unit_size"]),
                "status": "pending",
                "units_pl": "",
                "final_runs_h": "", "final_runs_a": "",
                "f5_runs": "", "first_inn_runs": "",
                "settled_at": "",
                "player_id":   str(c.get("player_id", "") or ""),
                "player_name": c.get("player_name", "") or "",
                "actual_result": "",
                "closing_price": "", "closing_fair_prob": "",
                "clv_pct": "", "beat_close": "",
                "notes": "",
            })
            next_id += 1
            added += 1
    _write_log(log, rows)
    print(f"[append] added {added} pending bet(s) for {target_date}")
    return added


# ---------------------------------------------------------------------------
# Settlement
# ---------------------------------------------------------------------------

def _fetch_game_result(game_pk: int) -> dict | None:
    """Returns {'final': bool, 'home_runs': int, 'away_runs': int,
                'f5_runs': int, 'first_inn_runs': int} or None."""
    url = f"{MLB_API}/game/{game_pk}/feed/live"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [settle] error fetching gamePk {game_pk}: {e}")
        return None
    state = (data.get("gameData", {}).get("status", {}).get("abstractGameState"))
    if state != "Final":
        return {"final": False, "home_runs": None, "away_runs": None,
                "f5_runs": None, "first_inn_runs": None}
    ls = data.get("liveData", {}).get("linescore", {})
    home_runs = ls.get("teams", {}).get("home", {}).get("runs")
    away_runs = ls.get("teams", {}).get("away", {}).get("runs")
    innings = ls.get("innings", []) or []
    first_inn_runs = 0
    f5_runs = 0
    for i, inn in enumerate(innings):
        h = (inn.get("home") or {}).get("runs", 0) or 0
        a = (inn.get("away") or {}).get("runs", 0) or 0
        if i == 0: first_inn_runs = h + a
        if i < 5: f5_runs += (h + a)
    return {
        "final": True,
        "home_runs": home_runs, "away_runs": away_runs,
        "f5_runs": f5_runs, "first_inn_runs": first_inn_runs,
    }

PLAYER_PROP_MARKETS = ("pitcher_strikeouts", "pitcher_walks", "batter_strikeouts", "batter_walks")


def _player_actual(game_pk: int, player_id: int, market: str) -> int | None:
    """Pull a player's actual stat from the live feed box score. Returns None
    if game isn't Final or player didn't appear."""
    try:
        live = requests.get(f"{MLB_API}/game/{game_pk}/feed/live", timeout=20).json()
    except Exception:
        return None
    state = (live.get("gameData", {}).get("status", {}).get("abstractGameState"))
    if state != "Final": return None
    teams = live.get("liveData", {}).get("boxscore", {}).get("teams", {})
    for side in ("home", "away"):
        players = teams.get(side, {}).get("players", {})
        p = players.get(f"ID{player_id}")
        if not p: continue
        if market in ("pitcher_strikeouts", "pitcher_walks"):
            stats = p.get("stats", {}).get("pitching", {})
            field = "strikeOuts" if market == "pitcher_strikeouts" else "baseOnBalls"
        elif market in ("batter_strikeouts", "batter_walks"):
            stats = p.get("stats", {}).get("batting", {})
            field = "strikeOuts" if market == "batter_strikeouts" else "baseOnBalls"
        else:
            return None
        if not stats: return None
        v = stats.get(field)
        try: return int(v) if v is not None else None
        except (ValueError, TypeError): return None
    return None


def _settle_one(row: dict, result: dict) -> tuple[str, float, str]:
    """Returns (status, units_pl, notes)"""
    market = row["market"]; side = row["side"]
    line = _f(row["line"])
    price = _i(row["price"])
    risk = _f(row["units_risked"], 0.0)

    # Player-prop markets — settle via per-player box-score stat
    if market in PLAYER_PROP_MARKETS:
        pid = _i(row.get("player_id"))
        pk  = _i(row.get("gamePk"))
        if pid is None or pk is None:
            return ("void", 0.0, "missing player_id/gamePk")
        actual = _player_actual(pk, pid, market)
        if actual is None:
            return ("void", 0.0, "player did not appear / not final")
        push = (line == int(line) and actual == int(line))
        win = (actual > line) if side == "over" else (actual < line)
        # Stamp actual into the row so the bet log shows the result
        row["actual_result"] = str(actual)
        if push: return ("push", 0.0, f"push (actual {actual})")
        if win:  return ("won", round(_payout_units(price, risk), 4), f"actual {actual}")
        return ("lost", -round(risk, 4), f"actual {actual}")

    h = result["home_runs"]; a = result["away_runs"]
    if h is None or a is None:
        return ("void", 0.0, "no final score")
    win = False; push = False

    if market == "moneyline":
        win = (h > a) if side == "home" else (a > h)
    elif market == "runline":
        # line stored as the side's spread, e.g. -1.5 or +1.5
        if side == "home": margin = h - a
        else:              margin = a - h
        win = margin > -line   # margin > -(-1.5) i.e. margin > 1.5; or margin > -1.5
    elif market == "total":
        total = h + a
        if side == "over":  win = total > line
        elif side == "under": win = total < line
        if line == int(line) and total == int(line):
            push = True
    elif market == "f5_total":
        f5 = result["f5_runs"]
        if side == "over":  win = f5 > line
        elif side == "under": win = f5 < line
        if line == int(line) and f5 == int(line):
            push = True
    elif market == "nrfi":
        # side: 'nrfi' or 'yrfi'
        first = result["first_inn_runs"]
        win = (first == 0) if side == "nrfi" else (first > 0)
    else:
        return ("void", 0.0, f"unknown market {market}")

    if push: return ("push", 0.0, "push")
    if win:  return ("won", round(_payout_units(price, risk), 4), "")
    return ("lost", -round(risk, 4), "")

STALE_PENDING_DAYS = 3   # void pending bets > N days past first pitch if still not Final


def settle_pending(data_root: Path) -> int:
    log = _ensure_log(data_root)
    rows = _read_log(log)
    pending = [r for r in rows if r["status"] == "pending"]
    if not pending:
        print("[settle] nothing pending")
        return 0
    print(f"[settle] {len(pending)} pending bet(s) to check")
    settled = 0
    cache: dict[int, dict] = {}
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    now_dt = datetime.now(timezone.utc)
    for r in pending:
        pk = _i(r["gamePk"])
        if pk is None: continue
        if pk not in cache:
            cache[pk] = _fetch_game_result(pk) or {}
        result = cache[pk]
        if not result.get("final"):
            # Auto-void postponed/rescheduled games whose first pitch was
            # more than STALE_PENDING_DAYS ago and that still aren't Final
            # (MLB reuses the same gamePk for the make-up date, so the live
            # feed reports "Preview" again — without this guard the bet
            # would sit pending forever).
            fp = r.get("first_pitch")
            if fp:
                try:
                    ts = datetime.fromisoformat(fp.replace("Z", "+00:00"))
                    days_stale = (now_dt - ts).days
                    if days_stale >= STALE_PENDING_DAYS:
                        r["status"] = "void"
                        r["units_pl"] = "0.0000"
                        r["settled_at"] = now
                        r["notes"] = (r.get("notes") or "") + \
                            f" auto-void: {days_stale}d past first pitch, game not Final (likely postponed)"
                        settled += 1
                        print(f"  [void] bet {r['bet_id']} {r['matchup']} — postponed/stale ({days_stale}d)")
                except Exception:
                    pass
            continue
        status, units_pl, notes = _settle_one(r, result)
        r["status"] = status
        r["units_pl"] = f"{units_pl:.4f}"
        r["final_runs_h"] = str(result["home_runs"])
        r["final_runs_a"] = str(result["away_runs"])
        r["f5_runs"] = str(result["f5_runs"]) if result.get("f5_runs") is not None else ""
        r["first_inn_runs"] = str(result["first_inn_runs"]) if result.get("first_inn_runs") is not None else ""
        r["settled_at"] = now
        if notes: r["notes"] = (r.get("notes") or "") + " " + notes
        settled += 1
    _write_log(log, rows)
    print(f"[settle] settled {settled} bet(s)")
    return settled


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

@dataclass
class Bucket:
    bets: int = 0
    won: int = 0
    lost: int = 0
    push: int = 0
    units_risked: float = 0.0
    units_pl: float = 0.0
    edge_sum: float = 0.0
    edge_n: int = 0
    # CLV
    clv_sum: float = 0.0
    clv_n: int = 0
    beat_close_n: int = 0

    def add(self, row: dict) -> None:
        self.bets += 1
        ed = _f(row.get("edge_pred"))
        if ed is not None: self.edge_sum += ed; self.edge_n += 1
        clv = _f(row.get("clv_pct"))
        if clv is not None:
            self.clv_sum += clv; self.clv_n += 1
            if (row.get("beat_close") or "").lower() == "yes":
                self.beat_close_n += 1
        st = row["status"]
        if st == "pending": return
        risk = _f(row.get("units_risked"), 0.0)
        pl = _f(row.get("units_pl"), 0.0)
        self.units_risked += risk
        self.units_pl += pl
        if st == "won": self.won += 1
        elif st == "lost": self.lost += 1
        elif st == "push": self.push += 1

    @property
    def settled(self) -> int: return self.won + self.lost + self.push
    @property
    def win_pct(self) -> float:
        decided = self.won + self.lost
        return self.won / decided if decided else 0.0
    @property
    def roi(self) -> float:
        return (self.units_pl / self.units_risked) if self.units_risked else 0.0
    @property
    def avg_edge(self) -> float:
        return (self.edge_sum / self.edge_n) if self.edge_n else 0.0
    @property
    def avg_clv(self) -> float:
        return (self.clv_sum / self.clv_n) if self.clv_n else 0.0
    @property
    def beat_close_pct(self) -> float:
        return (self.beat_close_n / self.clv_n) if self.clv_n else 0.0


def _bucketize(rows: list[dict], window: timedelta | None = None) -> tuple[Bucket, dict[str, Bucket]]:
    overall = Bucket()
    by_cat: dict[str, Bucket] = {}
    today = date.today()
    for r in rows:
        if window is not None:
            try: rd = date.fromisoformat(r["date"])
            except Exception: continue
            if today - rd > window: continue
        overall.add(r)
        cat = r["market"]
        if cat not in by_cat: by_cat[cat] = Bucket()
        by_cat[cat].add(r)
    return overall, by_cat


def _render_bucket(b: Bucket, name: str) -> str:
    return (f"| {name:14s} | {b.bets:4d} | {b.won:3d}-{b.lost:3d}-{b.push:3d} | "
            f"{b.win_pct*100:5.1f}% | {b.units_risked:6.2f} | {b.units_pl:+7.2f} | "
            f"{b.roi*100:+6.2f}% | {b.avg_edge*100:5.2f}% |")


def build_report(data_root: Path) -> Path:
    log = _ensure_log(data_root)
    rows = _read_log(log)
    md: list[str] = [
        f"# MLB Sharp Betting — Record\n",
        f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}_  ",
        f"_Log: `{LOG_FILENAME}` (every recommended bet, append-only)_\n",
    ]

    # Header for the standard record table
    header = ("\n| Bucket         | Bets |   W-L-P  | Win %  | Risked | Profit  |   ROI   |  AvgEdge |\n"
              "|---             |-----:|:--------:|------:|------:|-------:|--------:|---------:|")

    for label, window in (("All Time", None),
                          ("Last 30 Days", timedelta(days=30)),
                          ("Last 7 Days", timedelta(days=7))):
        overall, by_cat = _bucketize(rows, window)
        md.append(f"\n## {label}\n")
        md.append(header)
        md.append(_render_bucket(overall, "OVERALL"))
        for cat in ("moneyline", "runline", "total", "f5_total", "nrfi"):
            if cat in by_cat:
                md.append(_render_bucket(by_cat[cat], cat))

    # Per-confidence-tier snapshot (all-time)
    overall, _ = _bucketize(rows, None)
    md.append("\n## By Confidence (All Time)\n")
    md.append(header)
    tiers = [("9-10", lambda c: c >= 9),
             ("7-8",  lambda c: 7 <= c <= 8),
             ("5-6",  lambda c: 5 <= c <= 6)]
    for tier_name, pred in tiers:
        b = Bucket()
        for r in rows:
            c = _i(r.get("confidence"))
            if c is None or not pred(c): continue
            b.add(r)
        md.append(_render_bucket(b, tier_name))

    # Per-book snapshot
    md.append("\n## By Book (All Time)\n")
    md.append(header)
    by_book: dict[str, Bucket] = {}
    for r in rows:
        bk = r.get("book", "?")
        if bk not in by_book: by_book[bk] = Bucket()
        by_book[bk].add(r)
    for bk, b in sorted(by_book.items()):
        md.append(_render_bucket(b, bk))

    # CLV section
    overall, by_cat = _bucketize(rows, None)
    if overall.clv_n > 0:
        md.append("\n## Closing Line Value (All Time)\n")
        md.append("_Beat Close = bet's implied prob better than Pinnacle-devigged closing fair prob._  ")
        md.append("_Avg CLV = avg %-points by which our price beat the close (positive is good)._\n")
        md.append("| Bucket         | Bets w/ Close | Beat Close % | Avg CLV % |\n"
                 "|---             |--------------:|-------------:|----------:|")
        md.append(f"| OVERALL        | {overall.clv_n:>13d} | {overall.beat_close_pct*100:>11.1f}% | "
                  f"{overall.avg_clv*100:>+8.2f}% |")
        for cat in ("moneyline", "runline", "total", "f5_total", "nrfi"):
            if cat in by_cat and by_cat[cat].clv_n > 0:
                b = by_cat[cat]
                md.append(f"| {cat:14s} | {b.clv_n:>13d} | {b.beat_close_pct*100:>11.1f}% | "
                          f"{b.avg_clv*100:>+8.2f}% |")

    # Open / pending
    pend = [r for r in rows if r["status"] == "pending"]
    if pend:
        md.append(f"\n## Pending ({len(pend)})\n")
        md.append("| Date | Matchup | Market | Side | Line | Book | Price | Units |\n"
                 "|---|---|---|---|---|---|---|---|")
        for r in pend[-25:]:
            md.append(f"| {r['date']} | {r['matchup']} | {r['market']} | {r['side']} | "
                      f"{r['line']} | {r['book']} | {r['price']} | {r['units_risked']} |")

    # Last 10 settled bets
    settled = [r for r in rows if r["status"] in ("won","lost","push")]
    if settled:
        md.append(f"\n## Last 10 Settled\n")
        md.append("| Date | Matchup | Bet | Book | Price | Units | Result | P/L |\n"
                 "|---|---|---|---|---|---|---|---|")
        for r in settled[-10:][::-1]:
            bet = f"{r['market']}/{r['side']}" + (f" {r['line']}" if r['line'] else "")
            md.append(f"| {r['date']} | {r['matchup']} | {bet} | {r['book']} | "
                      f"{r['price']} | {r['units_risked']} | {r['status']} | "
                      f"{_f(r['units_pl'], 0):+.2f} |")

    out = data_root / REPORT_FILENAME
    out.write_text("\n".join(md))
    print(f"[report] wrote {out}")
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["append", "settle", "report", "daily",
                                         "settle-paper-props", "paper-report"])
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--data-root", default=str(DATA_ROOT_DEFAULT))
    ap.add_argument("--window-days", type=int, default=7,
                    help="window for paper-props P/L report")
    args = ap.parse_args(argv)
    data_root = Path(args.data_root).expanduser().resolve()
    target = (date.fromisoformat(args.date) if args.date else date.today()).isoformat()

    if args.command == "append":
        append_pending(target, data_root)
    elif args.command == "settle":
        settle_pending(data_root)
    elif args.command == "report":
        build_report(data_root)
    elif args.command == "daily":
        # The order matters: settle yesterday before appending today, so
        # the freshly built report includes everything settled.
        settle_pending(data_root)
        append_pending(target, data_root)
        build_report(data_root)
    elif args.command == "settle-paper-props":
        from paper_props import settle_paper_props
        n = settle_paper_props(data_root)
        print(f"[paper-settle] settled {n} paper prop(s)")
    elif args.command == "paper-report":
        from paper_props import paper_pnl_summary, render_pnl_markdown
        summary = paper_pnl_summary(data_root, window_days=args.window_days)
        out = data_root / "prop_paper_record.md"
        out.write_text(render_pnl_markdown(summary))
        print(f"[paper-report] wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
