# Getting Your Code on GitHub — The Simplest Way

No code, no terminal, no scary stuff. Just clicking buttons in a browser.

---

## First, what is GitHub?

GitHub is a free website where you store files online. Think of it like Google Drive, but it can also **run programs for you on a schedule**. That second part is what we need — we want GitHub to run our betting bot every day at noon.

Your files will live in something called a "repository" (or **"repo"** for short). A repo is just a fancy word for "folder for one project."

---

## Part 1: Make a free GitHub account (5 minutes)

### Step 1
Open your web browser and go to: **https://github.com**

### Step 2
Click the big **Sign up** button in the top-right corner.

### Step 3
Type in:
- Your email address
- A password (pick a good one)
- A username (this is what people see — like `scott123` or `sharpbets-scott`)

### Step 4
GitHub will ask "Are you a human?" and give you a puzzle. Solve it.

### Step 5
GitHub emails you a code. Open your email, copy the code, paste it on the GitHub page.

### Step 6
GitHub asks a few questions like "How many people will use this?" Just pick "**Just me**" and "**Free**." You don't need to pay for anything.

You're now on the GitHub homepage. You'll see your username in the top-right corner. **You're done with Part 1.**

---

## Part 2: Make your project folder on GitHub (2 minutes)

### Step 1
On the GitHub homepage, look in the **top-left corner** for a green button that says **New** (or look for a **+** symbol in the top-right and click "New repository").

### Step 2
You'll see a form. Fill it in like this:

- **Repository name:** type `mlb-sharp` (no spaces, all lowercase)
- **Description:** leave blank
- Click the bubble next to **Private** (this means only you can see it)
- **DO NOT** check the box "Add a README file"
- **DO NOT** check anything about gitignore or license

### Step 3
Click the green **Create repository** button at the bottom.

### Step 4
You're now on a page with a bunch of weird-looking commands. **Ignore all of those.** Look for a small link near the top that says **uploading an existing file**. Click it.

If you can't find that link, look at the URL in your browser bar. It should look like `https://github.com/YOUR-USERNAME/mlb-sharp`. Add `/upload/main` to the end so it becomes `https://github.com/YOUR-USERNAME/mlb-sharp/upload/main`. That takes you to the upload page.

**You should now see a big box that says "Drag files here to add them to your repository."**

---

## Part 3: Upload most of your files (3 minutes)

You have a folder on your computer with all the files I made. Open that folder in a new window so you can see both the folder and your browser at the same time.

### Step 1
**Click and drag** these files from your folder into the big upload box on GitHub:

- `README.md`
- `SETUP_GUIDE.md`
- `MLB_Sharp_Betting_System.md`
- `README_scraper.md`
- `requirements.txt`
- `mlb_data_scraper.py`
- `mlb_grader.py`
- `notify.py`
- `bet_tracker.py`
- `closing_snapshot.py`
- `bankroll_sim.py`
- `GITHUB_GUIDE_SIMPLE.md` (this file)

You can grab them all at once and drag them together.

### Step 2
Wait for them all to upload. You'll see a little progress bar and then green checkmarks next to each file name.

### Step 3
Scroll down to the bottom of the page. You'll see a box labeled **Commit changes**. In the first text field, type:

```
upload first batch of files
```

Leave everything else as-is.

### Step 4
Click the green **Commit changes** button.

You'll be taken back to your repo page and you'll see all your files listed. **Great — most of the files are uploaded.**

---

## Part 4: Add the special "robot instructions" files (5 minutes)

Your bot needs two special files in a special folder. The folder name starts with a dot (`.github`), which is a magic name GitHub uses for "robot instructions."

We'll create them by typing into GitHub directly — easier than trying to upload a hidden folder.

### Step 1: Open the file you have on your computer

On your computer, open the file at `.github/workflows/daily-bets.yml` in any text editor (TextEdit on Mac, Notepad on Windows). Select **all** the text inside (Cmd+A on Mac, Ctrl+A on Windows). Copy it (Cmd+C / Ctrl+C).

### Step 2: Create the file on GitHub

Go back to your repo page on GitHub (`https://github.com/YOUR-USERNAME/mlb-sharp`).

Look for a button that says **Add file** near the top-right of the file list. Click it → choose **Create new file**.

### Step 3: Type the special file name

In the file name field at the top of the page, type **exactly** this:

```
.github/workflows/daily-bets.yml
```

The slashes are important — GitHub will see the slashes and automatically create the folders for you. As you type, you should see the path appear like a breadcrumb above the file editor.

### Step 4: Paste the file's contents

Click in the big white text area below. Paste what you copied (Cmd+V / Ctrl+V).

### Step 5: Save it

Scroll down to **Commit changes**. In the message box, type:

```
add daily workflow
```

Click the green **Commit changes** button.

### Step 6: Do it again for the second workflow file

Go back to your repo page. Click **Add file** → **Create new file** again.

Type this file name:

```
.github/workflows/closing-snapshot.yml
```

