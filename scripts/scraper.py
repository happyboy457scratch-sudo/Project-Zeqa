import os
import json
import time
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

    cosmetics = {}

    def add_item(name, rarity_raw, category, img_url):
        if not name:
            return
        name_clean = str(name).strip()
        if not name_clean or name_clean in cosmetics:
            return
        if any(ignore in name_clean.lower() for ignore in ["search", "menu", "login", "home", "values", "discord", "twitter", "copyright", "nav", "filter", "sort"]):
            return
        
        rarity_str = str(rarity_raw).lower() if rarity_raw else "common"
        cosmetics[name_clean] = {
            "name": name_clean,
            "rarity": rarity_map.get(rarity_str, "Common"),
            "category": str(category).strip() if category else "Cosmetic",
            "imageUrl": str(img_url).strip() if img_url else ""
        }

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

        # Catch dynamic network traffic
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
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        print("Starting infinite scroll down the entire page...")
        
        last_height = page.evaluate("document.body.scrollHeight")
        idle_scrolls = 0
        max_idle_scrolls = 5

        while idle_scrolls < max_idle_scrolls:
            prev_item_count = len(cosmetics)

            # Scroll all the way down to trigger infinite scroll load
            page.mouse.wheel(0, 5000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # Pause to allow network requests and items to render
            page.wait_for_timeout(2500)

            # Parse currently rendered cards
            cards = page.query_selector_all("div, tr, li, article")
            for el in cards:
                try:
                    name_el = el.query_selector("h1, h2, h3, h4, h5, p, span, td")
                    if name_el:
                        name_text = name_el.inner_text().strip()
                        if name_text and 2 < len(name_text) < 45:
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

            new_height = page.evaluate("document.body.scrollHeight")
            new_item_count = len(cosmetics)

            print(f"Page Height: {new_height}px | Total items captured so far: {new_item_count}")

            # Stop if neither the height nor the item count increases after several attempts
            if new_height == last_height and new_item_count == prev_item_count:
                idle_scrolls += 1
                print(f"No new items loaded. Retrying... ({idle_scrolls}/{max_idle_scrolls})")
            else:
                idle_scrolls = 0
                last_height = new_height

        browser.close()

        # Save output dataset
        os.makedirs("data", exist_ok=True)
        output_file = "data/cosmetics.json"
        final_list = list(cosmetics.values())

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_list, f, indent=2)

        print(f"Scrape completed! Total of {len(final_list)} items saved to {output_file}.")

if __name__ == "__main__":
    run_scraper()
