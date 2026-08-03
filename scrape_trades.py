import json
import os
import hashlib
import requests

DATA_FILE = "data/trades.json"

# We try both the direct page and the internal JSON API endpoint used by the site
TARGET_URL = "https://inpvp.net/mineville/trades?mode=pvp"
API_URL = "https://inpvp.net/api/mineville/trades?mode=pvp"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://inpvp.net/mineville/trades?mode=pvp"
}

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

def fetch_trades():
    # 1. Try hitting the API endpoint directly
    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=15)
        print(f"API Response Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("trades", data.get("data", [data]))
    except Exception as e:
        print(f"API fetch notice: {e}")

    # 2. Fallback to main page URL
    try:
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
        print(f"Page Response Status Code: {response.status_code}")
        
        # Check for Cloudflare or anti-bot block pages
        if "Just a moment..." in response.text or "Cloudflare" in response.text:
            print("Warning: Request was intercepted by Cloudflare security challenge.")
            return []

        # Try to parse raw JSON if returned
        try:
            data = response.json()
            return data if isinstance(data, list) else data.get("trades", [])
        except ValueError:
            pass

        print("Page loaded, but returned HTML with no readable JSON array.")
        return []

    except Exception as e:
        print(f"Error fetching data: {e}")
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
        print(f"Success: Added {added_count} new trade(s). Total: {len(existing_trades)}")
    else:
        print("No new trades found in this run.")

if __name__ == "__main__":
    main()
