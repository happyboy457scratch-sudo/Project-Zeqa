import requests
import json
import re
import os
import time

BASE_URL = "https://inpvp.net/mineville/cosmetics"

# Categories and their item limits
CATEGORIES = {
    "artifacts": 327,
    "capes": 385,
    "killphrases": 65,
    "projectiles": 13
}

# Create a browser session to maintain cookies & bypass basic bot blocks
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://inpvp.net/mineville/cosmetics"
})

def parse_trade_chunks(raw_chunks, default_item_name="Unknown Item"):
    """Parses Next.js data stream chunks into structured JSON trades."""
    trades = []
    
    for chunk in raw_chunks:
        if "shards" in chunk or "trade" in chunk:
            matches = re.findall(r'\{[^{}]*"shards"[^{}]*\}', chunk)
            for m in matches:
                try:
                    clean_json = m.replace('\\"', '"')
                    data = json.loads(clean_json)
                    
                    trade_entry = {
                        "item": str(data.get("item", default_item_name)),
                        "quantity": int(data.get("quantity", 1)),
                        "shards": str(data.get("shards", "0")),
                        "total_shards": str(data.get("total_shards", data.get("shards", "0"))),
                        "raw_trade": str(data.get("raw_trade", f"{data.get('item', default_item_name)} → {data.get('shards', '0')}"))
                    }
                    trades.append(trade_entry)
                except json.JSONDecodeError:
                    continue

    return trades

def run_scraper():
    os.makedirs("data", exist_ok=True)
    all_trades = []

    for cat_name, total_count in CATEGORIES.items():
        print(f"\n--- Scraping Category: {cat_name.upper()} (1 to {total_count}) ---")

        for item_id in range(1, total_count + 1):
            # Matches exact format: https://inpvp.net/mineville/cosmetics/artifacts/7
            target_url = f"{BASE_URL}/{cat_name}/{item_id}"
            
            try:
                response = session.get(target_url, timeout=10)
                
                if response.status_code == 200:
                    raw_chunks = re.findall(r'self\.__next_f\.push\((.*?)\)', response.text)
                    extracted_trades = parse_trade_chunks(raw_chunks)
                    
                    all_trades.extend(extracted_trades)
                    print(f"[{cat_name}] Item #{item_id}: OK (Extracted {len(extracted_trades)} trades)")
                else:
                    print(f"[{cat_name}] Item #{item_id}: HTTP {response.status_code} -> {target_url}")

            except Exception as e:
                print(f"[{cat_name}] Item #{item_id}: Error ({e})")

            # Pause between requests to stay under rate limits
            time.sleep(0.3)

    # Save final array directly into data/trades.json
    output_path = "data/trades.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_trades, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Successfully saved {len(all_trades)} trades to {output_path}")

if __name__ == "__main__":
    run_scraper()
