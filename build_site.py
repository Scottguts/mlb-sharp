"""
build_site.py — generates a static website (GitHub Pages compatible)

Reads everything from mlb_data/ and emits a self-contained site to docs/:

  docs/
  ├── index.html       single-page app, multi-tab
  ├── .nojekyll        prevents Pages from running Jekyll
  └── data/
      ├── manifest.json    list of dates + summary
      ├── <DATE>.json      per-day snapshot (graded games + cards + props)
      ├── bet_log.json     full bet log
      ├── paper_log.json   full paper-trading log
      └── record.json      aggregate stats

The HTML is a single page with vanilla JS tabs. No build step, no framework,
no external dependencies. Hosts free on GitHub Pages.

Run:
    python build_site.py                       # default ./mlb_data → ./docs
    python build_site.py --data-root ./mlb_data --out ./docs
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------

def _load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _read_csv(path: Path) -> list[dict]:
    if not path.exists(): return []
    with path.open() as f:
        return list(csv.DictReader(f))


def build_per_date_snapshot(date_iso: str, data_root: Path) -> dict | None:
    """Bundle one day's graded games + cards + tracked props into one JSON."""
    day_dir = data_root / date_iso
    if not day_dir.exists():
        return None
    grades = _load_json(day_dir / "grades.json") or []
    cards_md = (day_dir / "cards.md").read_text() if (day_dir / "cards.md").exists() else ""
    prop_md  = (day_dir / "prop_tracking.md").read_text() if (day_dir / "prop_tracking.md").exists() else ""
    return {
        "date": date_iso,
        "n_games": len(grades),
        "grades": grades,
        "cards_markdown": cards_md,
        "prop_tracking_markdown": prop_md,
    }


def build_manifest(data_root: Path) -> dict:
    """Discover all date subfolders + summary stats."""
    dates = []
    for d in sorted(data_root.iterdir()):
        if not d.is_dir(): continue
        name = d.name
        # Match YYYY-MM-DD
        if len(name) != 10 or name[4] != "-" or name[7] != "-": continue
        grades_path = d / "grades.json"
        if not grades_path.exists(): continue
        g = _load_json(grades_path) or []
        cards = sum(len(gm.get("bet_cards") or []) for gm in g)
        units = sum((c.get("unit_size") or 0) for gm in g for c in (gm.get("bet_cards") or []))
        dates.append({
            "date": name,
            "n_games": len(g),
            "n_cards": cards,
            "units_recommended": round(units, 2),
        })
    dates.sort(key=lambda d: d["date"], reverse=True)
    return {"dates": dates, "latest": dates[0]["date"] if dates else None,
            "generated_at": datetime.now().isoformat(timespec="minutes")}


