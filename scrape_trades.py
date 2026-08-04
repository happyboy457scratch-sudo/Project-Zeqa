import json
import os
import hashlib
import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DATA_FILE = "data/trades.json"
TARGET_URL = "https://inpvp.net/mineville/trades?mode=pvp"

MONTHS_REGEX = r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b'

def load_existing_trades():
    """Load existing trades from data/trades.json."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def get_trade_signature(trade):
    """Generate MD5 hash signature for trade deduplication."""
    trade_string = json.dumps(trade, sort_keys=True)
    return hashlib.md5(trade_string.encode("utf-8")).hexdigest()

def clean_raw_text(text):
    """Strips out timestamps/dates like 'Jul 31', 'Jul 30', etc."""
    # Removes patterns like 'Jul 31', 'Jul 30'
    cleaned = re.sub(MONTHS_REGEX + r'\s+\d{1,2}', '', text, flags=re.IGNORECASE)
    return cleaned.strip()

def parse_shard_number(text):
    """
    Converts shard strings ('16.0k', '500') into float.
    Ignores plain integers under 100 to avoid misinterpreting dates/quantities.
    """
    clean_text = text.strip().lower()
    
    # Matches numbers with optional decimals and optional 'k'
    match = re.search(r'\b(\d+(?:\.\d+)?)(k)?\b', clean_text)
    if not match:
        return None
    
    number_part = float(match.group(1))
    has_k = bool(match.group(2))

    if has_k:
        return number_part * 1000.0
    
    # Ignore standalone small numbers (< 100) without 'k' to filter out dates/player IDs
    if number_part < 100:
        return None

    return number_part

def format_shard_value(val):
    """Formats numeric shard values into readable strings (e.g. 2000 -> '2k')."""
    if val >= 1000:
        k_val = val / 1000.0
        return f"{k_val:.1f}k" if k_val % 1 != 0 else f"{int(k_val)}k"
    return str(int(val))

def extract_item_and_quantity(item_text):
    """Detects multiplier patterns like 'x8' or '8x' and cleans the item title."""
    clean_item = item_text.strip()
    qty_match = re.search(r'(?:^|\s)(?:x\s*(\d+)|(\d+)\s*x)(?:\s+|$)', clean_item, re.IGNORECASE)
    
    quantity = 1
    if qty_match:
        qty_str = qty_match.group(1) or qty_match.group(2)
        quantity = int(qty_str)
        clean_item = re.sub(r'(?:^|\s)(?:x\s*\d+|\d+\s*x)(?:\s+|$)', ' ', clean_item, flags=re.IGNORECASE).strip()

    return clean_item, quantity

def is_valid_item_name(name):
    """Ensures item name exists, isn't a symbol, and doesn't start with invalid characters."""
    if not name:
        return False
    clean = name.strip()
    if not clean or clean.startswith("—") or clean.startswith("-") or clean in ["—", "-", "--"]:
        return False
    return True

def parse_single_item_trade(raw_text):
    """Parses a single row text into item, quantity, unit shards, and total shards."""
    # Filter out multi-item trades
    if any(tag in raw_text for tag in ["+1 more", "+2 more", "+3 more", "+4 more"]):
        return None

    if "→" not in raw_text and "->" not in raw_text:
        return None

    cleaned_text = clean_raw_text(raw_text)

    separator = "→" if "→" in cleaned_text else "->"
    parts = cleaned_text.split(separator)
    if len(parts) != 2:
        return None

    left_side = parts[0].strip()
    right_side = parts[1].strip()

    left_numeric = parse_shard_number(left_side)
    right_numeric = parse_shard_number(right_side)

    parsed_trade = None

    # Case 1: Shards → Item
    if left_numeric is not None and right_numeric is None:
        item_name, quantity = extract_item_and_quantity(right_side)
        total_shards = left_numeric
        unit_shards = total_shards / quantity if quantity > 0 else total_shards
        
        parsed_trade = {
            "item": item_name,
            "quantity": quantity,
            "shards": format_shard_value(unit_shards),
            "total_shards": format_shard_value(total_shards),
            "raw_trade": raw_text
        }

    # Case 2: Item → Shards
    elif right_numeric is not None and left_numeric is None:
        item_name, quantity = extract_item_and_quantity(left_side)
        total_shards = right_numeric
        unit_shards = total_shards / quantity if quantity > 0 else total_shards
        
        parsed_trade = {
            "item": item_name,
            "quantity": quantity,
            "shards": format_shard_value(unit_shards),
            "total_shards": format_shard_value(total_shards),
            "raw_trade": raw_text
        }

    # Strict check: drop if item name is invalid
    if not parsed_trade or not is_valid_item_name(parsed_trade.get("item")):
        return None

    return parsed_trade

def fetch_rendered_trades():
    """Launch headless browser, wait for DOM, and gather trades."""
    trades = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Navigating to page...")
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=45000)
        
        page.wait_for_timeout(5000)
        content = page.content()
        browser.close()

    soup = BeautifulSoup(content, "html.parser")

    lines = []
    for row in soup.find_all(["tr", "li", "div"]):
        text = row.get_text(separator=" ", strip=True)
        if text and ("→" in text or "->" in text):
            lines.append(text)

    for line in lines:
        parsed = parse_single_item_trade(line)
        if parsed:
            trades.append(parsed)

    return trades

def run_scraper():
    """Run a single scrape execution."""
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
        print(f"Success: Added {added_count} new trade(s). Total trades logged: {len(existing_trades)}")
    else:
        print("No new single-item trades found during this cycle.")

if __name__ == "__main__":
    run_scraper()
