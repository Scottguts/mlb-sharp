"""
build_dashboard.py — generates a single self-contained HTML dashboard
showing today's plays, overall record, and bankroll simulation.

The output file (`mlb_data/dashboard.html`) bakes in all the data so it
works offline. Open it in any browser. Mobile-friendly.

Run:
    python build_dashboard.py
    python build_dashboard.py --date 2026-04-25
    python build_dashboard.py --data-root ./mlb_data
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from bet_tracker import (
    DATA_ROOT_DEFAULT, LOG_FILENAME, _ensure_log, _read_log, _f, _i,
    _bucketize, Bucket,
)


RISK_COLOR = {
    "Max":      "#10B981",
    "Strong":   "#22C55E",
    "Standard": "#F59E0B",
    "Medium":   "#F59E0B",
    "Lean":     "#3B82F6",
    "Low":      "#3B82F6",
}
RISK_EMOJI = {"Max": "🎯", "Strong": "🔥", "Standard": "👀", "Medium": "👀",
              "Lean": "🪙", "Low": "🪙"}
MARKET_LABEL = {
    "moneyline": "Moneyline", "runline": "Run Line",
    "total": "Full-Game Total", "f5_total": "First 5 Total",
    "nrfi": "1st Inning",
}
BOOK_LABEL = {"fanduel": "FanDuel", "draftkings": "DraftKings",
              "betmgm": "BetMGM", "caesars": "Caesars"}


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def _load_grades(date_iso: str, data_root: Path):
    p = data_root / date_iso / "grades.json"
    if not p.exists(): return []
    return json.loads(p.read_text())

def _load_bet_log(data_root: Path):
    log = _ensure_log(data_root)
    return _read_log(log)


# ---------------------------------------------------------------------------
# Card / row renderers
# ---------------------------------------------------------------------------

def _fmt_price(p): return f"+{p}" if p > 0 else str(p)

def _esc(s): return html.escape(str(s) if s is not None else "")


def _render_play_card(game: dict, c: dict, idx: int) -> str:
    risk = c.get("risk", "Standard")
    color = RISK_COLOR.get(risk, "#6B7280")
    emoji = RISK_EMOJI.get(risk, "📊")
    book = BOOK_LABEL.get(c["book"].lower(), c["book"])
    market = MARKET_LABEL.get(c["market"], c["market"])
    line_str = f" @ {c['line']}" if c.get("line") is not None else ""
    fair_price = _fmt_price(c["fair_american"])
    price = _fmt_price(c["price_american"])

    reasoning = "".join(
        f'<li>{_esc(r)}</li>' for r in (c.get("reasoning") or [])[:5]
    ) or "<li class='muted'>No reasoning available</li>"

    triggers = "".join(
        f'<li>⚠ {_esc(t)}</li>' for t in (c.get("pass_triggers") or [])[:3]
    )

    return f"""
    <div class="play-card" style="border-left-color: {color};">
      <div class="play-header">
        <div class="play-title">
          <span class="play-emoji">{emoji}</span>
          <span class="play-num">Bet #{idx}</span>
          <span class="play-label">{_esc(c['bet_label'])}</span>
        </div>
        <div class="risk-badge" style="background: {color}22; color: {color}; border-color: {color}55;">
          {risk} · {c['unit_size']}u
        </div>
      </div>
      <div class="play-game">{_esc(game['matchup'])}</div>
      <div class="play-stats">
        <div class="stat"><div class="stat-label">Market</div><div class="stat-value">{_esc(market)}{_esc(line_str)}</div></div>
        <div class="stat"><div class="stat-label">Book</div><div class="stat-value strong">{_esc(book)}</div></div>
        <div class="stat"><div class="stat-label">Price</div><div class="stat-value strong" style="color: {color};">{price}</div></div>
        <div class="stat"><div class="stat-label">Edge</div><div class="stat-value">{c['edge']*100:.2f}%</div></div>
        <div class="stat"><div class="stat-label">Conf</div><div class="stat-value">{c['confidence']}/10</div></div>
        <div class="stat"><div class="stat-label">Fair</div><div class="stat-value">{fair_price} ({c['fair_prob']*100:.1f}%)</div></div>
      </div>
      <details class="play-details">
        <summary>Why this bet</summary>
        <ul class="reasoning">{reasoning}</ul>
        {f"<div class='triggers-label'>Pass if...</div><ul class='triggers'>{triggers}</ul>" if triggers else ""}
      </details>
    </div>
    """


def _render_record_table(rows):
    overall, by_cat = _bucketize(rows, None)
    out = """
    <table class="record-table">
      <thead>
        <tr>
          <th>Bucket</th><th>Bets</th><th>W-L-P</th><th>Win %</th>
          <th>Risked</th><th>P/L</th><th>ROI</th><th>Avg Edge</th>
        </tr>
      </thead>
      <tbody>
    """
    def _row(name, b: Bucket, is_overall=False):
        roi_color = "#22C55E" if b.roi > 0 else "#EF4444" if b.roi < 0 else "#94a3b8"
        cls = "overall" if is_overall else ""
        return f"""
        <tr class="{cls}">
          <td><strong>{_esc(name)}</strong></td>
          <td>{b.bets}</td>
          <td>{b.won}-{b.lost}-{b.push}</td>
          <td>{b.win_pct*100:.1f}%</td>
          <td>{b.units_risked:.2f}</td>
          <td style="color: {roi_color};"><strong>{b.units_pl:+.2f}</strong></td>
          <td style="color: {roi_color};">{b.roi*100:+.2f}%</td>
          <td>{b.avg_edge*100:.2f}%</td>
        </tr>"""
    out += _row("OVERALL", overall, True)
    for cat in ("moneyline", "runline", "total", "f5_total", "nrfi"):
        if cat in by_cat:
            out += _row(MARKET_LABEL.get(cat, cat), by_cat[cat])
    out += "</tbody></table>"
    return out


def _render_clv_table(rows):
    overall, by_cat = _bucketize(rows, None)
    if overall.clv_n == 0: return ""
    out = """
    <h3>Closing Line Value</h3>
    <p class="muted">Beat Close = your price was better than Pinnacle-devigged closing fair price.<br/>
    A sharp bettor averages +1-3% CLV across a large sample.</p>
    <table class="record-table">
      <thead><tr><th>Bucket</th><th>Bets w/ Close</th><th>Beat Close %</th><th>Avg CLV %</th></tr></thead>
      <tbody>
    """
    def _row(name, b):
        clv_color = "#22C55E" if b.avg_clv > 0 else "#EF4444"
        return f"""<tr><td><strong>{_esc(name)}</strong></td><td>{b.clv_n}</td>
        <td>{b.beat_close_pct*100:.1f}%</td>
        <td style="color: {clv_color};"><strong>{b.avg_clv*100:+.2f}%</strong></td></tr>"""
    out += _row("OVERALL", overall)
    for cat in ("moneyline", "runline", "total", "f5_total", "nrfi"):
        if cat in by_cat and by_cat[cat].clv_n > 0:
            out += _row(MARKET_LABEL.get(cat, cat), by_cat[cat])
    out += "</tbody></table>"
    return out


def _render_recent_settled(rows, n=15):
    settled = [r for r in rows if r["status"] in ("won", "lost", "push")]
    if not settled: return ""
    out = "<h3>Last Settled</h3><div class='settled-list'>"
    for r in settled[-n:][::-1]:
        st = r["status"]
        color = "#22C55E" if st == "won" else "#EF4444" if st == "lost" else "#94a3b8"
        pl = _f(r.get("units_pl"), 0)
        bet = f"{r['market']}/{r['side']}" + (f" {r['line']}" if r.get('line') else "")
        out += f"""
        <div class="settled-row" style="border-left-color: {color};">
          <div class="settled-meta">
            <span class="settled-date">{_esc(r['date'])}</span>
            <span class="settled-bet">{_esc(bet)} @ {_esc(r['book'].upper())}</span>
            <span class="settled-matchup muted">{_esc(r['matchup'])}</span>
          </div>
          <div class="settled-result" style="color: {color};">
            <strong>{st.upper()}</strong> · {pl:+.2f}u
          </div>
        </div>"""
    return out + "</div>"


# ---------------------------------------------------------------------------
# Build the page
# ---------------------------------------------------------------------------

def build(target: date, data_root: Path) -> Path:
    grades = _load_grades(target.isoformat(), data_root)
    bet_log = _load_bet_log(data_root)

    # Today's plays: pull cards from grades
    plays = []
    for g in grades:
        for c in g.get("bet_cards", []):
            plays.append((g, c))
    plays.sort(key=lambda gc: -(gc[1]["edge"] * gc[1]["confidence"]))

    n_games = len(grades)
    n_plays = len(plays)
    units = sum(c["unit_size"] for _, c in plays)
    best_edge = max((c["edge"] for _, c in plays), default=0)

    # Overall stats
    overall_b, _ = _bucketize(bet_log, None)
    last7_b, _ = _bucketize(bet_log, timedelta(days=7))
    last30_b, _ = _bucketize(bet_log, timedelta(days=30))

    # Render plays section
    plays_html = "".join(_render_play_card(g, c, i+1) for i, (g, c) in enumerate(plays))
    if not plays_html:
        plays_html = """
        <div class="no-plays">
          <div class="no-plays-icon">😴</div>
          <div class="no-plays-title">No plays today</div>
          <div class="no-plays-sub">No game cleared the edge + confidence filters.<br/>
          Sharp betting means most days you don't play.</div>
        </div>"""

    # Render no-play summary
    no_play_html = ""
    no_play_games = [g for g in grades if not g.get("bet_cards")]
    if no_play_games:
        no_play_html = "<div class='no-play-list'>"
        for g in no_play_games:
            no_play_html += f"""
            <div class="no-play-row">
              <span class="np-matchup">{_esc(g['matchup'])}</span>
              <span class="np-stats muted">
                Grade H{g['grade']['home']}/A{g['grade']['away']} ·
                xRuns {g['expected_total']} · F5 {g['expected_f5_total']} ·
                NRFI {g['nrfi_prob']*100:.1f}%
              </span>
            </div>"""
        no_play_html += "</div>"

    record_html  = _render_record_table(bet_log)
    clv_html     = _render_clv_table(bet_log)
    settled_html = _render_recent_settled(bet_log)

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MLB Sharp — {target.isoformat()}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ background: #020617; color: #e2e8f0; font-family: 'DM Sans', system-ui, sans-serif; min-height: 100vh; }}
body {{ background: radial-gradient(circle at 15% 0%, rgba(14,165,233,0.05), transparent 50%),
                  radial-gradient(circle at 85% 100%, rgba(124,58,237,0.05), transparent 50%); }}
.container {{ max-width: 960px; margin: 0 auto; padding: 16px 12px; }}
.muted {{ color: #94a3b8; }}
.glass {{ background: rgba(15,23,42,0.6); border: 1px solid rgba(148,163,184,0.1); border-radius: 16px; backdrop-filter: blur(8px); }}
.glass-inner {{ background: rgba(15,23,42,0.4); border: 1px solid rgba(148,163,184,0.08); border-radius: 12px; }}

/* Header */
.header {{ padding: 24px 20px; margin-bottom: 16px; position: relative; overflow: hidden;
           background: linear-gradient(135deg, rgba(14,165,233,0.08) 0%, rgba(15,23,42,0.7) 40%, rgba(124,58,237,0.06) 100%); }}
.header-top {{ display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; }}
.brand {{ display: flex; align-items: center; gap: 10px; }}
.brand-icon {{ font-size: 28px; }}
.brand-name {{ font-size: 24px; font-weight: 800; letter-spacing: -0.02em; }}
.brand-version {{ font-size: 11px; padding: 3px 8px; border-radius: 6px; background: rgba(167,139,250,0.15); color: #a78bfa; font-weight: 700; }}
.brand-meta {{ color: #94a3b8; font-size: 13px; margin-top: 6px; display: flex; gap: 12px; flex-wrap: wrap; }}
.brand-meta span.sep {{ color: #475569; }}
.header-stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 16px; }}
.stat-card {{ padding: 10px; background: rgba(15,23,42,0.5); border-radius: 10px; text-align: center; border: 1px solid rgba(148,163,184,0.08); }}
.stat-card .v {{ font-size: 22px; font-weight: 800; font-family: 'JetBrains Mono', monospace; }}
.stat-card .l {{ font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 2px; }}

/* Tabs */
.tabs {{ display: flex; gap: 6px; margin-bottom: 16px; flex-wrap: wrap; }}
.tab {{ padding: 8px 14px; border-radius: 10px; font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.15s;
        border: 1px solid rgba(148,163,184,0.08); background: rgba(15,23,42,0.5); color: #94a3b8; user-select: none; }}
.tab:hover {{ background: rgba(15,23,42,0.7); }}
.tab.active {{ background: linear-gradient(135deg, #0ea5e9, #0284c7); color: #fff; border-color: transparent;
               box-shadow: 0 4px 16px rgba(14,165,233,0.25); font-weight: 700; }}

/* Sections */
.section {{ display: none; }}
.section.active {{ display: block; }}
.section-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; padding: 16px 20px 0; }}
.section-title {{ display: flex; align-items: center; gap: 8px; font-size: 17px; font-weight: 700; }}

/* Play cards */
.play-card {{ padding: 16px; margin-bottom: 12px; border-left: 4px solid #6B7280;
              background: rgba(15,23,42,0.4); border-radius: 12px; border-top: 1px solid rgba(148,163,184,0.08);
              border-right: 1px solid rgba(148,163,184,0.08); border-bottom: 1px solid rgba(148,163,184,0.08); }}
.play-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; flex-wrap: wrap; gap: 8px; }}
.play-title {{ display: flex; align-items: center; gap: 8px; }}
.play-emoji {{ font-size: 20px; }}
.play-num {{ font-size: 12px; color: #94a3b8; font-weight: 600; }}
.play-label {{ font-size: 16px; font-weight: 800; }}
.risk-badge {{ padding: 4px 10px; border-radius: 8px; font-size: 11px; font-weight: 700; border: 1px solid; }}
.play-game {{ color: #cbd5e1; font-size: 13px; margin-bottom: 12px; }}
.play-stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }}
.stat {{ padding: 8px 10px; background: rgba(2,6,23,0.5); border-radius: 8px; }}
.stat-label {{ font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px; }}
.stat-value {{ font-size: 14px; font-weight: 600; font-family: 'JetBrains Mono', monospace; }}
.stat-value.strong {{ font-weight: 800; }}
.play-details {{ margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(148,163,184,0.08); }}
.play-details summary {{ cursor: pointer; font-size: 12px; color: #94a3b8; font-weight: 600; user-select: none; }}
.play-details summary:hover {{ color: #cbd5e1; }}
.reasoning, .triggers {{ list-style: none; margin-top: 8px; font-size: 13px; color: #cbd5e1; }}
.reasoning li, .triggers li {{ padding: 4px 0 4px 16px; position: relative; }}
.reasoning li::before {{ content: '•'; position: absolute; left: 0; color: #475569; }}
.triggers li {{ color: #f59e0b; }}
.triggers-label {{ font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 12px; font-weight: 700; }}

/* No plays */
.no-plays {{ text-align: center; padding: 60px 20px; }}
.no-plays-icon {{ font-size: 48px; margin-bottom: 12px; }}
.no-plays-title {{ font-size: 18px; font-weight: 700; margin-bottom: 6px; }}
.no-plays-sub {{ font-size: 13px; color: #94a3b8; line-height: 1.5; }}

.no-play-list {{ margin-top: 16px; }}
.no-play-row {{ padding: 10px 14px; border-radius: 8px; background: rgba(2,6,23,0.4); margin-bottom: 6px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; align-items: baseline; font-size: 13px; }}
.np-matchup {{ font-weight: 600; color: #cbd5e1; }}
.np-stats {{ font-size: 11px; font-family: 'JetBrains Mono', monospace; }}

/* Tables */
table.record-table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }}
table.record-table th {{ text-align: left; padding: 10px 8px; font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid rgba(148,163,184,0.1); font-weight: 700; }}
table.record-table td {{ padding: 10px 8px; border-bottom: 1px solid rgba(148,163,184,0.05); font-family: 'JetBrains Mono', monospace; }}
table.record-table tr.overall {{ background: rgba(99,102,241,0.05); }}
table.record-table tr:hover {{ background: rgba(15,23,42,0.4); }}

/* Settled list */
.settled-list {{ margin-top: 12px; }}
.settled-row {{ padding: 10px 14px; border-radius: 8px; background: rgba(2,6,23,0.4); margin-bottom: 6px; border-left: 3px solid;
                display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; align-items: baseline; font-size: 13px; }}
.settled-meta {{ display: flex; flex-direction: column; gap: 2px; }}
.settled-date {{ font-size: 11px; color: #64748b; font-family: 'JetBrains Mono', monospace; }}
.settled-bet {{ font-weight: 600; color: #cbd5e1; }}
.settled-matchup {{ font-size: 11px; }}
.settled-result {{ font-family: 'JetBrains Mono', monospace; }}

h3 {{ font-size: 15px; margin: 24px 0 12px; padding: 0 20px; font-weight: 700; }}
section.section .glass {{ padding: 20px; }}
@media (max-width: 600px) {{
  .header-stats {{ grid-template-columns: repeat(2, 1fr); }}
  .play-stats {{ grid-template-columns: repeat(2, 1fr); }}
  table.record-table {{ font-size: 11px; }}
}}
</style>
</head>
<body>
<div class="container">

  <!-- HEADER -->
  <div class="glass header">
    <div class="header-top">
      <div>
        <div class="brand">
          <span class="brand-icon">⚾</span>
          <span class="brand-name">MLB Sharp</span>
          <span class="brand-version">v1</span>
        </div>
        <div class="brand-meta">
          <span>{target.isoformat()}</span>
          <span class="sep">|</span>
          <span>{n_games} games</span>
          <span class="sep">|</span>
          <span>FD · DK · MGM · CZR</span>
        </div>
      </div>
      <div style="text-align: right;">
        <div style="font-size: 36px; font-weight: 800; color: #22C55E; line-height: 1; font-family: 'JetBrains Mono', monospace;">{n_plays}</div>
        <div style="font-size: 11px; color: #94a3b8; letter-spacing: 0.08em; text-transform: uppercase;">Plays Today</div>
      </div>
    </div>
    <div class="header-stats">
      <div class="stat-card"><div class="v" style="color: #22C55E;">{n_plays}</div><div class="l">Plays</div></div>
      <div class="stat-card"><div class="v" style="color: #F59E0B;">{units:.1f}u</div><div class="l">Exposure</div></div>
      <div class="stat-card"><div class="v" style="color: #60A5FA;">{best_edge*100:.1f}%</div><div class="l">Best Edge</div></div>
      <div class="stat-card"><div class="v" style="color: {('#22C55E' if overall_b.units_pl >= 0 else '#EF4444')};">{overall_b.units_pl:+.1f}u</div><div class="l">All-Time P/L</div></div>
    </div>
  </div>

  <!-- TABS -->
  <div class="tabs">
    <div class="tab active" data-tab="today">📅 Today</div>
    <div class="tab" data-tab="record">📊 Record</div>
    <div class="tab" data-tab="log">📝 Bet Log</div>
  </div>

  <!-- TODAY -->
  <section class="section active" id="today">
    <div class="glass">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
        <div class="section-title"><span>⚡</span><span>Top Plays</span></div>
        <span class="muted" style="font-size: 12px;">{target.isoformat()} · {n_games} games graded</span>
      </div>
      {plays_html}
      {f"<h3 style='padding-left:0;margin-top:24px;'>Other graded games</h3>{no_play_html}" if no_play_html else ""}
    </div>
  </section>

  <!-- RECORD -->
  <section class="section" id="record">
    <div class="glass">
      <div class="section-title"><span>📊</span><span>All-Time Record</span></div>
      {record_html}
      <h3 style="padding-left: 0;">Last 30 Days</h3>
      {_render_record_table([r for r in bet_log if r.get("date") and (date.fromisoformat(r["date"]) > date.today() - timedelta(days=30))]) if bet_log else "<p class='muted'>No bets logged yet.</p>"}
      {clv_html}
    </div>
  </section>

  <!-- LOG -->
  <section class="section" id="log">
    <div class="glass">
      <div class="section-title"><span>📝</span><span>Recent Activity</span></div>
      {settled_html or "<p class='muted'>No bets logged yet. The dashboard will populate as the daily cron logs your picks.</p>"}
    </div>
  </section>

  <div style="text-align: center; margin-top: 24px; padding: 16px; font-size: 11px; color: #475569;">
    Generated {datetime.now().strftime('%Y-%m-%d %H:%M %Z')} · MLB Sharp Bot
  </div>
</div>

<script>
document.querySelectorAll('.tab').forEach(t => {{
  t.addEventListener('click', () => {{
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.section').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    document.getElementById(t.dataset.tab).classList.add('active');
  }});
}});
</script>
</body>
</html>
"""

    out = data_root / "dashboard.html"
    out.write_text(html_doc)
    print(f"[dashboard] wrote {out} ({len(html_doc):,} bytes)")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--data-root", default=str(DATA_ROOT_DEFAULT))
    args = ap.parse_args(argv)
    target = date.fromisoformat(args.date) if args.date else date.today()
    build(target, Path(args.data_root).expanduser().resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
