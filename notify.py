"""
notify.py — push the daily MLB cards.md to a destination.

Configured via environment variables. Pick any combination:

  SLACK_WEBHOOK_URL        Incoming Webhook from a Slack workspace
  DISCORD_WEBHOOK_URL      Webhook URL from a Discord channel
  TELEGRAM_BOT_TOKEN       Bot token from BotFather
  TELEGRAM_CHAT_ID         Your chat / channel ID

  EMAIL_SMTP_HOST          e.g. smtp.gmail.com
  EMAIL_SMTP_PORT          587
  EMAIL_SMTP_USER          sender address
  EMAIL_SMTP_PASS          app password
  EMAIL_TO                 comma-separated recipient list

Usage:
    python notify.py                                  # today's cards
    python notify.py --date 2026-04-25
    python notify.py --data-root ./mlb_data
"""

from __future__ import annotations

import argparse
import json
import os
import smtplib
import sys
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests


def _load_cards(date_iso: str, data_root: Path) -> tuple[str, dict | None]:
    cards_md = data_root / date_iso / "cards.md"
    grades_json = data_root / date_iso / "grades.json"
    if not cards_md.exists():
        raise FileNotFoundError(f"No cards file at {cards_md}")
    body = cards_md.read_text()
    grades = json.loads(grades_json.read_text()) if grades_json.exists() else None
    return body, grades


def _summary_line(grades: list[dict] | None) -> str:
    if not grades: return "MLB betting cards ready."
    n_games = len(grades)
    n_bets = sum(len(g.get("bet_cards", [])) for g in grades)
    units = sum(c["unit_size"] for g in grades for c in g.get("bet_cards", []))
    return f"MLB Sharp Cards — {n_games} games, {n_bets} plays, {units:.1f}u total exposure."


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------

def post_slack(body: str, summary: str) -> bool:
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url: return False
    # Slack webhook caps message text at ~40k; chunk if needed
    chunks = _chunks(body, 38000)
    ok = True
    for i, c in enumerate(chunks):
        prefix = f"*{summary}*\n" if i == 0 else ""
        r = requests.post(url, json={"text": prefix + "```\n" + c + "\n```"}, timeout=20)
        ok = ok and r.ok
    return ok


# ---------------------------------------------------------------------------
# Discord
# ---------------------------------------------------------------------------

def post_discord(body: str, summary: str) -> bool:
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url: return False
    chunks = _chunks(body, 1900)   # Discord caps at 2000 chars
    ok = True
    for i, c in enumerate(chunks):
        prefix = f"**{summary}**\n" if i == 0 else ""
        r = requests.post(url, json={"content": prefix + "```\n" + c + "\n```"}, timeout=20)
        ok = ok and (r.status_code in (200, 204))
    return ok


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def post_telegram(body: str, summary: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat): return False
    chunks = _chunks(body, 3800)
    ok = True
    for i, c in enumerate(chunks):
        prefix = f"*{summary}*\n" if i == 0 else ""
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": prefix + "```\n" + c + "\n```",
                  "parse_mode": "Markdown"},
            timeout=20)
        ok = ok and r.ok
    return ok


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def post_email(body: str, summary: str, target_date: str) -> bool:
    host = os.environ.get("EMAIL_SMTP_HOST")
    port = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
    user = os.environ.get("EMAIL_SMTP_USER")
    pwd  = os.environ.get("EMAIL_SMTP_PASS")
    to   = os.environ.get("EMAIL_TO")
    if not (host and user and pwd and to): return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"MLB Sharp Cards — {target_date}"
    msg["From"] = user
    msg["To"]   = to
    msg.attach(MIMEText(summary + "\n\n" + body, "plain"))

    with smtplib.SMTP(host, port) as s:
        s.starttls()
        s.login(user, pwd)
        s.sendmail(user, [a.strip() for a in to.split(",")], msg.as_string())
    return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chunks(text: str, size: int):
    # split on blank lines so we don't break inside a card if possible
    out, current = [], ""
    for block in text.split("\n\n"):
        if len(current) + len(block) + 2 > size:
            if current: out.append(current); current = ""
        current += (("\n\n" if current else "") + block)
    if current: out.append(current)
    return out or [""]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--data-root", default="./mlb_data")
    args = ap.parse_args(argv)
    target = (date.fromisoformat(args.date) if args.date else date.today()).isoformat()
    data_root = Path(args.data_root).expanduser().resolve()

    body, grades = _load_cards(target, data_root)
    summary = _summary_line(grades)

    sent_to = []
    for fn, name in (
        (lambda: post_slack(body, summary), "slack"),
        (lambda: post_discord(body, summary), "discord"),
        (lambda: post_telegram(body, summary), "telegram"),
        (lambda: post_email(body, summary, target), "email"),
    ):
        try:
            if fn(): sent_to.append(name)
        except Exception as e:
            print(f"[warn] {name} send failed: {e}")

    if not sent_to:
        print("[error] no destination configured. Set at least one of "
              "SLACK_WEBHOOK_URL / DISCORD_WEBHOOK_URL / TELEGRAM_BOT_TOKEN+TELEGRAM_CHAT_ID / EMAIL_*")
        return 1
    print(f"[done] sent cards to: {', '.join(sent_to)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
