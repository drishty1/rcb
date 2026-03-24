#!/usr/bin/env python3
"""
Railway worker — runs forever, checks every 60 seconds.
"""
import json, os, urllib.request, time
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
URL = "https://shop.royalchallengers.com/ticket"
STATE_FILE = "/tmp/rcb_state.json"
INTERVAL = 60


def fetch_matches():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        stealth_sync(page)
        page.goto(URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(15000)
        text = page.inner_text("body")
        browser.close()

    log(f"Page text snippet: {text[:300]}")

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
            if data:
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
    log("RCB Monitor (Railway) started — checking every 60s")

    known = load_state()
    if known is None:
        log("Saving baseline...")
        known = fetch_matches()
        save_state(known)
        log(f"Baseline: {len(known)} match(es)")
        for m in known:
            log(f"  • {m}")

    while True:
        time.sleep(INTERVAL)
        try:
            current = fetch_matches()
            new = current - known
            if new:
                for match in new:
                    log(f"NEW MATCH: {match}")
                    send_telegram(match)
                known = current
                save_state(known)
            else:
                log(f"No new matches ({len(current)} total)")
        except Exception as e:
            log(f"Error: {e}")


if __name__ == "__main__":
    main()
