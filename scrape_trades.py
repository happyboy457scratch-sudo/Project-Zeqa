import json
import os
import hashlib
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
        # Launch headless browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("Navigating to page and waiting for client-side JavaScript...")
        page.goto(TARGET_URL, wait_until="networkidle", timeout=30000)
        
        # Give extra time for interactive tables/components to render
        page.wait_for_timeout(3000)
        
        content = page.content()
        browser.close()

    soup = BeautifulSoup(content, "html.parser")

    # Extract dynamic rows or cards from rendered DOM
    for row in soup.find_all(["tr", "div"], class_=lambda c: c and "trade" in c.lower()):
        text = row.get_text(separator=" ", strip=True)
        if text:
            trades.append({"details": text})

    # Fallback to all table rows if specific class isn't found
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
        print(f"Success: Added {added_count} new trade(s). Total trades: {len(existing_trades)}")
    else:
        print("No new trades found in this run.")

if __name__ == "__main__":
    main()
