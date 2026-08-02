import os
import json
import time
from playwright.sync_api import sync_playwright

def run_scraper():
    url = "https://inpvp.net/mineville/vault?mode=pvp"
    
    rarity_map = {
        "common": "Common",
        "rare": "Rare",
        "epic": "Epic",
        "legendary": "Legendary",
        "limited": "Limited",
        "exotic": "Exotic",
        "partner": "Partner"
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print(f"Loading {url}...")
        page.goto(url, wait_until="networkidle")
        time.sleep(5)  # Allow page hydration to complete

        cosmetics = []

        # Try extracting directly from Next.js payload
        next_data = page.query_selector("script#__NEXT_DATA__")
        if next_data:
            try:
                raw_json = json.loads(next_data.inner_text())
                page_props = raw_json.get("props", {}).get("pageProps", {})
                raw_items = page_props.get("cosmetics") or page_props.get("items") or page_props.get("vault") or []

                for idx, item in enumerate(raw_items, 1):
                    rarity_raw = str(item.get("rarity", "Common")).lower()
                    rarity = rarity_map.get(rarity_raw, "Common")
                    
                    cosmetics.append({
                        "id": item.get("id", idx),
                        "name": item.get("name", f"Cosmetic {idx}"),
                        "category": item.get("category", "Items"),
                        "rarity": rarity,
                        "value": item.get("value", 10000),
                        "demand": item.get("demand", 5),
                        "salesExistingRatio": item.get("salesExistingRatio", 50),
                        "priceHistory": item.get("priceHistory", [8000, 8500, 9000, 9500, 10000]),
                        "imageUrl": item.get("imageUrl") or item.get("image") or ""
                    })
            except Exception as e:
                print(f"Error parsing Next.js payload: {e}")

        browser.close()

        # Ensure output folder exists
        os.makedirs("data", exist_ok=True)
        output_file = "data/cosmetics.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(cosmetics, f, indent=2)

        print(f"Saved {len(cosmetics)} items to {output_file}!")

if __name__ == "__main__":
    run_scraper()
