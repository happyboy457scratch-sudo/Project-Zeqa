import requests
import json
import re
import time
import os

BASE_URL = "https://inpvp.com/mineville/cosmetics"

# Define categories and total item counts provided
CATEGORIES = {
    "artifacts": 327,
    "capes": 385,
    "killphrases": 65,
    "projectiles": 13
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def extract_graph_chunks(html_text):
    """Extracts raw Next.js state chunks containing graph dates/prices."""
    raw_chunks = re.findall(r'self\.__next_f\.push\((.*?)\)', html_text)
    relevant_data = []
    
    for chunk in raw_chunks:
        # Check if the chunk contains pricing or trade history indicators
        if any(keyword in chunk for keyword in ['shards', 'history', 'price', 'points']):
            relevant_data.append(chunk)
            
    return relevant_data

def run_scraper():
    os.makedirs("data/scraped_graphs", exist_ok=True)
    all_results = {}

    for cat_name, total_count in CATEGORIES.items():
        print(f"\n--- Scraping Category: {cat_name.upper()} (1 to {total_count}) ---")
        cat_data = {}

        for item_id in range(1, total_count + 1):
            target_url = f"{BASE_URL}/{cat_name}/{item_id}"
            
            try:
                response = requests.get(target_url, headers=HEADERS, timeout=10)
                
                if response.status_code == 200:
                    chunks = extract_graph_chunks(response.text)
                    cat_data[item_id] = {
                        "url": target_url,
                        "chunks_found": len(chunks),
                        "data": chunks
                    }
                    print(f"[{cat_name}] Item #{item_id}: OK ({len(chunks)} graph chunks)")
                else:
                    print(f"[{cat_name}] Item #{item_id}: Skipped (HTTP {response.status_code})")

            except Exception as e:
                print(f"[{cat_name}] Item #{item_id}: Failed ({e})")

            # Small pause to avoid getting rate-limited by Cloudflare
            time.sleep(0.3)

        all_results[cat_name] = cat_data

    # Save full dump
    with open("data/scraped_graphs/all_cosmetics_graphs.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print("\nScraping finished! Saved data to data/scraped_graphs/all_cosmetics_graphs.json")

if __name__ == "__main__":
    run_scraper()
