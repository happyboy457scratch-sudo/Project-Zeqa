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

    # Store items in a dictionary keyed by item name for automatic deduplication
    cosmetics = {}

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

        def process_item(item):
            if isinstance(item, dict):
                name = item.get("name") or item.get("title") or item.get("itemName")
                if name:
                    name_str = str(name).strip()
                    if name_str and name_str not in cosmetics:
                        rarity_raw = str(item.get("rarity", "Common")).lower()
                        cosmetics[name_str] = {
                            "name": name_str,
                            "rarity": rarity_map.get(rarity_raw, "Common"),
                            "category": item.get("category") or item.get("type") or "Cosmetic",
                            "imageUrl": item.get("imageUrl") or item.get("image") or item.get("icon") or ""
                        }

        # 1. Listen for background API network responses continuously
        def handle_response(response):
            try:
                content_type = response.headers.get("content-type", "")
                if "json" in content_type or "api" in response.url:
                    data = response.json()
                    items = []
                    if isinstance(data, list):
                        items = data
                    elif isinstance(data, dict):
                        for k in ["cosmetics", "items", "data", "values", "result"]:
                            if k in data and isinstance(data[k], list):
                                items = data[k]
                                break

                    if items:
                        for item in items:
                            process_item(item)
            except Exception:
                pass

        page.on("response", handle_response)

        print(f"Connecting to {url}...")
        res = page.goto(url, wait_until="domcontentloaded", timeout=60000)
        print(f"Page Response Code: {res.status if res else 'Unknown'}")
        
        page.wait_for_timeout(5000)

        # 2. Adaptive repetition loop: Scroll continuously until item count stops growing
        no_new_items_count = 0
        max_idle_scrolls = 6  # Stop after 6 consecutive scrolls with no new items
        
        print("Starting continuous loop to fetch ALL items...")

        while no_new_items_count < max_idle_scrolls:
            initial_count = len(cosmetics)

            # Scroll down to trigger lazy loading
            page.evaluate("window.scrollBy(0, 1000)")
            page.wait_for_timeout(1500)

            # Check DOM elements if API interception hasn't captured an item yet
            cards = page.query_selector_all("div[class*='item'], div[class*='card'], tr, div[class*='Value']")
            for el in cards:
                try:
                    name_el = el.query_selector("h1, h2, h3, h4, h5, p, span, td")
                    if name_el:
                        name_text = name_el.inner_text().strip()
                        if name_text and 2 < len(name_text) < 45 and name_text not in cosmetics:
                            if not any(ignore in name_text.lower() for ignore in ["search", "menu", "login", "home", "values", "discord", "twitter", "copyright", "nav"]):
                                rarity_el = el.query_selector("[class*='rarity'], [class*='badge']")
                                category_el = el.query_selector("[class*='category'], [class*='type']")
                                img_el = el.query_selector("img")
                                
                                rarity_str = rarity_el.inner_text().strip().lower() if rarity_el else "common"
                                cat_str = category_el.inner_text().strip() if category_el else "Cosmetic"
                                img_url = img_el.get_attribute("src") if img_el else ""

                                cosmetics[name_text] = {
                                    "name": name_text,
                                    "rarity": rarity_map.get(rarity_str, "Common"),
                                    "category": cat_str,
                                    "imageUrl": img_url or ""
                                }
                except Exception:
                    pass

            # Click any 'Load More' or pagination button if present on the page
            load_more = page.query_selector("button:has-text('Load More'), button:has-text('Show More'), [class*='loadMore']")
            if load_more and load_more.is_visible():
                try:
                    load_more.click()
                    print("Clicked 'Load More' button!")
                    page.wait_for_timeout(2000)
                except Exception:
                    pass

            current_count = len(cosmetics)
            new_items_found = current_count - initial_count

            if new_items_found > 0:
                print(f"Scraped +{new_items_found} new items! (Total count: {current_count})")
                no_new_items_count = 0  # Reset counter since new items were found
            else:
                no_new_items_count += 1
                print(f"No new items on scroll attempt {no_new_items_count}/{max_idle_scrolls}...")

        browser.close()

        # Save output dataset
        os.makedirs("data", exist_ok=True)
        output_file = "data/cosmetics.json"
        final_list = list(cosmetics.values())

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_list, f, indent=2)

        print(f"Finished! Total of {len(final_list)} unique cosmetics saved to {output_file}.")

if __name__ == "__main__":
    run_scraper()