Open `.github/workflows/closing-snapshot.yml` from your computer in a text editor, copy all of it, paste into the GitHub editor, click **Commit changes** at the bottom.

---

## Part 5: Tell GitHub the bot is allowed to save its work (1 minute)

The bot will create new files every day (the bet cards). We need to give it permission to do that.

### Step 1
At the top of your repo page, click **Settings** (it's a gear icon, far right of the row that has "Code", "Issues", "Pull requests", etc.)

### Step 2
On the left side, scroll down and click **Actions** → then click **General**.

### Step 3
Scroll down to a section titled **Workflow permissions**. You'll see two bubbles:

- "Read repository contents and packages permissions"
- "Read and write permissions" ← **click this one**

### Step 4
Click the green **Save** button just below those bubbles.

---

## Part 6: Add your secret keys (5 minutes)

The bot needs your secret API key (the Odds API one) and your phone notification secrets. We give them to GitHub in a special hidden way so nobody else can see them.

### Step 1
Still in **Settings**. On the left side, find **Secrets and variables** → click it → click **Actions** underneath it.

### Step 2: Add the Odds API key

Click the green **New repository secret** button (top-right).

- **Name:** type `ODDS_API_KEY` (exactly like that — caps matter)
- **Secret:** paste your new Odds API key (you said you regenerated it — use the new one)

Click **Add secret**.

### Step 3: Add your Telegram secrets (if using Telegram)

Click **New repository secret** again.

- **Name:** `TELEGRAM_BOT_TOKEN`
- **Secret:** the token BotFather gave you (the long thing with a colon in it)

Click **Add secret**.

Click **New repository secret** one more time.

- **Name:** `TELEGRAM_CHAT_ID`
- **Secret:** your numeric chat ID from `@userinfobot`

Click **Add secret**.

### Step 4: Or add your Discord secret (if using Discord instead)

Click **New repository secret**.

- **Name:** `DISCORD_WEBHOOK_URL`
- **Secret:** the webhook URL you copied from Discord

Click **Add secret**.

---

## Part 7: Test it! (5 minutes)

### Step 1
At the top of your repo page, click the **Actions** tab.

### Step 2
The first time you click Actions, GitHub may show a yellow banner asking if you want to enable workflows. Click **I understand my workflows, go ahead and enable them**.

### Step 3
On the left side, you'll see two workflows listed:
- **Daily MLB Sharp Cards**
- **Closing Line Snapshot**

Click **Daily MLB Sharp Cards**.

### Step 4
On the right side, you'll see a small box that says "**This workflow has a workflow_dispatch event trigger.**" Below that is a **Run workflow** dropdown button.

Click **Run workflow** → in the small popup, click the green **Run workflow** button.

### Step 5
Wait about 10 seconds, then refresh the page. You'll see a new entry at the top with a yellow circle (it's running).

### Step 6
Click on the running workflow to watch it work. You'll see steps tick off:

```
✓ Checkout repo
✓ Set up Python
✓ Install dependencies
... and so on
```

The whole thing takes about 3-5 minutes.

### Step 7
**When the "Send cards to configured destinations" step finishes, your phone should buzz** with a notification from your bot. That's the bet cards!

If today is a no-game day or no bets cleared the filters, you'll get a "no plays" message instead. That's normal.

### Step 8
Click back to your repo's main page (click the **Code** tab). You should see:

- A new folder called `mlb_data/` 
- Inside that, a folder named with today's date
- Inside that date folder, files like `cards.md` (your bet card)
- A new file `mlb_data/bet_log.csv` (your betting history)

You can click any of these to read them right in GitHub.

---

## You're done!

From now on, the bot does everything by itself. Every day at noon Eastern Time:

1. It pulls today's MLB games and odds
2. It grades every game
3. It picks the bets with real edges
4. It sends them to your phone
5. It saves everything to your repo so you have a record

You don't have to do anything. Just check your phone at noon.

---

## If something goes wrong

**The workflow runs and shows a red X (failed):**
1. Click the failed run
2. Click the failed step (it has a red X next to it)
3. Read the error message at the bottom

Common reasons:
- **"Workflow has been disabled"** → go to Actions tab and click "Enable workflow"
- **Can't push back to repo** → you skipped Part 5. Go enable read/write permissions.
- **Auth failed on Odds API** → secret name is misspelled. Must be exactly `ODDS_API_KEY`.
- **No notification on phone** → secret name for Telegram/Discord is misspelled, OR phone notifications are turned off in your phone settings.

**Phone never buzzes:**
1. Check the "Send cards" step in the Actions log — it tells you which channels it sent to
2. If it says "no destination configured" → your secret name doesn't match. Spell-check it.
3. If it says "sent to telegram" but your phone is silent → check your phone's Notifications settings for Telegram (must be Allowed)

**You messed up uploading a file:**
You can always click any file in your repo and click the trash icon to delete it, then re-upload. GitHub keeps a history so nothing is ever truly lost.

If you get stuck on any specific step, take a screenshot of what you see and I'll help debug.