def build_record_snapshot(data_root: Path) -> dict:
    """Aggregate stats from bet_log.csv — overall, per market, per window."""
    rows = _read_csv(data_root / "bet_log.csv")
    today = date.today()

    def _f(x, default=0.0):
        try: return float(x)
        except (ValueError, TypeError): return default

    def bucket(rows: list[dict]) -> dict:
        b = {"bets": 0, "won": 0, "lost": 0, "push": 0, "void": 0, "pending": 0,
             "units_risked": 0.0, "units_pl": 0.0, "edge_sum": 0.0, "edge_n": 0}
        for r in rows:
            b["bets"] += 1
            st = r.get("status", "")
            if st == "pending": b["pending"] += 1; continue
            if st == "void":    b["void"] += 1; continue
            risk = _f(r.get("units_risked"))
            pl   = _f(r.get("units_pl"))
            b["units_risked"] += risk
            b["units_pl"]     += pl
            ed = _f(r.get("edge_pred"));
            if ed: b["edge_sum"] += ed; b["edge_n"] += 1
            if st == "won":  b["won"]  += 1
            elif st == "lost": b["lost"] += 1
            elif st == "push": b["push"] += 1
        decided = b["won"] + b["lost"]
        b["win_pct"] = round(b["won"] / decided * 100, 1) if decided else 0.0
        b["roi"]     = round(b["units_pl"] / b["units_risked"] * 100, 2) if b["units_risked"] else 0.0
        b["avg_edge"] = round(b["edge_sum"] / b["edge_n"] * 100, 2) if b["edge_n"] else 0.0
        return b

    def in_window(r, days):
        try: d = date.fromisoformat(r.get("date", ""))
        except Exception: return False
        return d >= today - timedelta(days=days)

    out = {
        "all_time":      bucket(rows),
        "last_30":       bucket([r for r in rows if in_window(r, 30)]),
        "last_7":        bucket([r for r in rows if in_window(r, 7)]),
        "by_market":     {},
        "by_confidence": {},
        "by_book":       {},
    }
    for m in ("moneyline", "runline", "total", "f5_total", "nrfi"):
        out["by_market"][m] = bucket([r for r in rows if r.get("market") == m])
    for tier_name, lo, hi in (("9-10", 9, 10), ("7-8", 7, 8), ("5-6", 5, 6)):
        def matches(r):
            try: c = int(r.get("confidence", 0))
            except Exception: return False
            return lo <= c <= hi
        out["by_confidence"][tier_name] = bucket([r for r in rows if matches(r)])
    for bk in ("fanduel", "draftkings", "betmgm", "caesars"):
        out["by_book"][bk] = bucket([r for r in rows if r.get("book") == bk])
    return out


def build_paper_snapshot(data_root: Path) -> dict:
    rows = _read_csv(data_root / "prop_paper_log.csv")
    today = date.today()

    def _f(x, default=0.0):
        try: return float(x)
        except (ValueError, TypeError): return default

    def bucket(rs: list[dict]) -> dict:
        b = {"bets": 0, "won": 0, "lost": 0, "push": 0, "void": 0, "pending": 0,
             "units_risked": 0.0, "units_pl": 0.0}
        for r in rs:
            b["bets"] += 1
            st = r.get("status", "")
            if st == "pending": b["pending"] += 1; continue
            if st == "void":    b["void"] += 1; continue
            b["units_risked"] += _f(r.get("units_risked"))
            b["units_pl"]     += _f(r.get("units_pl"))
            if st == "won":  b["won"]  += 1
            elif st == "lost": b["lost"] += 1
            elif st == "push": b["push"] += 1
        d = b["won"] + b["lost"]
        b["win_pct"] = round(b["won"] / d * 100, 1) if d else 0.0
        b["roi"]     = round(b["units_pl"] / b["units_risked"] * 100, 2) if b["units_risked"] else 0.0
        return b

    def in_window(r, days):
        try: d = date.fromisoformat(r.get("date", ""))
        except Exception: return False
        return d >= today - timedelta(days=days)

    by_market = {}
    for m in sorted({r.get("market", "") for r in rows if r.get("market")}):
        by_market[m] = bucket([r for r in rows if r.get("market") == m])
    return {
        "all_time":  bucket(rows),
        "last_7":    bucket([r for r in rows if in_window(r, 7)]),
        "by_market": by_market,
        "rows": rows[-200:],   # last 200 for the table
    }


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MLB Sharp — Predictions & Track Record</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #020617; --fg: #e2e8f0; --muted: #94a3b8; --border: rgba(148,163,184,0.12);
  --green: #22C55E; --red: #EF4444; --amber: #F59E0B; --blue: #3B82F6; --indigo: #4F46E5;
  --emerald: #10B981; --slate: #6B7280;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { background: var(--bg); color: var(--fg); font-family: 'DM Sans', system-ui, sans-serif; min-height: 100vh; }
