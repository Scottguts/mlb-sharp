# MLB Sharp Betting — Step-by-Step Setup Guide

From zero to "betting cards on my phone every day at 12 PM ET" in about 30 minutes.

---

## Part 1 — Get the code into GitHub

### Step 1.1: Create a free GitHub account

If you already have one, skip ahead.

1. Go to https://github.com/signup
2. Pick a username, verify your email
3. Free plan is fine — Actions runs free on public repos and gives you 2,000 free minutes/month on private repos (the daily cron uses ~3-5 min/day = ~120 min/month)

### Step 1.2: Install Git on your computer

**Mac:** Open Terminal, run `git --version`. If it prompts to install Xcode tools, click Install.

**Windows:** Download https://git-scm.com/download/win and run the installer. Accept all defaults.

### Step 1.3: Create the repo on GitHub

1. Click the **+** in the top-right of github.com → **New repository**
2. Repository name: `mlb-sharp` (or whatever you want)
3. Set it to **Private** (so your bet log isn't public)
4. **Do NOT** check "Add a README" — your local copy already has files
5. Click **Create repository**
6. Leave the page open — you'll need the URL it shows you

### Step 1.4: Put all the files in one folder on your computer

Create a folder called `mlb-sharp` somewhere convenient (Desktop is fine). Copy these files into it:

```
mlb-sharp/
├── README.md
├── SETUP_GUIDE.md
├── MLB_Sharp_Betting_System.md
├── README_scraper.md
├── requirements.txt
├── mlb_data_scraper.py
├── mlb_grader.py
├── notify.py
├── bet_tracker.py
├── closing_snapshot.py
├── bankroll_sim.py
└── .github/
    └── workflows/
        ├── daily-bets.yml
        └── closing-snapshot.yml
```

**Important:** the `.github/workflows/` folder is hidden by default on Mac. In Finder: Cmd+Shift+. to show hidden files. Make sure those two `.yml` files are inside `.github/workflows/`, not at the top level.

### Step 1.5: Push the code to GitHub

Open Terminal (Mac) or Git Bash (Windows). Navigate into the folder:

```bash
cd ~/Desktop/mlb-sharp           # adjust if you put it somewhere else
```

Run these commands one at a time:

```bash
git init
git add .
git commit -m "initial sharp betting system"
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/mlb-sharp.git
git push -u origin main
```

Replace `<YOUR-USERNAME>` with your actual GitHub username.

If GitHub asks for a password, use a **Personal Access Token** instead (Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token → check `repo` scope → copy it and use as the password).

When this finishes, refresh your repo page on GitHub — you should see all the files.

### Step 1.6: Enable Actions write permission

The daily cron needs to commit results back to your repo.

1. In your repo: **Settings** (top tab)
2. **Actions** (left sidebar) → **General**
3. Scroll to **Workflow permissions**
4. Select **Read and write permissions**
5. Click **Save**

---

## Part 2 — Set up push notifications to your phone

You have three good options. I recommend **Telegram** for the cleanest "straight to phone" experience — it's free, instant, and you can mute/unmute easily. Discord is a fine fallback if you already use it.

### Option A — Telegram (recommended)

Telegram pushes hit your phone like SMS — no algorithm, no scrolling.

#### Step 2A.1: Install Telegram on your phone

App Store / Play Store → "Telegram" → install → sign up with your phone number.

#### Step 2A.2: Create a bot via BotFather

On your phone in the Telegram app:

1. Search for `@BotFather` (it's a verified blue checkmark account)
2. Tap **Start**
3. Send: `/newbot`
4. BotFather asks for a name. Reply with: `MLB Sharp Cards` (anything works)
5. BotFather asks for a username. Reply with something ending in `bot`, e.g.: `mlb_sharp_scott_bot`
6. BotFather replies with a message containing a token like `7234567890:AAH8c...XzYz1A`. **This is your `TELEGRAM_BOT_TOKEN`.** Copy it somewhere temporarily.

#### Step 2A.3: Start a chat with your new bot

1. Tap the link in BotFather's message (looks like `t.me/mlb_sharp_scott_bot`)
2. Tap **Start** in the new chat. This is required — bots can't message you until you message them first.

#### Step 2A.4: Get your Chat ID

You need the numeric ID of your chat with the bot.

Easiest method:
1. In Telegram, search for `@userinfobot`
2. Tap **Start**
3. It replies with your user info including your **Id** (a number like `123456789`). **This is your `TELEGRAM_CHAT_ID`.** Copy it.

#### Step 2A.5: Test that the bot can message you

In a browser, paste this URL (replace the parts in caps):

```
https://api.telegram.org/botYOUR_TOKEN/sendMessage?chat_id=YOUR_CHAT_ID&text=test
```

If it works, your phone gets a "test" notification from your bot. If you see an error, double-check the token and chat ID.

#### Step 2A.6: Make sure phone notifications are enabled

In the Telegram app:
1. Open the chat with your bot
2. Tap the bot's name at top
3. **Notifications** → set to **Default** (or **Custom** with sound on)
4. Phone settings → Notifications → Telegram → make sure they're **Allowed** with **Banners** and **Sounds**

You're done with Telegram.

### Option B — Discord (simpler if you already use Discord)

#### Step 2B.1: Install Discord on your phone

App Store / Play Store → install → sign in.

#### Step 2B.2: Create a server (or use an existing one)

In Discord on your phone or computer:
1. Tap **+** in the server list (left side)
2. **Create My Own** → **For me and my friends**
3. Name it anything ("Sharp Bets")

#### Step 2B.3: Create a webhook for a channel

This is easiest on the desktop app or web:
1. Pick a channel (e.g., `#general`) → click the **gear icon** next to its name → **Integrations**
2. **Webhooks** → **New Webhook**
3. Name it ("MLB Cards Bot") → click **Copy Webhook URL**. **This is your `DISCORD_WEBHOOK_URL`.**

#### Step 2B.4: Make sure phone notifications are enabled

In Discord on your phone:
1. Long-press the server name → **Notification Settings** → **All Messages**
2. Phone settings → Notifications → Discord → **Allowed**

### Option C — Email

Works but less immediate than Telegram/Discord. Use Gmail with an "App Password" (Settings → Security → 2-Step Verification → App passwords). You'll need:

- `EMAIL_SMTP_HOST` = `smtp.gmail.com`
- `EMAIL_SMTP_PORT` = `587`
- `EMAIL_SMTP_USER` = your Gmail address
- `EMAIL_SMTP_PASS` = the 16-char app password (NOT your regular password)
- `EMAIL_TO` = where to send to (can be the same Gmail)

---

## Part 3 — Add the secrets to GitHub

Now wire up the keys in your repo.

### Step 3.1: Open the secrets page

1. In your `mlb-sharp` repo: **Settings** (top tab)
2. **Secrets and variables** (left sidebar) → **Actions**

### Step 3.2: Add `ODDS_API_KEY`

1. Click **New repository secret**
2. **Name:** `ODDS_API_KEY`
3. **Secret:** paste your Odds API key (the new one you regenerated)
4. **Add secret**

### Step 3.3: Add your push notification secrets

**For Telegram:** add two secrets:
- Name: `TELEGRAM_BOT_TOKEN` — Value: the token from BotFather
- Name: `TELEGRAM_CHAT_ID` — Value: your numeric chat ID

**For Discord:** add one secret:
- Name: `DISCORD_WEBHOOK_URL` — Value: the webhook URL you copied

**For email:** add the five email secrets listed in Option C.

You can set up multiple channels — the notifier will push to every channel you configured.

### Step 3.4: Verify the secrets list

Your secrets list should now show (for Telegram):

```
ODDS_API_KEY            • Updated now
TELEGRAM_BOT_TOKEN      • Updated now
TELEGRAM_CHAT_ID        • Updated now
```

You can never view secret values again after adding them — only update or delete. That's normal.

---

## Part 4 — First test run

### Step 4.1: Manually trigger the daily workflow

1. In your repo: **Actions** (top tab)
2. Click **Daily MLB Sharp Cards** in the left sidebar
3. Click **Run workflow** dropdown (right side) → **Run workflow** (green button)
4. Wait ~30 seconds, then refresh — you'll see a new run appear with a yellow circle (running)

### Step 4.2: Watch the run

Click on the running workflow → click the `build-and-send` job. You'll see each step expand as it runs:

```
✓ Checkout repo
✓ Set up Python
✓ Install dependencies
✓ Determine target date
✓ Settle yesterday's pending bets
✓ Scrape MLB data           ← longest step (~2 min)
✓ Grade games and build cards
✓ Append today's cards to bet log
✓ Rebuild record.md
✓ Rebuild bankroll simulation
✓ Send cards to configured destinations  ← phone push happens here
✓ Commit daily artifacts back to repo
✓ Upload cards.md as workflow artifact
```

Total runtime ~3-5 minutes.

### Step 4.3: Check your phone

When the **Send cards** step finishes, your phone should buzz with the day's cards. They'll look like:

```
*MLB Sharp Cards — 12 games, 4 plays, 4.5u total exposure.*
### Bet #1 — Baltimore Orioles ML
| Field | Value |
| Game | Tampa Bay Rays @ Baltimore Orioles |
| Best Book | DRAFTKINGS +110 |
| Edge | 4.40% |
| Confidence | 7/10 |
| Unit Size | 1.0u |
...
```

If today is a no-game day or no plays clear the edge filter, you'll get "No bets today" instead. That's normal — sharp betting means most days you don't play.

### Step 4.4: Confirm the commit

Refresh your repo page. You should see:
- A new commit `daily cards 2026-04-XX` from `mlb-sharp-bot`
- A new folder `mlb_data/2026-04-XX/` with `cards.md`, `grades.json`, `slate.json`, `odds.json`
- A new file `mlb_data/bet_log.csv`
- A new file `mlb_data/record.md`
- A new file `mlb_data/bankroll_sim.md`

Click any of these to view them right in GitHub.

---

## Part 5 — Confirm the cron is scheduled

Going forward, the cron runs automatically at 12:00 PM ET every day. To verify:

1. **Actions** tab → **Daily MLB Sharp Cards** → look at scheduled runs
2. The hourly closing-line snapshot runs automatically too — you'll see `Closing Line Snapshot` runs throughout each evening

You don't need to do anything else. Tomorrow at noon ET your phone will buzz again.

---

## Common issues

**Workflow fails at "Commit daily artifacts back":** You forgot Step 1.6. Go enable read/write permissions for Actions.

**Workflow runs but nothing appears on phone:** Send step probably didn't find a configured channel. Check the Actions log of the "Send cards" step — it'll print which channels it sent to. If it says "no destination configured", verify your secrets are spelled exactly right (case matters).

**`Workspace still starting` or scraper times out:** Re-run the workflow. GitHub runners are occasionally slow.

**Odds API returns "auth failed":** Your key is wrong or got rate-limited. Regenerate at the-odds-api.com and update the secret.

**No bets generated:** Normal on quiet slates. Check `grades.json` to confirm games were graded — if they were and no card emitted, the edge filter just didn't find a play. Let it run a few more days.

**Bot stopped working:** Telegram bots stop messaging you if you block/delete the chat. Re-open the chat and tap **Start** again.

---

## Once it's running

- Open `mlb_data/record.md` in your repo to check overall + per-category record
- Open `mlb_data/bankroll_sim.md` to see how each sizing strategy is doing
- Open `mlb_data/bet_log.csv` in Excel/Sheets for arbitrary analysis
- The Telegram/Discord push gives you the "what to bet today" — everything else lives in the repo

That's the whole loop.
