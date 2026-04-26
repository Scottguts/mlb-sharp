"""
post_record.py — push the bet record to a dedicated Discord channel

Run after each settlement pass. Posts:
  1. A "settled today" summary (yesterday's bets + results)
  2. All-time record (overall + per-category)
  3. CLV summary (if any closing data)
  4. Pending bets queue

Configured via:
  DISCORD_RECORD_WEBHOOK_URL   — separate channel from your daily plays
                                 (falls back to DISCORD_WEBHOOK_URL if unset)

Run:
    python post_record.py                      # uses default data root
    python post_record.py --data-root ./mlb_data
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

from bet_tracker import (
    DATA_ROOT_DEFAULT, _ensure_log, _read_log, _bucketize, Bucket, _f, _i,
)


COLORS = {
    "good":      0x22C55E,   # green — winning P/L
    "bad":       0xEF4444,   # red — losing P/L
    "neutral":   0x6B7280,   # slate gray
    "header":    0x4F46E5,   # indigo
    "info":      0x60A5FA,   # blue
    "warning":   0xF59E0B,   # amber
}

MARKET_LABEL = {
    "moneyline": "Moneyline",
    "runline":   "Run Line",
    "total":     "FG Total",
    "f5_total":  "F5 Total",
    "nrfi":      "NRFI/YRFI",
}


def _color_for_pl(pl: float) -> int:
    return COLORS["good"] if pl > 0 else (COLORS["bad"] if pl < 0 else COLORS["neutral"])


def _build_settled_today_embed(rows: list[dict]) -> dict | None:
    """Show bets that settled today (or in last 24 hours)."""
    today = date.today()
    cutoff = today - timedelta(days=1)
    settled_today = []
    for r in rows:
        if r.get("status") not in ("won", "lost", "push"): continue
        # Use the bet's date — bets settled the day after they're placed
        try:
            bet_date = date.fromisoformat(r.get("date", ""))
        except Exception: continue
        if bet_date >= cutoff:
            settled_today.append(r)

    if not settled_today: return None

    won = sum(1 for r in settled_today if r["status"] == "won")
    lost = sum(1 for r in settled_today if r["status"] == "lost")
    push = sum(1 for r in settled_today if r["status"] == "push")
    pl = sum(_f(r.get("units_pl"), 0.0) for r in settled_today)

    lines = []
    for r in sorted(settled_today, key=lambda x: x.get("date", "")):
        st = r["status"]
        emoji = "✅" if st == "won" else "❌" if st == "lost" else "⏸"
        bet = f"{r['market']}/{r['side']}" + (f" {r['line']}" if r.get("line") else "")
        units_pl = _f(r.get("units_pl"), 0.0)
        sign = "+" if units_pl >= 0 else ""
        lines.append(
            f"{emoji} `{r['date']}` **{bet}** ({r['matchup']}) — {sign}{units_pl:.2f}u"
        )

    desc = "\n".join(lines)
    if len(desc) > 3500:
        desc = desc[:3500] + "\n…(truncated)"

    return {
        "title": "📊 RECENT SETTLED",
        "description": desc,
        "color": _color_for_pl(pl),
        "fields": [
            {"name": "Record",  "value": f"{won}-{lost}-{push}", "inline": True},
            {"name": "P/L",     "value": f"{'+' if pl>=0 else ''}{pl:.2f}u", "inline": True},
            {"name": "Bets",    "value": f"{len(settled_today)}", "inline": True},
        ],
    }


def _build_alltime_record_embed(rows: list[dict]) -> dict:
    overall, by_cat = _bucketize(rows, None)
    lines = [
        f"**OVERALL** · {overall.bets} bets · {overall.won}-{overall.lost}-{overall.push} · "
        f"{overall.win_pct*100:.1f}% · {overall.units_pl:+.2f}u · ROI {overall.roi*100:+.1f}%",
        "",
    ]
    for cat in ("moneyline", "runline", "total", "f5_total", "nrfi"):
        if cat not in by_cat: continue
        b = by_cat[cat]
        lines.append(
            f"**{MARKET_LABEL.get(cat, cat)}** · {b.bets} · {b.won}-{b.lost}-{b.push} · "
            f"{b.win_pct*100:.1f}% · {b.units_pl:+.2f}u · ROI {b.roi*100:+.1f}%"
        )
    return {
        "title": "📈 ALL-TIME RECORD",
        "description": "\n".join(lines),
        "color": _color_for_pl(overall.units_pl),
        "footer": {"text": f"Avg edge predicted: {overall.avg_edge*100:.2f}%  |  Total risked: {overall.units_risked:.1f}u"},
    }


def _build_clv_embed(rows: list[dict]) -> dict | None:
    overall, by_cat = _bucketize(rows, None)
    if overall.clv_n < 3: return None   # need at least 3 samples to be meaningful
    lines = [
        f"**OVERALL** ({overall.clv_n} bets w/ closing data) · "
        f"Beat Close {overall.beat_close_pct*100:.1f}% · "
        f"Avg CLV {overall.avg_clv*100:+.2f}%",
        "",
    ]
    for cat in ("moneyline", "runline", "total", "f5_total", "nrfi"):
        if cat not in by_cat or by_cat[cat].clv_n == 0: continue
        b = by_cat[cat]
        lines.append(
            f"**{MARKET_LABEL.get(cat, cat)}** · {b.clv_n} bets · "
            f"Beat Close {b.beat_close_pct*100:.0f}% · CLV {b.avg_clv*100:+.2f}%"
        )
    return {
        "title": "🎯 CLOSING LINE VALUE",
        "description": "\n".join(lines),
        "color": _color_for_pl(overall.avg_clv),
        "footer": {"text": "Sharp avg: +1-3% CLV. Negative CLV = the model is taking the wrong side."},
    }


def _build_pending_embed(rows: list[dict]) -> dict | None:
    pending = [r for r in rows if r.get("status") == "pending"]
    if not pending: return None
    lines = []
    for r in sorted(pending, key=lambda x: x.get("first_pitch", ""))[:20]:
        bet = f"{r['market']}/{r['side']}" + (f" {r['line']}" if r.get("line") else "")
        lines.append(f"⏳ `{r['date']}` **{bet}** ({r['matchup']}) — {r['units_risked']}u @ {r['book'].upper()}")
    desc = "\n".join(lines)
    return {
        "title": f"⏳ PENDING ({len(pending)} bets)",
        "description": desc,
        "color": COLORS["info"],
    }


def post(data_root: Path) -> bool:
    url = (os.environ.get("DISCORD_RECORD_WEBHOOK_URL")
           or os.environ.get("DISCORD_WEBHOOK_URL"))
    if not url:
        print("[record] no DISCORD_RECORD_WEBHOOK_URL or DISCORD_WEBHOOK_URL set — skipping")
        return False

    log = _ensure_log(data_root)
    rows = _read_log(log)
    if not rows:
        print("[record] empty bet log — nothing to post")
        return False

    embeds = []
    settled = _build_settled_today_embed(rows)
    if settled: embeds.append(settled)
    embeds.append(_build_alltime_record_embed(rows))
    clv = _build_clv_embed(rows)
    if clv: embeds.append(clv)
    pending = _build_pending_embed(rows)
    if pending: embeds.append(pending)

    # Discord allows 10 embeds per message
    payload = {"embeds": embeds[:10]}
    try:
        r = requests.post(url, json=payload, timeout=20)
        if r.status_code in (200, 204):
            print(f"[record] posted {len(embeds)} embeds to record channel")
            return True
        print(f"[record] post failed: HTTP {r.status_code} — {r.text[:200]}")
        return False
    except Exception as e:
        print(f"[record] post failed: {e}")
        return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=str(DATA_ROOT_DEFAULT))
    args = ap.parse_args(argv)
    post(Path(args.data_root).expanduser().resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
