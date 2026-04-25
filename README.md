# MLB Sharp Betting — Automated Daily Cards

End-to-end pipeline that, every day at **12:00 PM ET**, scrapes the MLB slate,
grades every game using the Sharp Betting System, generates a betting card
for each play that clears the edge + confidence filters, and pushes the
cards to your phone (Slack / Discord / Telegram / email).

```
              ┌─ settle yesterday's pending bets via MLB Stats API
              ↓
┌─────────────────┐   ┌─────────────────┐   ┌────────────────┐   ┌──────────┐
│ scraper.py      │ → │ grader.py       │ → │ cards.md       │ → │ notify.py│
│ Stats API +     │   │ 0–100 grades +  │   │ Markdown bet   │   │ Slack /  │
│ Statcast +      │   │ NRFI / F5 / FG  │   │ card per play  │   │ Discord /│
│ Open-Meteo +    │   │ probabilities + │   │                │   │ Telegram/│
│ Odds API        │   │ unit sizing     │   │                │   │ email    │
└─────────────────┘   └─────────────────┘   └────────────────┘   └──────────┘
                              ↓                                       ↑
                     ┌────────────────┐    ┌──────────────────┐       │
                     │ GitHub Actions │ →  │ bet_tracker.py   │ ──────┘
                     │ daily cron     │    │ append → log,    │
                     │ @ 12 PM ET     │    │ rebuild record.md│
                     └────────────────┘    └──────────────────┘
                                                    │
                                  bet_log.csv ←─────┴─────→ record.md
                                  (append-only)              (overall + by category)
```

## What it bets

| Market | Notes |
|---|---|
| Full-game Moneyline | sides only, devigged vs Pinnacle for fair |
| Full-game Run Line  | derived from win prob × cover translation |
| Full-game Total     | normal-distribution model around expected runs |
| First-5 Total       | pitching-heavy, no bullpen contribution |
| NRFI / YRFI         | starter quality + park + top-of-order proxy |

Books shopped for the best price: **FanDuel, DraftKings, BetMGM, Caesars**.
Pinnacle is included only as the sharp anchor for devig math — you never see
it as a "best book to bet at".

## Files in this repo

```
.
├── README.md                  this file
├── MLB_Sharp_Betting_System.md  the overall playbook
├── README_scraper.md          deeper docs on the scraper
├── requirements.txt           Python deps
├── mlb_data_scraper.py        all data ingestion
├── mlb_grader.py              0-100 grade model + bet card generator
├── notify.py                  Slack/Discord/Telegram/email push
├── bet_tracker.py             append, settle, report (overall + by category + CLV)
├── closing_snapshot.py        captures closing-line value hourly during games
├── bankroll_sim.py            replays log under flat / ladder / Kelly sizing
├── .github/workflows/
│   ├── daily-bets.yml         12 PM ET cron + commits results
│   └── closing-snapshot.yml   hourly cron during MLB game windows
└── mlb_data/
    ├── bet_log.csv            ← every bet ever recommended (append-only)
    ├── record.md              ← overall + per-market record + CLV (rebuilt daily)
    ├── bankroll_sim.md        ← five sizing strategies replayed (rebuilt daily)
    └── <DATE>/
        ├── slate.json
        ├── odds.json
        ├── grades.json
        ├── cards.md           ← what gets pushed to your phone
        └── games/<gamePk>.json
```

## Record-keeping (overall + by category)

Every bet the grader recommends is written to `bet_log.csv` as a `pending` row
on the day it's made. The next morning's run settles those bets by pulling
the final box score from the MLB Stats API and computing units P/L for each
market type:

| Market | Settlement |
|---|---|
| moneyline | side wins outright |
| runline | side covers ±1.5 (margin > -line) |
| total | full-game runs over/under, integer line = push |
| f5_total | runs through 5 innings, integer line = push |
| nrfi / yrfi | scoreless 1st inning vs run scored in 1st |

The settled rows are then aggregated into `record.md` showing:

- **Overall record** — bets, W-L-P, win %, units risked, units P/L, ROI %, avg edge predicted
- **Per-category breakdown** — same columns, one row per market (moneyline, runline, total, f5_total, nrfi)
- **Time windows** — All time, last 30 days, last 7 days
- **By confidence tier** — 9-10 / 7-8 / 5-6
- **By book** — fanduel / draftkings / betmgm / caesars
- **Pending bets** — what's still open
- **Last 10 settled** — recent results

