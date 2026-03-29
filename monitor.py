#!/usr/bin/env python3
import json, os, urllib.request
from datetime import datetime
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
URL = "https://shop.royalchallengers.com/ticket"
STATE_FILE = "state.json"


def fetch_matches():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(10000)
        text = page.inner_text("body")
        browser.close()

    matches = set()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for i, line in enumerate(lines):
        if line == "VS" and i > 0 and i < len(lines) - 1:
            start = max(0, i - 3)
            end = min(len(lines), i + 5)
            matches.add(" | ".join(lines[start:end]))
    return matches


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            data = json.load(f)
            if data:  # only return if non-empty
                return set(data)
    return None


def save_state(matches):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(matches), f, indent=2)


def send_telegram(match_text):
    text = (
        f"🏏 New RCB Match Added!\n\n"
        f"{match_text}\n\n"
        f"🔴 Likely RCB vs CSK — grab tickets fast!\n"
        f"🎟 Book now:\nhttps://shop.royalchallengers.com/ticket"
    )
    data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req, timeout=10)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    known = load_state()

    if known is None:
        log("First run — saving baseline...")
        known = fetch_matches()
        save_state(known)
        log(f"Baseline: {len(known)} match(es)")
        for m in known:
            log(f"  • {m}")
        return

    log(f"Known: {len(known)} match(es). Checking...")
    current = fetch_matches()
    new = current - known

    if new:
        for match in new:
            log(f"NEW MATCH: {match}")
            send_telegram(match)
        save_state(current)
        log("State updated.")
    elif current != known:
        removed = known - current
        log(f"Match(es) removed from site (likely over): {len(removed)}. Updating state.")
        save_state(current)
    else:
        log(f"No new matches ({len(current)} total)")


if __name__ == "__main__":
    main()
