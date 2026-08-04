import json
import os
import hashlib
import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import git

DATA_FILE = "data/trades.json"
TARGET_URL = "https://inpvp.net/mineville/trades?mode=pvp"

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

def parse_shard_number(text):
    """Converts shard strings ('16.0k', '500') into numeric float."""
    clean_text = text.strip().lower()
    match = re.search(r'\b(\d+(?:\.\d+)?)(k)?\b', clean_text)
    if not match:
        return None
    
    number_part = float(match.group(1))
    has_k = bool(match.group(2))

    if has_k:
        return number_part * 1000.0
    return number_part

def format_shard_value(val):
    """Formats numeric shard values into readable strings (e.g. 2000 -> '2.0k')."""
    if val >= 1000:
        k_val = val / 1000.0
        return f"{k_val:.1f}k" if k_val % 1 != 0 else f"{int(k_val)}k"
    return str(int(val))

def extract_item_and_quantity(item_text):
    """Detects multiplier patterns like 'x8' or '8x' and strips them out."""
    clean_item = item_text.strip()
    qty_match = re.search(r'(?:^|\s)(?:x\s*(\d+)|(\d+)\s*x)(?:\s+|$)', clean_item, re.IGNORECASE)
    
    quantity = 1
    if qty_match:
        qty_str = qty_match.group(1) or qty_match.group(2)
        quantity = int(qty_str)
        clean_item = re.sub(r'(?:^|\s)(?:x\s*\d+|\d+\s*x)(?:\s+|$)', ' ', clean_item, flags=re.IGNORECASE).strip()

    return clean_item, quantity

def is_valid_item_name(name):
    """Ensures the item name exists and isn't a placeholder symbol."""
    if not name:
        return False
    clean = name.strip()
    if not clean or clean in ["—", "-", "--"]:
        return False
    return True

def parse_single_item_trade(raw_text):
    """Extracts item, quantity, total shards, and calculates unit shard price."""
    if any(tag in raw_text for tag in ["+1 more", "+2 more", "+3 more", "+4 more"]):
        return None

    if "→" not in raw_text and "->" not in raw_text:
        return None

    separator = "→" if "→" in raw_text else "->"
    parts = raw_text.split(separator)
    if len(parts) != 2:
        return None

    left_side = parts[0].strip()
    right_side = parts[1].strip()

    left_numeric = parse_shard_number(left_side)
    right_numeric = parse_shard_number(right_side)

    parsed_trade = None

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

def push_changes_to_github():
    """Commit data/trades.json and push using GitHub Action runner token."""
    try:
        github_token = os.getenv("GITHUB_TOKEN")
        github_user = os.getenv("GITHUB_USERNAME", "happyboy457scratch-sudo")
        github_repo = os.getenv("GITHUB_REPO", "Project-Zeqa")

        if not github_token:
            print("Missing GITHUB_TOKEN environment variable. Skipping git push.")
            return

        remote_url = f"https://x-access-token:{github_token}@github.com/{github_user}/{github_repo}.git"

        repo = git.Repo(os.getcwd())
        repo.git.add(DATA_FILE)
        
        if repo.is_dirty(path=DATA_FILE):
            commit_msg = f"Auto-update: Latest trade data ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
            repo.index.commit(commit_msg)
            
            origin = repo.remote(name='origin')
            origin.set_url(remote_url)
            origin.push()
            print("Successfully pushed new trade data to GitHub!")
        else:
            print("No new changes detected in trades file.")
    except Exception as e:
        print(f"Git push notice: {e}")

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
        push_changes_to_github()
    else:
        print("No new single-item trades found during this cycle.")

if __name__ == "__main__":
    run_scraper()
