import json
import os
import hashlib
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import git

DATA_FILE = "data/trades.json"
TARGET_URL = "https://inpvp.net/mineville/trades?mode=pvp"
LOOP_INTERVAL_SECONDS = 300  # 5 minutes

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

def parse_single_item_trade(raw_text):
    """
    Filters out multi-item trades (+1 more, etc.) and item-for-item swaps.
    Strictly captures: Shards -> Item  OR  Item -> Shards
    """
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

    # Pattern matching shard amounts (e.g., "10k", "500", "3.5k", "10.0k")
    shard_pattern = re.compile(r'^\d+(\.\d+)?k?$', re.IGNORECASE)

    # Case 1: 10k Shards → Single Item
    if shard_pattern.match(left_side) and not shard_pattern.match(right_side):
        return {
            "item": right_side,
            "shards": left_side,
            "raw_trade": raw_text
        }

    # Case 2: Single Item → 10k Shards
    elif shard_pattern.match(right_side) and not shard_pattern.match(left_side):
        return {
            "item": left_side,
            "shards": right_side,
            "raw_trade": raw_text
        }

    return None

def fetch_rendered_trades():
    """Launch headless browser, wait for page DOM, and gather rendered trades."""
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
    """Commit data/trades.json and push directly to GitHub using Replit secrets."""
    try:
        github_token = os.getenv("GITHUB_TOKEN")
        github_user = os.getenv("GITHUB_USERNAME")
        github_repo = os.getenv("GITHUB_REPO")

        if not all([github_token, github_user, github_repo]):
            print("Missing GitHub secrets in Replit environment. Skipping git push.")
            return

        remote_url = f"https://{github_user}:{github_token}@github.com/{github_user}/{github_repo}.git"

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

def run_scraper_cycle():
    """Single execution run of trade scraper."""
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

def main():
    print("==========================================")
    print("Mineville Trade Scraper Loop Started")
    print(f"Targeting interval: Every {LOOP_INTERVAL_SECONDS} seconds")
    print("==========================================")

    while True:
        start_time = time.time()
        try:
            run_scraper_cycle()
        except Exception as e:
            print(f"An error occurred during loop execution: {e}")

        elapsed = time.time() - start_time
        sleep_duration = max(0, LOOP_INTERVAL_SECONDS - elapsed)
        
        print(f"Sleeping for {int(sleep_duration)} seconds until next run...\n")
        time.sleep(sleep_duration)

if __name__ == "__main__":
    main()
