"""
notify.py — push the daily MLB cards to a destination.

Discord uses RICH EMBEDS (color-coded cards per bet, structured fields).
Other channels (Slack, Telegram, email) get the markdown body in a code block.
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


# ===========================================================================
# Visual config
# ===========================================================================

COLORS = {
    "Max":      0x10B981,   # emerald — rare 2u play
    "Strong":   0x22C55E,   # green   — 1.5u play
    "Medium":   0xF59E0B,   # amber   — 1u play
    "Standard": 0xF59E0B,   # amber   — 1u play
    "Low":      0x3B82F6,   # blue    — 0.5u lean
    "Lean":     0x3B82F6,   # blue    — 0.5u lean
    "neutral":  0x6B7280,   # slate gray
    "header":   0x4F46E5,   # indigo
}

EMOJI = {
    "Max":      "🎯",
    "Strong":   "🔥",
    "Medium":   "👀",
    "Standard": "👀",
    "Low":      "🪙",
    "Lean":     "🪙",
}

MARKET_LABEL = {
    "moneyline":  "Moneyline",
    "runline":    "Run Line",
    "total":      "Full-Game Total",
    "f5_total":   "First 5 Total",
    "nrfi":       "1st-Inning",
}

BOOK_LABEL = {
    "fanduel":    "FanDuel",
    "draftkings": "DraftKings",
    "betmgm":     "BetMGM",
    "caesars":    "Caesars",
    "pinnacle":   "Pinnacle",
    "espnbet":    "ESPN BET",
}


# ===========================================================================
# Loaders
# ===========================================================================

def _load_cards(date_iso: str, data_root: Path) -> tuple[str, list[dict] | None]:
    cards_md = data_root / date_iso / "cards.md"
    grades_json = data_root / date_iso / "grades.json"
    if not cards_md.exists():
        raise FileNotFoundError(f"No cards file at {cards_md}")
    body = cards_md.read_text()
    grades = json.loads(grades_json.read_text()) if grades_json.exists() else None
    return body, grades


def _summary_line(grades: list[dict] | None) -> tuple[str, dict]:
    if not grades:
        return "MLB betting cards ready.", {}
    n_games = len(grades)
    cards   = [c for g in grades for c in g.get("bet_cards", [])]
    n_bets  = len(cards)
    units   = sum(c["unit_size"] for c in cards)
    best_edge = max((c["edge"] for c in cards), default=0)
    return (
        f"MLB Sharp Cards — {n_games} games • {n_bets} plays • {units:.1f}u total exposure",
        {"n_games": n_games, "n_bets": n_bets, "units": units, "best_edge": best_edge},
    )


# ===========================================================================
# Slack
# ===========================================================================

def post_slack(body: str, summary: str, grades=None) -> bool:
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url: return False
    chunks = _chunks(body, 38000)
    ok = True
    for i, c in enumerate(chunks):
        prefix = f"*{summary}*\n" if i == 0 else ""
        r = requests.post(url, json={"text": prefix + "```\n" + c + "\n```"}, timeout=20)
        ok = ok and r.ok
    return ok


# ===========================================================================
# Discord — rich embeds
# ===========================================================================

def post_discord(body: str, summary: str, grades=None, target_date: str | None = None) -> bool:
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        return False

    if grades:
        try:
            return _post_discord_embeds(url, grades, summary, target_date)
        except Exception as e:
            print(f"[discord] embed path failed ({e}); falling back to text")

    chunks = _chunks(body, 1900)
    ok = True
    for i, c in enumerate(chunks):
        prefix = f"**{summary}**\n" if i == 0 else ""
        r = requests.post(url, json={"content": prefix + "```\n" + c + "\n```"}, timeout=20)
        ok = ok and (r.status_code in (200, 204))
    return ok


def _post_discord_embeds(url: str, grades: list[dict], summary: str,
                         target_date: str | None) -> bool:
    summary_text, stats = _summary_line(grades)
    cards = [(g, c) for g in grades for c in g.get("bet_cards", [])]
    cards.sort(key=lambda gc: (-gc[1]["unit_size"], -gc[1]["edge"]))

    header_embed = _build_header_embed(summary_text, stats, target_date, len(grades), len(cards))
    requests.post(url, json={"embeds": [header_embed]}, timeout=20).raise_for_status()

    if not cards:
        no_play = {
            "title": "No plays today",
            "description": "No bets cleared the edge + confidence filters.\n"
                           "Patience — sharp betting means most days you don't play.",
            "color": COLORS["neutral"],
        }
        requests.post(url, json={"embeds": [no_play]}, timeout=20).raise_for_status()
        return True

    embeds = [_build_bet_embed(g, c, idx + 1) for idx, (g, c) in enumerate(cards)]
    for batch_start in range(0, len(embeds), 10):
        batch = embeds[batch_start:batch_start + 10]
        r = requests.post(url, json={"embeds": batch}, timeout=20)
        r.raise_for_status()
    return True


def _build_header_embed(summary_text: str, stats: dict, target_date: str | None,
                        n_games: int, n_cards: int) -> dict:
    when = target_date or date.today().isoformat()
    desc_lines = [
        f"**Date:** {when}",
        f"**Games graded:** {n_games}",
        f"**Plays recommended:** {n_cards}",
        f"**Total exposure:** {stats.get('units', 0):.1f}u",
    ]
    if stats.get("best_edge"):
        desc_lines.append(f"**Best edge:** {stats['best_edge']*100:.2f}%")
    return {
        "title": "⚾ MLB Sharp Cards",
        "description": "\n".join(desc_lines),
        "color": COLORS["header"],
        "footer": {"text": "1u = 1% of bankroll • shopping FanDuel · DraftKings · BetMGM · Caesars"},
    }


def _build_bet_embed(game: dict, card: dict, idx: int) -> dict:
    risk    = card.get("risk", "Standard")
    color   = COLORS.get(risk, COLORS["neutral"])
    icon    = EMOJI.get(risk, "📊")

    market_label = MARKET_LABEL.get(card["market"], card["market"])
    book_label   = BOOK_LABEL.get(card["book"].lower(), card["book"])
    price_str    = _fmt_price(card["price_american"])
    line_str     = "" if card.get("line") is None else f" @ {card['line']}"

    fields = [
        {"name": "Game",   "value": game["matchup"],         "inline": False},
        {"name": "Market", "value": market_label + line_str, "inline": True},
        {"name": "Book",   "value": f"**{book_label}**",     "inline": True},
        {"name": "Price",  "value": f"**{price_str}**",      "inline": True},
        {"name": "Edge",   "value": f"{card['edge']*100:.2f}%",                "inline": True},
        {"name": "Conf",   "value": f"{card['confidence']}/10",                "inline": True},
        {"name": "Size",   "value": f"**{card['unit_size']}u**",               "inline": True},
        {"name": "Fair",   "value": f"{_fmt_price(card['fair_american'])} ({card['fair_prob']*100:.1f}%)",
         "inline": True},
    ]

    reasoning = card.get("reasoning") or []
    if reasoning:
        why = "\n".join(f"• {r}" for r in reasoning[:5])
        if len(why) > 1000:
            why = why[:1000] + "…"
        fields.append({"name": "Why", "value": why, "inline": False})

    triggers = card.get("pass_triggers") or []
    if triggers:
        warn = "\n".join(f"⚠ {t}" for t in triggers[:3])
        if len(warn) > 1000:
            warn = warn[:1000] + "…"
        fields.append({"name": "Pass if...", "value": warn, "inline": False})

    return {
        "title": f"{icon} Bet #{idx} — {card['bet_label']}",
        "color": color,
        "fields": fields,
        "footer": {"text": f"Risk: {risk} • {card['unit_size']}u • Edge {card['edge']*100:.2f}%"},
    }


def _fmt_price(american: int) -> str:
    return f"+{american}" if american > 0 else str(american)


# ===========================================================================
# Telegram
# ===========================================================================

def post_telegram(body: str, summary: str, grades=None) -> bool:
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


# ===========================================================================
# Email
# ===========================================================================

def post_email(body: str, summary: str, target_date: str, grades=None) -> bool:
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


# ===========================================================================
# Helpers
# ===========================================================================

def _chunks(text: str, size: int):
    out, current = [], ""
    for block in text.split("\n\n"):
        if len(current) + len(block) + 2 > size:
            if current: out.append(current); current = ""
        current += (("\n\n" if current else "") + block)
    if current: out.append(current)
    return out or [""]


# ===========================================================================
# CLI
# ===========================================================================

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--data-root", default="./mlb_data")
    args = ap.parse_args(argv)
    target = (date.fromisoformat(args.date) if args.date else date.today()).isoformat()
    data_root = Path(args.data_root).expanduser().resolve()

    body, grades = _load_cards(target, data_root)
    summary, _   = _summary_line(grades)

    sent_to = []
    for fn, name in (
        (lambda: post_slack(body, summary, grades), "slack"),
        (lambda: post_discord(body, summary, grades, target_date=target), "discord"),
        (lambda: post_telegram(body, summary, grades), "telegram"),
        (lambda: post_email(body, summary, target, grades), "email"),
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