body {
  background:
    radial-gradient(circle at 15% 0%, rgba(14,165,233,0.05), transparent 50%),
    radial-gradient(circle at 85% 100%, rgba(124,58,237,0.05), transparent 50%);
}
.container { max-width: 1100px; margin: 0 auto; padding: 16px 12px; }
.muted { color: var(--muted); }
.glass { background: rgba(15,23,42,0.6); border: 1px solid var(--border); border-radius: 16px; backdrop-filter: blur(8px); padding: 20px; }
a { color: #38bdf8; text-decoration: none; }
a:hover { text-decoration: underline; }

/* Header */
header { padding: 24px 20px; margin-bottom: 16px;
  background: linear-gradient(135deg, rgba(14,165,233,0.08) 0%, rgba(15,23,42,0.7) 40%, rgba(124,58,237,0.06) 100%);
  border-radius: 16px; border: 1px solid var(--border); }
.brand { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.brand-name { font-size: 28px; font-weight: 800; letter-spacing: -0.02em; }
.brand-sub { color: var(--muted); margin-top: 4px; font-size: 13px; }
.pill { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; background: rgba(167,139,250,0.18); color: #a78bfa; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 20px; }
@media (max-width: 640px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } }
.stat-card { padding: 12px; background: rgba(15,23,42,0.55); border-radius: 12px; text-align: center; border: 1px solid var(--border); }
.stat-card .v { font-size: 22px; font-weight: 800; font-family: 'JetBrains Mono', monospace; }
.stat-card .l { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; margin-top: 2px; }

/* Tabs */
.tabs { display: flex; gap: 6px; margin-bottom: 16px; flex-wrap: wrap; }
.tab { padding: 10px 16px; border-radius: 10px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.15s;
       border: 1px solid var(--border); background: rgba(15,23,42,0.5); color: var(--muted); user-select: none; }
.tab:hover { background: rgba(15,23,42,0.75); color: var(--fg); }
.tab.active { background: linear-gradient(135deg, #0ea5e9, #0284c7); color: #fff; border-color: transparent;
              box-shadow: 0 4px 16px rgba(14,165,233,0.25); }

/* Sections */
.section { display: none; }
.section.active { display: block; }
.section-title { display: flex; align-items: center; gap: 8px; font-size: 18px; font-weight: 700; margin-bottom: 16px; }

/* Date picker */
.date-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.date-bar select { background: rgba(15,23,42,0.6); color: var(--fg); border: 1px solid var(--border);
                    border-radius: 10px; padding: 8px 12px; font-family: 'JetBrains Mono', monospace; font-size: 13px;
                    cursor: pointer; }
.date-bar .nav-btn { padding: 8px 12px; background: rgba(15,23,42,0.6); color: var(--fg); border: 1px solid var(--border);
                     border-radius: 10px; cursor: pointer; font-size: 13px; }
.date-bar .nav-btn:hover { background: rgba(15,23,42,0.9); }

/* Game / play cards */
.game-row { padding: 14px; margin-bottom: 10px; background: rgba(15,23,42,0.4); border-radius: 12px;
            border: 1px solid var(--border); border-left: 4px solid var(--slate); }
.game-row.has-bet { border-left-color: var(--emerald); }
.game-row.no-bet { opacity: 0.78; }
.game-head { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
.game-title { font-weight: 700; font-size: 15px; }
.game-time { font-size: 12px; color: var(--muted); }
.game-stats { display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: var(--muted); }
.game-stats b { color: var(--fg); font-family: 'JetBrains Mono', monospace; }
.bet-pill { display: inline-block; padding: 4px 8px; border-radius: 8px; font-size: 11px; font-weight: 700; background: rgba(34,197,94,0.12); color: var(--green); border: 1px solid rgba(34,197,94,0.3); margin-top: 6px; }

/* Tables */
.table-wrap { overflow-x: auto; margin: 12px 0; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 9px 12px; text-align: left; border-bottom: 1px solid var(--border); }
th { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; }
td { font-family: 'JetBrains Mono', monospace; font-size: 13px; }
td.text { font-family: 'DM Sans', sans-serif; }
tr.overall td { font-weight: 800; }
.pos { color: var(--green); }
.neg { color: var(--red); }

/* Filter chips */
.chips { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }
.chip { padding: 5px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; background: rgba(15,23,42,0.5); color: var(--muted); cursor: pointer; border: 1px solid var(--border); }
.chip.active { background: rgba(14,165,233,0.18); color: #38bdf8; border-color: rgba(14,165,233,0.3); }

/* About */
.about p { margin-bottom: 12px; line-height: 1.6; color: #cbd5e1; }
.about h3 { margin: 18px 0 8px; font-size: 15px; }
.about ul { padding-left: 22px; margin-bottom: 12px; color: #cbd5e1; }
.about li { margin-bottom: 4px; }

.footer { text-align: center; margin-top: 24px; padding: 16px; font-size: 11px; color: #475569; }
.loading { text-align: center; padding: 40px; color: var(--muted); }
</style>
</head>
<body>
<div class="container">

  <header>
    <div class="brand">
      <div>
        <div class="brand-name">⚾ MLB Sharp</div>
        <div class="brand-sub">Market-anchored model · automated daily · open methodology</div>
      </div>
      <span class="pill" id="generated-label">loading…</span>
    </div>
    <div class="stats-grid" id="hero-stats">
      <div class="stat-card"><div class="v" id="hero-record">—</div><div class="l">All-Time Record</div></div>
      <div class="stat-card"><div class="v" id="hero-roi">—</div><div class="l">All-Time ROI</div></div>
      <div class="stat-card"><div class="v" id="hero-pl">—</div><div class="l">All-Time P/L</div></div>
      <div class="stat-card"><div class="v" id="hero-edge">—</div><div class="l">Avg Predicted Edge</div></div>
    </div>
  </header>

  <div class="tabs" role="tablist">
    <div class="tab active" data-tab="today">📅 Today</div>
    <div class="tab" data-tab="history">📆 History</div>
    <div class="tab" data-tab="record">📊 Track Record</div>
    <div class="tab" data-tab="bets">📝 Bet Log</div>
    <div class="tab" data-tab="props">🎯 Paper Props</div>
    <div class="tab" data-tab="about">ℹ️ About</div>
  </div>

  <!-- Today -->
  <section class="section active" id="today">
    <div class="glass">
      <div class="section-title">⚡ Today's Slate</div>
      <div class="date-bar">
        <span class="muted">Showing:</span>
        <span id="today-date" style="font-family: 'JetBrains Mono', monospace;">—</span>
      </div>
      <div id="today-games" class="loading">Loading today's games…</div>
    </div>
  </section>

  <!-- History -->
  <section class="section" id="history">
    <div class="glass">
      <div class="section-title">📆 Historical Slate Browser</div>
      <div class="date-bar">
        <button class="nav-btn" id="hist-prev">← Prev</button>
        <select id="hist-select"></select>
        <button class="nav-btn" id="hist-next">Next →</button>
        <span class="muted" id="hist-count" style="margin-left: auto; font-size: 12px;"></span>
      </div>
      <div id="hist-content" class="loading">Pick a date.</div>
    </div>
  </section>

  <!-- Record -->
  <section class="section" id="record">
    <div class="glass">
      <div class="section-title">📊 Track Record</div>
      <div id="record-content" class="loading">Loading record…</div>
    </div>
  </section>

  <!-- Bets -->
  <section class="section" id="bets">
    <div class="glass">
      <div class="section-title">📝 Full Bet Log</div>
      <div class="chips" id="bets-filter">
        <div class="chip active" data-filter="all">All</div>
        <div class="chip" data-filter="won">Won</div>
        <div class="chip" data-filter="lost">Lost</div>
        <div class="chip" data-filter="pending">Pending</div>
        <div class="chip" data-filter="moneyline">Moneyline</div>
        <div class="chip" data-filter="total">Total</div>
      </div>
      <div id="bets-content" class="loading">Loading…</div>
    </div>
  </section>

  <!-- Paper Props -->
  <section class="section" id="props">
    <div class="glass">
      <div class="section-title">🎯 Paper Trading — Player Props</div>
      <p class="muted" style="margin-bottom: 16px; font-size: 13px;">
        Phase 2 backtest. Pitcher strikeouts, pitcher walks, and batter walks tracked
        with 0.5u paper sizing. <b>No real money is bet from these markets yet</b> —
        we're testing whether prop edges sustain higher ROI than ML/total before promoting.
      </p>
      <div id="props-content" class="loading">Loading…</div>
    </div>
  </section>

  <!-- About -->
  <section class="section" id="about">
    <div class="glass about">
      <div class="section-title">ℹ️ About this system</div>
      <p>An end-to-end automated MLB sharp betting system. Every day at ~11 AM ET, GitHub Actions
        scrapes the slate, grades every game across 7 categories, anchors the model to Pinnacle's
        no-vig fair price, and pushes a sized betting card to Discord when (and only when) the
        edges clear strict gates.</p>
      <h3>How a play earns its way onto the card</h3>
      <ul>
        <li>Model probability must clear the per-market <b>MIN_EDGE</b> threshold (2.5–3.5%).</li>
        <li>Confidence must be ≥6/10 — combines grade-gap and edge-size, both axes required.</li>
        <li>Edge must be ≤12% (anything higher = calibration bug, rejected).</li>
        <li>Max 5 plays per slate, 6u total exposure, 1 play per game.</li>
        <li>Plausibility guards filter out misclassified DH games / alt-line markets.</li>
      </ul>
      <h3>Signals the model uses</h3>
      <ul>
        <li><b>Pitching:</b> velocity trend, CSW%, pitch movement shifts, splits vs hand</li>
        <li><b>Bullpen:</b> usage fatigue + K%/BB%/ERA quality + handedness availability</li>
        <li><b>Offense:</b> platoon edges, recent RPG, top-of-order wOBA, 7-day rolling form</li>
        <li><b>Weather/park:</b> 10-yr calibrated park factors, wind × CF orientation, temp</li>
        <li><b>Catcher framing:</b> elite framers boost K projections, soft framers cost runs</li>
        <li><b>Umpire:</b> live 60-day K-tendency from MLB Stats API</li>
        <li><b>Travel:</b> cross-country flights flag the offense</li>
        <li><b>Market anchor:</b> Pinnacle devigged fair price as Bayesian prior (capped ±5pp)</li>
      </ul>
      <h3>What it is — and isn't</h3>
      <p>It is a research / paper-trading system with a real-money betting layer running on the
        same model. All numbers shown are <b>recommended</b> bets — actual results depend on whether
        the user placed them. Past performance does not guarantee future results.</p>
      <p>Source: <a href="https://github.com/Scottguts/mlb-sharp" target="_blank">github.com/Scottguts/mlb-sharp</a></p>
    </div>
  </section>

  <div class="footer" id="footer">Updated daily by the GitHub Actions cron · last build: loading…</div>
</div>

<script>
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

// Tabs
$$('.tab').forEach(t => {
  t.addEventListener('click', () => {
    $$('.tab').forEach(x => x.classList.remove('active'));
    $$('.section').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    $(`#${t.dataset.tab}`).classList.add('active');
  });
});

// Helpers
const fmt = (n, decimals=2) => (n === undefined || n === null || Number.isNaN(n)) ? '—' : Number(n).toFixed(decimals);
const fmtPrice = (n) => n > 0 ? `+${n}` : `${n}`;
const cls = (n) => n > 0 ? 'pos' : (n < 0 ? 'neg' : '');
function fmtPL(n) { if (n === undefined || n === null) return '—'; const c = cls(n); const s = (n > 0 ? '+' : '') + Number(n).toFixed(2) + 'u'; return `<span class="${c}">${s}</span>`; }
function fmtPct(n) { if (n === undefined || n === null) return '—'; const c = cls(n); const s = (n > 0 ? '+' : '') + Number(n).toFixed(2) + '%'; return `<span class="${c}">${s}</span>`; }

// State
let manifest = null;
let record = null;
let paperData = null;
let betLog = null;
let currentDateData = null;

const DATA = 'data';

async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

async function loadManifest() {
  manifest = await fetchJSON(`${DATA}/manifest.json`);
  $('#generated-label').textContent = `updated ${manifest.generated_at.replace('T', ' ')}`;
  $('#footer').textContent = `Updated daily by GitHub Actions · last build: ${manifest.generated_at.replace('T', ' ')}`;
  // Date picker
  const sel = $('#hist-select');
  sel.innerHTML = '';
  manifest.dates.forEach(d => {
    const opt = document.createElement('option');
    opt.value = d.date;
    opt.textContent = `${d.date} — ${d.n_games} games, ${d.n_cards} plays (${d.units_recommended}u)`;
    sel.appendChild(opt);
  });
  $('#hist-count').textContent = `${manifest.dates.length} dates archived`;
  sel.addEventListener('change', () => loadDate(sel.value, 'hist-content'));
  $('#hist-prev').addEventListener('click', () => { sel.selectedIndex = Math.min(sel.selectedIndex + 1, sel.options.length - 1); sel.dispatchEvent(new Event('change')); });
  $('#hist-next').addEventListener('click', () => { sel.selectedIndex = Math.max(sel.selectedIndex - 1, 0); sel.dispatchEvent(new Event('change')); });
}

function gameCardHTML(gm) {
  const cards = gm.bet_cards || [];
  const hasBet = cards.length > 0;
  const klass = hasBet ? 'game-row has-bet' : 'game-row no-bet';
  const time = gm.gameDate ? new Date(gm.gameDate).toLocaleString('en-US', {hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York'}) + ' ET' : '';
  let betsHTML = '';
  for (const c of cards) {
    const edge = (c.edge * 100).toFixed(2);
    const price = fmtPrice(c.price_american);
    const line = (c.line !== null && c.line !== undefined) ? ` ${c.line}` : '';
    betsHTML += `<span class="bet-pill">${c.bet_label}${line} @ ${c.book.toUpperCase()} ${price} · ${edge}% edge · ${c.unit_size}u · conf ${c.confidence}/10</span> `;
  }
  return `
    <div class="${klass}">
      <div class="game-head">
        <div>
          <div class="game-title">${gm.matchup}</div>
          <div class="game-time">${time}</div>
        </div>
        <div class="game-stats">
          <span>Grade <b>H${fmt(gm.grade.home, 1)} / A${fmt(gm.grade.away, 1)}</b></span>
          <span>WP <b>${(gm.win_prob.home*100).toFixed(1)}% / ${(gm.win_prob.away*100).toFixed(1)}%</b></span>
          <span>xRuns <b>${gm.expected_total}</b></span>
          <span>F5 <b>${gm.expected_f5_total}</b></span>
          <span>NRFI <b>${(gm.nrfi_prob*100).toFixed(1)}%</b></span>
        </div>
      </div>
      ${betsHTML}
    </div>`;
}

async function loadDate(dateIso, targetId) {
  const el = $(`#${targetId}`);
  el.innerHTML = '<div class="loading">Loading…</div>';
  try {
    const d = await fetchJSON(`${DATA}/${dateIso}.json`);
    if (targetId === 'today-games') $('#today-date').textContent = dateIso;
    let html = '';
    for (const gm of d.grades) html += gameCardHTML(gm);
    el.innerHTML = html || '<div class="muted">No games this date.</div>';
  } catch (e) {
    el.innerHTML = `<div class="muted">Could not load ${dateIso}: ${e.message}</div>`;
  }
}

async function loadRecord() {
  if (record === null) record = await fetchJSON(`${DATA}/record.json`);
  // Hero
  const at = record.all_time;
  $('#hero-record').textContent = `${at.won}-${at.lost}-${at.push}`;
  $('#hero-roi').innerHTML = fmtPct(at.roi);
  $('#hero-pl').innerHTML = fmtPL(at.units_pl);
  $('#hero-edge').textContent = `${fmt(at.avg_edge, 1)}%`;
  // Table builder
  function tbl(title, buckets) {
    let html = `<h3 style="margin: 16px 0 8px;">${title}</h3><div class="table-wrap"><table><thead><tr>
      <th>Bucket</th><th>Bets</th><th>W-L-P</th><th>Win%</th><th>Risked</th><th>P/L</th><th>ROI</th><th>Avg Edge</th></tr></thead><tbody>`;
    for (const [name, b] of buckets) {
      html += `<tr><td class="text">${name}</td><td>${b.bets}</td><td>${b.won}-${b.lost}-${b.push}</td>
        <td>${fmt(b.win_pct,1)}%</td><td>${fmt(b.units_risked,1)}u</td><td>${fmtPL(b.units_pl)}</td>
        <td>${fmtPct(b.roi)}</td><td>${fmt(b.avg_edge,2)}%</td></tr>`;
    }
    html += '</tbody></table></div>';
    return html;
  }
  let html = '';
  html += tbl('Time windows', [['All-Time', record.all_time], ['Last 30 days', record.last_30], ['Last 7 days', record.last_7]]);
  html += tbl('By market', Object.entries(record.by_market));
  html += tbl('By confidence', Object.entries(record.by_confidence));
  html += tbl('By book', Object.entries(record.by_book));
  $('#record-content').innerHTML = html;
}

let betsFilter = 'all';
async function loadBets() {
  if (betLog === null) betLog = await fetchJSON(`${DATA}/bet_log.json`);
  renderBets();
}
function renderBets() {
  let rows = betLog || [];
  if (betsFilter !== 'all') {
    if (['won','lost','pending'].includes(betsFilter)) rows = rows.filter(r => r.status === betsFilter);
    else rows = rows.filter(r => r.market === betsFilter);
  }
  rows = rows.slice().reverse();
  let html = `<div class="muted" style="margin-bottom: 8px; font-size: 12px;">${rows.length} rows</div>
    <div class="table-wrap"><table><thead><tr>
      <th>Date</th><th>Matchup</th><th>Market</th><th>Side</th><th>Line</th><th>Book</th>
      <th>Price</th><th>Edge</th><th>Conf</th><th>Units</th><th>Status</th><th>P/L</th></tr></thead><tbody>`;
  for (const r of rows.slice(0, 300)) {
    const edge = r.edge_pred ? `${(Number(r.edge_pred)*100).toFixed(2)}%` : '—';
    const pl = (r.units_pl !== '' && r.units_pl !== undefined) ? fmtPL(Number(r.units_pl)) : '—';
    html += `<tr><td>${r.date||''}</td><td class="text">${r.matchup||''}</td><td>${r.market}</td>
      <td>${r.side}</td><td>${r.line||''}</td><td>${r.book}</td><td>${fmtPrice(Number(r.price))}</td>
      <td>${edge}</td><td>${r.confidence}</td><td>${r.units_risked}u</td>
      <td>${r.status}</td><td>${pl}</td></tr>`;
  }
  if (rows.length > 300) html += `<tr><td colspan="12" class="muted text">… ${rows.length - 300} more rows (showing latest 300) …</td></tr>`;
  html += '</tbody></table></div>';
  $('#bets-content').innerHTML = html;
}
$('#bets-filter').addEventListener('click', (e) => {
  if (!e.target.classList.contains('chip')) return;
  $$('#bets-filter .chip').forEach(c => c.classList.remove('active'));
  e.target.classList.add('active');
  betsFilter = e.target.dataset.filter;
  renderBets();
});

async function loadProps() {
  if (paperData === null) paperData = await fetchJSON(`${DATA}/paper_log.json`);
  const p = paperData;
  function tbl(title, buckets) {
    let html = `<h3 style="margin: 16px 0 8px;">${title}</h3><div class="table-wrap"><table><thead><tr>
      <th>Bucket</th><th>Bets</th><th>W-L-P-V-Pen</th><th>Win%</th><th>Risked</th><th>P/L</th><th>ROI</th></tr></thead><tbody>`;
    for (const [name, b] of buckets) {
      html += `<tr><td class="text">${name}</td><td>${b.bets}</td>
        <td>${b.won}-${b.lost}-${b.push}-${b.void}-${b.pending}</td>
        <td>${fmt(b.win_pct,1)}%</td><td>${fmt(b.units_risked,1)}u</td>
        <td>${fmtPL(b.units_pl)}</td><td>${fmtPct(b.roi)}</td></tr>`;
    }
    html += '</tbody></table></div>';
    return html;
  }
  let html = '';
  html += tbl('Time windows', [['All-Time', p.all_time], ['Last 7 days', p.last_7]]);
  html += tbl('By market', Object.entries(p.by_market));
  html += `<h3 style="margin: 16px 0 8px;">Last paper bets</h3><div class="table-wrap"><table><thead><tr>
    <th>Date</th><th>Market</th><th>Player</th><th>Side</th><th>Line</th><th>Book</th><th>Price</th>
    <th>Edge</th><th>Status</th><th>Actual</th><th>P/L</th></tr></thead><tbody>`;
  for (const r of (p.rows || []).slice().reverse().slice(0, 200)) {
    const edge = r.edge_pred ? `${(Number(r.edge_pred)*100).toFixed(2)}%` : '—';
    const pl = (r.units_pl !== '' && r.units_pl !== undefined) ? fmtPL(Number(r.units_pl)) : '—';
    html += `<tr><td>${r.date||''}</td><td>${r.market}</td><td class="text">${r.player_name||''}</td>
      <td>${r.side}</td><td>${r.line||''}</td><td>${r.book}</td><td>${fmtPrice(Number(r.price))}</td>
      <td>${edge}</td><td>${r.status}</td><td>${r.actual_result||''}</td><td>${pl}</td></tr>`;
  }
  html += '</tbody></table></div>';
  $('#props-content').innerHTML = html;
}

(async () => {
  try {
    await loadManifest();
    await loadRecord();
    if (manifest.latest) await loadDate(manifest.latest, 'today-games');
    if (manifest.dates.length > 0) await loadDate(manifest.dates[0].date, 'hist-content');
  } catch (e) {
    $('#today-games').innerHTML = `<div class="muted">Boot error: ${e.message}</div>`;
  }
  // Lazy-load the heavier tabs on click
  $$('.tab').forEach(t => {
    t.addEventListener('click', async () => {
      if (t.dataset.tab === 'bets') await loadBets();
      if (t.dataset.tab === 'props') await loadProps();
    });
  });
})();
</script>
</body>
</html>
"""


def build(data_root: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ".nojekyll").write_text("")
    data_dir = out_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # 1. Manifest
    manifest = build_manifest(data_root)
    (data_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))

    # 2. Per-date snapshots
    n_dates = 0
    for d in manifest["dates"]:
        snap = build_per_date_snapshot(d["date"], data_root)
        if snap is None: continue
        (data_dir / f"{d['date']}.json").write_text(json.dumps(snap, indent=2, default=str))
        n_dates += 1

    # 3. Record
    record = build_record_snapshot(data_root)
    (data_dir / "record.json").write_text(json.dumps(record, indent=2, default=str))

    # 4. Bet log
    bet_log = _read_csv(data_root / "bet_log.csv")
    (data_dir / "bet_log.json").write_text(json.dumps(bet_log, indent=2, default=str))

    # 5. Paper log
    paper = build_paper_snapshot(data_root)
    (data_dir / "paper_log.json").write_text(json.dumps(paper, indent=2, default=str))

    # 6. Main page
    (out_dir / "index.html").write_text(INDEX_HTML)

    print(f"[site] wrote {out_dir}/")
    print(f"       index.html ({len(INDEX_HTML):,} bytes)")
    print(f"       data/manifest.json ({n_dates} date snapshots)")
    print(f"       data/record.json")
    print(f"       data/bet_log.json ({len(bet_log)} rows)")
    print(f"       data/paper_log.json ({len(paper.get('rows', []))} rows)")
    return out_dir


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build static site to docs/")
    ap.add_argument("--data-root", default="./mlb_data")
    ap.add_argument("--out", default="./docs")
    args = ap.parse_args(argv)
    data_root = Path(args.data_root).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    build(data_root, out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
