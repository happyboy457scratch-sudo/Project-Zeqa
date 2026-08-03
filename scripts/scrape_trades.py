import json
import os
import hashlib
import requests

DATA_FILE = "data/trades.json"
TARGET_URL = "https://inpvp.net/mineville/trades?mode=pvp"

# Headers to mimic a real browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "application/json, text/plain, */*"
}

def load_existing_trades():
    """Load existing trades from JSON file to prevent duplicates."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Warning: Existing data file was corrupted or empty. Starting fresh.")
            return []
    return []

def get_trade_signature(trade):
    """Generate a unique ID/hash for a trade if an explicit ID isn't provided."""
    if "id" in trade:
        return str(trade["id"])
    
    # Hash unique fields (e.g. buyer, seller, items, timestamp)
    trade_string = json.dumps(trade, sort_keys=True)
    return hashlib.md5(trade_string.encode("utf-8")).hexdigest()

def fetch_trades():
    """Fetch recent trades from the endpoint or page."""
    try:
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        # Check if response is raw JSON (API endpoint)
        if "application/json" in response.headers.get("Content-Type", ""):
            data = response.json()
            return data.get("trades", data) if isinstance(data, dict) else data
        
        # Fallback parsing placeholder if endpoint returns structured page payload
        print("Page returned HTML/text. Ensure target URL points to API endpoint if applicable.")
        return []
    except Exception as e:
        print(f"Error fetching trade data: {e}")
        return []

def main():
    existing_trades = load_existing_trades()
    
    # Track existing unique IDs/signatures
    seen_ids = {get_trade_signature(t) for t in existing_trades}
    
    new_raw_trades = fetch_trades()
    added_count = 0

    for trade in new_raw_trades:
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
        print("No new trades found.")

if __name__ == "__main__":
    main()
