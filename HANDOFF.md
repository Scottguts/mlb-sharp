# MLB Sharp Betting — Full Handoff / Onboarding Brief

> Paste-and-go context for a new Claude (or Claude Code) session. The **full source
> is in this repo** — clone it rather than pasting 10k lines. This doc is the map.

---

## 0. First thing a new chat should do

```bash
git clone https://github.com/Scottguts/mlb-sharp.git
cd mlb-sharp
```

Everything below describes what you just cloned. Source of truth = the code + the
GitHub Actions workflows. ~10,100 lines of Python across 14 modules.

---

## 1. What this system is

An **automated, market-anchored MLB betting pipeline**. Every day it:

1. **Scrapes** the slate (MLB Stats API), pitcher Statcast, weather (Open-Meteo),
   and multi-book odds (The Odds API).
2. **Grades** every game 0–100 across 7 weighted categories, converts grades to a
   **market-anchored win probability**, and computes an **edge** vs. the devigged
   sharp line (Pinnacle).
3. **Emits a betting card** only for plays that clear strict edge + confidence +
   price gates. Most days are **"NO PLAYS"** — that is by design, not a bug.
4. **Posts** cards to Discord, **tracks** every bet + CLV in CSV logs, settles via
   box scores, and **rebuilds a GitHub Pages site**.

**Core philosophy (do not violate):** the edge comes from small, evidence-backed
disagreements with the market plus line-shopping — NOT from predicting games from
scratch. Never loosen gates to manufacture bets. A quiet day is a correct day.

---

## 2. The money philosophy / key constants (`mlb_grader.py`)

```python
WEIGHTS = {pitching 32, offense 22, bullpen 10, weather_park 10,
           market 10, situational 8, injury_lineup 8}   # sum == 100

MIN_EDGE = {moneyline 1.8%, total 2.5%, runline 3.5%, f5_total 3.5%, nrfi 3.5%}
MIN_EDGE_PITCHER_PROP = 5.0%
MAX_REASONABLE_EDGE   = 6%     # bigger "edges" are treated as stale/calibration bugs → rejected
MIN_TEAM_WIN_PROB     = 0.45   # never bet a dog the model gives <45% to win outright
PRICE BAND            = -180 .. +180
MIN_CONFIDENCE        = 6/10
BOOK_CONFIRMATION_TOLERANCE_CENTS = 8   # best price must be confirmed by a DIFFERENT book
Per-slate caps: 5 regular cards / 6.0u · 3 prop cards / 3.0u · 1 card & ≤ cap units per game

ENABLED_MARKETS = moneyline✓ total✓ f5_total✓ nrfi✓ pitcher_strikeouts✓ pitcher_walks✓
                  runline✗ (disabled)
```

Validation is by **Brier / log-loss on ALL graded games + CLV**, never small-sample ROI.

---

## 3. File inventory (what each module does)

| File | Role |
|---|---|
| `mlb_data_scraper.py` | Fetches schedule, Statcast pitcher profiles, team batting splits, weather, and multi-book odds. **Owns the Odds-API key rotation + quota monitor** (see §5). |
| `mlb_grader.py` | The model. Category grades → win prob → edges → `BetCard`s. Gates, unit sizing, NRFI/F5/total/prop card builders. Writes `grades.json` + `cards.md`. |
| `paper_props.py` | Ungated "paper" prop experiment (flat 0.5u) logged to `prop_paper_log.csv`, settled from box scores. Separate from real fired props. |
| `bet_tracker.py` | Appends fired bets to `bet_log.csv`, settles pending bets, builds `record.md`, runs the paper-report. |
| `closing_snapshot.py` | Captures closing prices near first pitch → CLV. (Uses key rotation; one call/run.) |
| `pregame_alerts.py` | Near-game checks: lineup scratches, weather swings, line moved through our fair value. Fetches the odds board **once per run** (quota-safe). |
| `notify.py` | Builds the Discord embeds. Posts a red `@here` alert on a DATA OUTAGE. |
| `build_site.py` | Generates the static GitHub Pages site (`docs/`) + per-date JSON snapshots. |
| `build_dashboard.py`, `bankroll_sim.py`, `post_record.py`, `prop_tracking.py`, `historical_validate.py`, `model_calibration.py` | Supporting: HTML dashboard, bankroll sim, record channel post, prop data-quality tracker, backtests, calibration. |

**Data lives in** `mlb_data/<YYYY-MM-DD>/` (slate.json, games/, odds.json, grades.json,
cards.md, prop_tracking.md) plus top-level `mlb_data/bet_log.csv`,
`prop_paper_log.csv`, `odds_quota.json`.

---

## 4. How it runs (GitHub Actions)

| Workflow | Schedule (UTC) | Purpose |
|---|---|---|
| `daily-bets.yml` | staggered crons ~14:47–17:17 | THE pipeline: scrape → grade → notify → track → build site → commit. `precheck` job skips if that day's `cards.md` already committed. |
| `heartbeat.yml` | 17:30 & 18:30 | **Dead-man's-switch**: if no slate committed by early afternoon ET, pings Discord + auto-dispatches daily-bets. Survives a dropped daily-bets cron. |
| `pregame-alerts.yml` | every 30 min, game hours | Line-move / scratch / weather alerts. |
| `closing-snapshot.yml` | hourly, game hours | Closing-line CLV capture. |
| `refresh-record.yml` | — | Rebuilds the public record. |

