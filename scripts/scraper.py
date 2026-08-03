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

    # UI labels, filters, and non-cosmetic text to exclude
    ignore_keywords = [
        "search", "menu", "login", "home", "values", "discord", "twitter", 
        "copyright", "nav", "filter", "sort", "item list", "my favorites",
        "no favorites", "tags", "range", "shards", "coins", "settings",
        "collection", "compare", "category", "rarity", "type"
    ]

    cosmetics = {}

    def add_item(name, rarity_raw, category, img_url):
        if not name:
            return
        name_clean = str(name).strip()
        
        # Must be valid length and not already captured
        if not name_clean or name_clean in cosmetics or len(name_clean) <= 2:
            return
            
        name_lower = name_clean.lower()
        
        # Skip site headers, UI buttons, and filter labels
        if any(ignore in name_lower for ignore in ignore_keywords):
            return
            
        # Skip pure numbers or shard totals (e.g., "1,250,000")
        if name_clean.replace(",", "").replace(" ", "").isdigit():
            return

        rarity_str = str(rarity_raw).lower() if rarity_raw else "common"
        cosmetics[name_clean] = {
            "name": name_clean,
            "rarity": rarity_map.get(rarity_str, "Common"),
            "category": str(category).strip() if category and str(category).strip().lower() not in ignore_keywords else "Cosmetic",
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

            # 1. Listen for dynamic API data payloads
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

            # 2. Extract embedded script state if present
            try:
                scripts = page.query_selector_all("script")
                for sc in scripts:
                    txt = sc.inner_text().strip()
                    if "rarity" in txt or "imageUrl" in txt:
                        if txt.startswith("{") or txt.startswith("["):
                            parsed = json.loads(txt)
                            def recursive_script_scan(node):
                                if isinstance(node, dict):
                                    if "name" in node:
                                        add_item(
                                            node.get("name"),
                                            node.get("rarity"),
                                            node.get("category") or node.get("type"),
                                            node.get("imageUrl") or node.get("image") or node.get("icon")
                                        )
                                    for v in node.values():
                                        recursive_script_scan(v)
                                elif isinstance(node, list):
                                    for item in node:
                                        recursive_script_scan(item)
                            recursive_script_scan(parsed)
            except Exception:
                pass

            # 3. Smooth scroll to collect item cards specifically
            print("Scrolling page to collect items...")
            for step in range(15):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(1000)

                # Focus specifically on elements likely containing cosmetics
                cards = page.query_selector_all("[class*='item'], [class*='card'], [class*='cosmetic'], tr")
                for el in cards:
                    try:
                        name_el = el.query_selector("h1, h2, h3, h4, h5, p, span")
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

    # Save output dataset cleanly
    os.makedirs("data", exist_ok=True)
    output_file = "data/cosmetics.json"
    final_list = list(cosmetics.values())

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_list, f, indent=2)

    print(f"Completed clean scrape! Saved {len(final_list)} valid cosmetics to {output_file}.")

if __name__ == "__main__":
    run_scraper()
