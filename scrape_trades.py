import json
import os
import hashlib
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

DATA_FILE = "data/trades.json"
TARGET_URL = "https://inpvp.net/mineville/trades?mode=pvp"

def load_existing_trades():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def get_trade_signature(trade):
    trade_string = json.dumps(trade, sort_keys=True)
    return hashlib.md5(trade_string.encode("utf-8")).hexdigest()

def fetch_rendered_trades():
    trades = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Add a custom user agent so the headless browser isn't flagged
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        print("Navigating to page...")
        # Load until initial DOM content is ready (prevents networkidle timeout)
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=45000)
        
        print("Waiting for trade data to render...")
        # Give JS time to fetch and render the trade list
        page.wait_for_timeout(5000)
        
        content = page.content()
        browser.close()

    soup = BeautifulSoup(content, "html.parser")

    # Extract dynamic rows or cards from rendered DOM
    for row in soup.find_all(["tr", "div"], class_=lambda c: c and "trade" in c.lower()):
        text = row.get_text(separator=" ", strip=True)
        if text:
            trades.append({"details": text})

    # Fallback to standard table rows
    if not trades:
        for row in soup.find_all("tr"):
            cols = [col.get_text(strip=True) for col in row.find_all(["td", "th"])]
            if cols:
                trades.append({"columns": cols})

    return trades

def main():
    existing_trades = load_existing_trades()
    seen_ids = {get_trade_signature(t) for t in existing_trades}

    scraped_trades = fetch_rendered_trades()
    added_count = 0

    for trade in scraped_trades:
        sig = get_trade_signature(trade)
        if sig not in seen_ids:
            seen_ids.add(sig)
            existing_trades.append(trade)
            added_count += 1

    if added_count > 0:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_trades, f, indent=2)
        print(f"Success: Added {added_count} new trade(s). Total trades stored: {len(existing_trades)}")
    else:
        print("No new trades found in this run.")

if __name__ == "__main__":
    main()