Run any piece manually:

```bash
python bet_tracker.py append --date 2026-04-25   # add today's recs
python bet_tracker.py settle                     # close out finished games
python bet_tracker.py report                     # rebuild record.md
python bet_tracker.py daily --date 2026-04-25    # all three in one shot
```

`bet_log.csv` is plain CSV — open it in Excel / Google Sheets to slice it
however you want, or load it into a notebook with `pandas.read_csv()`.

## Closing Line Value (CLV) tracking

A second workflow, `closing-snapshot.yml`, runs hourly during MLB game
windows. Each invocation:

1. Loads `bet_log.csv` and finds pending bets whose first pitch is in the
   next ~60 minutes and that don't yet have a closing snapshot.
2. Pulls the current odds, finds the same market/side/line at our four
   target books, and records the best available price as `closing_price`.
3. Devigs the same market on Pinnacle to compute `closing_fair_prob`.
4. Writes `clv_pct = closing_fair_prob − bet_implied_prob` and `beat_close`.

Then the daily report adds a CLV section:

```
## Closing Line Value (All Time)

| Bucket         | Bets w/ Close | Beat Close % | Avg CLV % |
|---             |--------------:|-------------:|----------:|
| OVERALL        |             9 |        66.7% |    +1.04% |
| moneyline      |             2 |        50.0% |    +0.74% |
| nrfi           |             3 |       100.0% |    +1.91% |
```

**Why it matters:** Win/loss is high-variance over hundreds of bets. CLV is
the only short-term proof your process is right. A sharp bettor averages
+2-3% CLV over time. If your CLV is consistently negative, the model is
miscalibrated — fix that first, regardless of recent W/L.

**API budget**: The Odds API free tier is 500 requests/month. The hourly
closing cron only fires when there are pending bets in the window, and
each invocation is one request — fits comfortably.

## Bankroll simulation

`bankroll_sim.py` replays every settled bet in `bet_log.csv` against five
position-sizing strategies and writes `bankroll_sim.md`:

| Strategy | What it does |
|---|---|
| flat_1u | Bet exactly 1% of current bankroll on every play |
| flat_2u | Bet exactly 2% — tests bankroll volatility tolerance |
| current_ladder | Sized exactly as the cards recommended (the system default) |
| half_kelly | 0.5 × Kelly fraction (capped at 5% of bankroll per bet) |
| quarter_kelly | 0.25 × Kelly — most conservative, lowest variance |

The report shows ending bankroll, growth %, ROI, and **max drawdown** per
strategy — overall and broken out per market. Use it to answer:

- Is the current ladder beating flat 1u? (If not, simpler is better.)
- Is half-Kelly leaving money on the table or causing too much variance?
- Which markets have produced positive long-run growth and which haven't?

The simulator uses **percent-of-current-bankroll sizing**, so it auto-
rebalances after wins and losses (compounding). This is closer to how
sharp bettors actually scale — fixed-dollar simulations underrepresent
the upside of a working edge.

Run manually:

```bash
python bankroll_sim.py                              # default $10,000 bankroll
python bankroll_sim.py --start-bankroll 5000        # custom
```

The daily workflow rebuilds it automatically after each settlement pass.

## One-time setup

### 1. Push these files to a fresh GitHub repo

```bash
git init mlb-sharp
cd mlb-sharp
# copy the files from this folder in
git add .
git commit -m "initial sharp betting system"
git branch -M main
git remote add origin git@github.com:<you>/mlb-sharp.git
git push -u origin main
```

### 2. Add repo secrets (Settings → Secrets and variables → Actions)

Required:

| Secret | Why |
|---|---|
| `ODDS_API_KEY` | Free key from https://the-odds-api.com — enables Pinnacle devig + multi-book shop |

Pick at least one delivery channel:

| Secret(s) | What it does |
|---|---|
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |
| `DISCORD_WEBHOOK_URL` | Discord channel webhook |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Telegram bot push |
| `EMAIL_SMTP_HOST` + `EMAIL_SMTP_PORT` + `EMAIL_SMTP_USER` + `EMAIL_SMTP_PASS` + `EMAIL_TO` | SMTP email |