> GitHub cron is **best-effort and drops runs under load** — that's why crons are
> staggered AND backed by the heartbeat. If a slate is ever missing, the fix is
> usually just: `gh workflow run daily-bets.yml --repo Scottguts/mlb-sharp`.

**Manual full fire (forces a real rebuild even if cards exist):**
```bash
git rm mlb_data/$(date +%F)/cards.md && git commit -m "force rerun" && git push
gh workflow run daily-bets.yml --repo Scottguts/mlb-sharp --ref main
```

**Run locally** (needs `ODDS_API_KEY` in env): `python mlb_data_scraper.py --date YYYY-MM-DD`
then `python mlb_grader.py --date YYYY-MM-DD`. The grader alone re-renders cards from
existing scraped data with no API calls.

---

## 5. Odds-API quota — the #1 operational issue (READ THIS)

The Odds API sells **500 requests/key/month**. Running out = the slate goes dark
(DATA OUTAGE). This has bitten the system repeatedly. Current defenses:

1. **Key rotation** (`_odds_keys` / `_get_odds_json` in `mlb_data_scraper.py`):
   configure `ODDS_API_KEY`, `ODDS_API_KEY_2`, … `_8` (GitHub secrets). Drains the
   primary, auto-fails-over to the next on 401/429 — even mid-slate.
2. **Burn control**: pregame/closing fetch the board **once per run** (not per bet)
   and route through rotation. Monthly burn is ≈ **900–950 requests** (props are the
   big fixed cost: ~15 games/day).
3. **Proactive warning** (`check_and_alert_odds_quota`): reads the quota headers The
   Odds API returns on every call (zero extra requests) and posts a Discord heads-up
   when your **last** key drops below ~150 requests — days before an outage. A
   non-last key draining is silent (the backup covers it).
4. **Outage alert**: `notify.py` posts a red `@here` embed if odds are unavailable,
   so it never looks like a disciplined no-play.

**If the slate is dark:** check `mlb_data/<date>/odds.json` → `"available": false` +
a 401 error = quota exhausted. Fix: add another key
`gh secret set ODDS_API_KEY_3 --repo Scottguts/mlb-sharp` (free key at
the-odds-api.com), or wait for the monthly reset (keys reset on signup anniversary).

---

## 6. Recent fixes already applied (so you don't redo them)

- Odds key rotation + the quota monitor + burn reduction (pregame once-per-run,
  closing single-call-via-rotation).
- Outage → red Discord alert; heartbeat watchdog workflow; daily-bets push now
  `pull --rebase` + retries.
- Determinism: site builds are now zero-diff (sorted globs, `sort_keys`,
  slate-relative prop-freshness gate) — the old ~100k-line docs churn is gone.
- Crash-safety: atomic CSV writes; corrupt-row-tolerant `_next_id`.
- Model correctness (apply going forward, history untouched):
  **A** two-book confirmation keyed on *distinct* book;
  **B** `expected_total` + total card anchor to the same Pinnacle paired line;
  **C** pitcher-prop bets the genuinely +EV side (not raw-Poisson lean);
  **E** game dates converted UTC→ET so night games aren't filed a day late.
- No-play rows on the site now show the book ML + total.

---

## 7. Known open items / good next tasks

- **D — CLV vig mismatch** (`closing_snapshot.py`): CLV compares devigged-close vs
  *vigged*-bet; fixing makes the published metric slightly more optimistic (needs a
  backfill decision). Not yet done.
- **F — runline settlement sign** can mis-grade home favorites (runline is disabled,
  so ~0 live impact).
- **G — doubleheader prop matching** by team-pair only (rare).
- Consider a permanent **3rd Odds API key** for headroom (props alone ≈ 450/mo).

---

## 8. Hard rules for anyone working on this

1. **Never loosen betting gates** (MIN_EDGE, confidence, price band, caps) to create
   more plays. Tightening/correctness is fine; manufacturing volume is not.
2. **Don't rewrite history**: model changes apply *going forward*. `bet_log.csv` is
   the record of what was actually bet — re-grading past dates must not alter it.
3. **Verify before deploy**: `python -m py_compile` the touched files; for site JS,
   `node --check` the inline script; discard cosmetic `docs/data/` churn.
4. **Secrets**: never commit API keys. Errors are redacted (`apiKey=***`) — keep it.
5. Commit on a branch / push only when asked; end commits with the Co-Authored-By
   trailer.

---

## 9. Repo / environment facts

- GitHub: `github.com/Scottguts/mlb-sharp` · default branch `main`
- Secrets needed: `ODDS_API_KEY` (+ `_2`.._8 optional), `DISCORD_WEBHOOK_URL`,
  (optional) `SLACK_WEBHOOK_URL`, `TELEGRAM_*`, `GH_DISPATCH_TOKEN`.
- Data sources: `statsapi.mlb.com/api/v1`, `api.the-odds-api.com/v4`
  (key), Open-Meteo (no key).
- Timezone: all display is ET; crons are UTC with EDT/EST variants.
