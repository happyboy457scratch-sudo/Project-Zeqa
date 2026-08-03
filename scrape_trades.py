import json
import os
import hashlib
import re
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

def parse_single_item_trade(raw_text):
    """
    Filters out multi-item trades (like "+1 more", "+2 more", or comma lists)
    and strictly captures: Price -> Item  OR  Item -> Price
    """
    # Reject multi-item trades immediately
    if "+1 more" in raw_text or "+2 more" in raw_text or "+3 more" in raw_text or "+4 more" in raw_text:
        return None

    # Check for arrow separator
    if "→" not in raw_text and "->" not in raw_text:
        return None

    # Split the trade into Left and Right sides of the arrow
    separator = "→" if "→" in raw_text else "->"
    parts = raw_text.split(separator)
    if len(parts) != 2:
        return None

    left_side = parts[0].strip()
    right_side = parts[1].strip()

    # Regex pattern to match coin prices (e.g., "10k", "500", "3.5k", "10.0k")
    price_pattern = re.compile(r'^\d+(\.\d+)?k?$', re.IGNORECASE)

    # Case 1:  10k → Single Item
    if price_pattern.match(left_side) and not price_pattern.match(right_side):
        return {
            "item": right_side,
            "price": left_side,
            "raw_trade": raw_text
        }

    # Case 2:  Single Item → 10k
    elif price_pattern.match(right_side) and not price_pattern.match(left_side):
        return {
            "item": left_side,
            "price": right_side,
            "raw_trade": raw_text
        }

    # Reject item-for-item or multi-item trades
    return None

def fetch_rendered_trades():
    trades = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        print("Navigating to page...")
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=45000)
        
        print("Waiting for trade list to render...")
        page.wait_for_timeout(5000)
        
        content = page.content()
        browser.close()

    soup = BeautifulSoup(content, "html.parser")

    # Extract all candidate lines or rows
    lines = []
    for row in soup.find_all(["tr", "li", "div"]):
        text = row.get_text(separator=" ", strip=True)
        if text and ("→" in text or "->" in text):
            lines.append(text)

    # Process and filter each line
    for line in lines:
        parsed = parse_single_item_trade(line)
        if parsed:
            trades.append(parsed)

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
        print(f"Success: Added {added_count} valid single-item trade(s). Total stored: {len(existing_trades)}")
    else:
        print("No new single-item trades found in this run.")

if __name__ == "__main__":
    main()