### 3. Verify the cron

Open the **Actions** tab, find _Daily MLB Sharp Cards_, click **Run workflow**
to test manually. If the secrets are in place you should:

  * see a green build,
  * receive the cards in your channel,
  * see a new commit `daily cards YYYY-MM-DD` with the data files.

After that, the cron at 12 PM ET handles it automatically.

## Unit & confidence system (the core of the bankroll discipline)

Configured at the top of `mlb_grader.py`. Defaults:

```python
UNIT_LADDER = [
    (0.080, 9, 2.0, "Max"),       # 8%+ edge, 9+ confidence → 2.0u (rare)
    (0.060, 7, 1.5, "Strong"),    # 6%+ edge, 7+ confidence → 1.5u
    (0.040, 6, 1.0, "Standard"),  # 4%+ edge, 6+ confidence → 1.0u
    (0.030, 5, 0.5, "Lean"),      # 3%+ edge, 5+ confidence → 0.5u
]
MIN_EDGE       = {moneyline 3%, runline 3%, total 3%, f5_total 3.5%, nrfi 3.5%}
MIN_CONFIDENCE = 5
MAX_BETS_PER_SLATE = 8u total exposure
MAX_UNITS_PER_GAME = 2.0u
```

Confidence formula combines edge size with grade differential:

```
base = 5
+1 if grade gap ≥ 8  |  +2 if grade gap ≥ 15
+1 if edge ≥ 5%      |  +2 if edge ≥ 7%
−1 if edge < 3%
```

1 unit = 1% of bankroll. Recalibrate quarterly. Never increase after a loss.

## Time zones / when the cron actually fires

GitHub Actions cron is in UTC. We schedule **two** crons:
`0 16 * * *` (12 PM ET during EDT, March-Nov) and `0 17 * * *` (12 PM ET during
EST, Nov-March). Whichever one is "wrong" for the current DST state runs an
idempotent overwrite of the same files — no harm done.

If you want a different push time (e.g., 11 AM or 2 PM), edit
`.github/workflows/daily-bets.yml`.

## Local dry run before pushing

```bash
pip install -r requirements.txt
export ODDS_API_KEY=...                # required
export DISCORD_WEBHOOK_URL=...         # or SLACK / TELEGRAM / EMAIL
python mlb_data_scraper.py             # writes ./mlb_data/<today>/
python mlb_grader.py                   # writes ./mlb_data/<today>/cards.md
python notify.py                       # pushes the card to your channel
cat mlb_data/$(date +%F)/cards.md      # eyeball it
```

## What the published cards look like

```
### Bet #2 — F5 Over 4.5

| Field | Value |
|---|---|
| Game | Tampa Bay Rays @ Baltimore Orioles (2026-04-25T23:05:00Z) |
| Market | f5_total |
| Best Book | DRAFTKINGS -105 (line 4.5) |
| Fair Odds | -135 (57.5%) |
| Edge | 6.42% |
| Confidence | 7/10 |
| Risk | Strong |
| Unit Size | 1.5u |

**Reasoning**
- Expected F5 total 5.10 vs market 4.5
- away: velo down -7.8 mph — RED FLAG
- away: vs RHB xwOBA 0.345
- hitter park (pf_runs 102)

**Pass triggers**
- Either starter scratched
- Line moves through your fair value
- Weather forecast worsens
```

## Limits & honest caveats

- The Odds API free tier is ~500 requests / month. One scrape per day leaves
  plenty of headroom even with the alternate-market calls.
- F5 totals and 1st-inning totals **are not posted by every book for every
  game**. When a market is missing the grader silently skips that bet type
  for that game.
- The NRFI model is a deliberately simple bayesian update around the league
  base rate. Improving it is the highest-ROI place to extend the system —
  add starter K%/BB% rates, top-3-batter wOBA in the 1st, and umpire K%
  from UmpScorecards.
- Grades are only as good as the data. If lineups aren't confirmed by the
  time the cron runs at noon, the offense + lineup categories grade as
  neutral. For the sharpest cards, run the grader again ~30 min before
  first pitch with a manual `workflow_dispatch` (the workflow already
  supports it).
