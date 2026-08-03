import json
import os
import hashlib
import requests
from bs4 import BeautifulSoup

DATA_FILE = "data/trades.json"
TARGET_URL = "https://inpvp.net/mineville/trades?mode=pvp"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

def load_existing_trades():
    """Load existing trades from JSON file."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Warning: Existing data file was corrupted or empty. Starting fresh.")
            return []
    return []

def get_trade_signature(trade):
    """Generate a unique signature string to identify duplicate trades."""
    trade_string = json.dumps(trade, sort_keys=True)
    return hashlib.md5(trade_string.encode("utf-8")).hexdigest()

def fetch_trades():
    """Fetch trade data from web page or embedded Next.js JSON payload."""
    try:
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()

        # Attempt 1: Check for embedded __NEXT_DATA__ script (common on modern web apps)
        soup = BeautifulSoup(response.text, "html.parser")
        next_data_script = soup.find("script", id="__NEXT_DATA__")
        
        if next_data_script:
            try:
                payload = json.loads(next_data_script.string)
                # Look for trades in pageProps
                props = payload.get("props", {}).get("pageProps", {})
                if "trades" in props:
                    return props["trades"]
            except Exception as parse_err:
                print(f"Notice: Could not parse __NEXT_DATA__: {parse_err}")

        # Attempt 2: HTML Scraping Fallback (table or list elements)
        trades = []
        rows = soup.find_all(["tr", "div"], class_=lambda c: c and "trade" in c.lower()) if soup else []

        for row in rows:
            text_content = row.get_text(strip=True)
            if text_content:
                trades.append({"raw_text": text_content})

        if not trades:
            # Basic fallback: capture list items or rows if specific classes aren't matched
            all_rows = soup.find_all("tr")
            for row in all_rows:
                cols = [ele.text.strip() for ele in row.find_all(["td", "th"])]
                if cols:
                    trades.append({"columns": cols})

        return trades

    except Exception as e:
        print(f"Error fetching page data: {e}")
        return []

def main():
    existing_trades = load_existing_trades()
    seen_ids = {get_trade_signature(t) for t in existing_trades}
    
    scraped_trades = fetch_trades()
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
        print(f"Success: Added {added_count} new trade(s). Total trades saved: {len(existing_trades)}")
    else:
        print("No new trades found.")

if __name__ == "__main__":
    main()
