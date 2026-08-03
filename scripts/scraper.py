import os
import json
from playwright.sync_api import sync_playwright

def run_scraper():
    url = "https://milkyclan.com/values"
    
    rarity_map = {
        "common": "Common",
        "rare": "Rare",
        "epic": "Epic",
        "legendary": "Legendary",
        "limited": "Limited",
        "exotic": "Exotic",
        "partner": "Partner"
    }

    # Only filter out actual UI system buttons & navigation links
    exact_system_labels = {
        "home", "value", "values", "compare", "collection", "settings",
        "item list", "my favorites", "no favorites yet.", "tags",
        "shard value range", "existing items range", "primary color",
        "subcategory", "type", "rarity", "search"
    }

    cosmetics = {}

    def add_item(name, rarity_raw, category, img_url):
        if not name:
            return
        name_clean = str(name).strip()
        
        if not name_clean or name_clean in cosmetics:
            return
            
        name_lower = name_clean.lower()
        
        # Skip exact UI section headers and system tabs
        if name_lower in exact_system_labels:
            return
            
        # Ignore raw unit prices like "0 coins" or "0 shards" if captured as titles
        if name_lower.endswith("coins") or name_lower.endswith("shards"):
            # Only ignore if it starts with a number (e.g., "0 coins", "500,000 shards")
            if name_clean.split()[0].replace(",", "").isdigit():
                return

        rarity_str = str(rarity_raw).lower() if rarity_raw else "common"
        cosmetics[name_clean] = {
            "name": name_clean,
            "rarity": rarity_map.get(rarity_str, "Common"),
            "category": str(category).strip() if category and str(category).strip().lower() not in exact_system_labels else "Cosmetic",
            "imageUrl": str(img_url).strip() if img_url else ""
        }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox"
                ]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            page = context.new_page()

            # 1. Dynamic API Response Listener
            def handle_response(response):
                try:
                    content_type = response.headers.get("content-type", "")
                    if "json" in content_type or "api" in response.url:
                        data = response.json()
                        def recursive_find(obj):
                            if isinstance(obj, dict):
                                if "name" in obj or "itemName" in obj or "title" in obj:
                                    name = obj.get("name") or obj.get("itemName") or obj.get("title")
                                    add_item(
                                        name,
                                        obj.get("rarity"),
                                        obj.get("category") or obj.get("type"),
                                        obj.get("imageUrl") or obj.get("image") or obj.get("icon")
                                    )
                                for v in obj.values():
                                    recursive_find(v)
                            elif isinstance(obj, list):
                                for item in obj:
                                    recursive_find(item)
                        recursive_find(data)
                except Exception:
                    pass

            page.on("response", handle_response)

            print(f"Connecting to {url}...")
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4000)

            # 2. Page Scroll Loop
            print("Scrolling to load all items...")
            for step in range(20):
                page.mouse.wheel(0, 1000)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(800)

                # Extract content from item card elements
                cards = page.query_selector_all("div, article, section")
                for el in cards:
                    try:
                        name_el = el.query_selector("h1, h2, h3, h4, h5, p, span, div")
                        if name_el:
                            name_text = name_el.inner_text().strip()
                            rarity_el = el.query_selector("[class*='rarity'], [class*='badge']")
                            cat_el = el.query_selector("[class*='category'], [class*='type']")
                            img_el = el.query_selector("img")

                            add_item(
                                name_text,
                                rarity_el.inner_text().strip() if rarity_el else "Common",
                                cat_el.inner_text().strip() if cat_el else "Cosmetic",
                                img_el.get_attribute("src") if img_el else ""
                            )
                    except Exception:
                        pass

            browser.close()

    except Exception as e:
        print(f"Scraper execution notice: {e}")

    # Write output to JSON
    os.makedirs("data", exist_ok=True)
    output_file = "data/cosmetics.json"
    final_list = list(cosmetics.values())

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_list, f, indent=2)

    print(f"Done! Cleanly saved {len(final_list)} cosmetics to {output_file}.")

if __name__ == "__main__":
    run_scraper()
