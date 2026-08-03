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

    cosmetics = []

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

        # 1. Listen for dynamic API network responses
        def handle_response(response):
            nonlocal cosmetics
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
                        print(f"[API Intercept] Caught {len(items)} items from: {response.url}")
                        for idx, item in enumerate(items, 1):
                            if isinstance(item, dict):
                                name = item.get("name") or item.get("title") or item.get("itemName")
                                if name:
                                    rarity_raw = str(item.get("rarity", "Common")).lower()
                                    cosmetics.append({
                                        "id": item.get("id", idx),
                                        "name": str(name).strip(),
                                        "category": item.get("category", "Items"),
                                        "rarity": rarity_map.get(rarity_raw, "Common"),
                                        "value": item.get("value", item.get("price", 10000)),
                                        "demand": item.get("demand", 5),
                                        "salesExistingRatio": item.get("salesExistingRatio", 50),
                                        "priceHistory": item.get("priceHistory", [8000, 8500, 9000, 9500, 10000]),
                                        "imageUrl": item.get("imageUrl") or item.get("image") or item.get("icon") or ""
                                    })
            except Exception:
                pass

        page.on("response", handle_response)

        print(f"Connecting to {url}...")
        res = page.goto(url, wait_until="domcontentloaded", timeout=60000)
        print(f"Page Response Code: {res.status if res else 'Unknown'}")
        
        # Give full JavaScript framework time to initialize
        page.wait_for_timeout(6000)

        # Scroll down to force image and list hydration
        for _ in range(5):
            page.evaluate("window.scrollBy(0, 800)")
            page.wait_for_timeout(1000)

        # 2. Check embedded script tags (Next.js / React hydration payloads)
        if not cosmetics:
            print("Checking page script tags for embedded data...")
            next_script = page.query_selector("script#__NEXT_DATA__")
            if next_script:
                try:
                    raw_data = json.loads(next_script.inner_text())
                    page_props = raw_data.get("props", {}).get("pageProps", {})
                    items = page_props.get("values") or page_props.get("items") or page_props.get("cosmetics") or []
                    print(f"[Script Payload] Found {len(items)} items inside __NEXT_DATA__")
                    for idx, item in enumerate(items, 1):
                        if isinstance(item, dict) and "name" in item:
                            rarity_raw = str(item.get("rarity", "Common")).lower()
                            cosmetics.append({
                                "id": item.get("id", idx),
                                "name": item["name"],
                                "category": item.get("category", "Items"),
                                "rarity": rarity_map.get(rarity_raw, "Common"),
                                "value": item.get("value", 10000),
                                "demand": item.get("demand", 5),
                                "salesExistingRatio": item.get("salesExistingRatio", 50),
                                "priceHistory": item.get("priceHistory", [8000, 8500, 9000, 9500, 10000]),
                                "imageUrl": item.get("imageUrl") or item.get("image") or ""
                            })
                except Exception as e:
                    print(f"Error parsing script tag: {e}")

        # 3. Fallback: Parse rendered DOM cards
        if not cosmetics:
            print("Parsing rendered page elements...")
            cards = page.query_selector_all("div, tr, li, article")
            seen_names = set()
            
            for idx, el in enumerate(cards, 1):
                try:
                    title_el = el.query_selector("h1, h2, h3, h4, h5, p, span, td")
                    img_el = el.query_selector("img")
                    
                    if title_el:
                        name = title_el.inner_text().strip()
                        # Ignore general UI text
                        if name and 2 < len(name) < 45 and name not in seen_names:
                            if not any(ignore in name.lower() for ignore in ["search", "menu", "login", "home", "values", "discord", "twitter", "copyright", "nav"]):
                                seen_names.add(name)
                                img_url = img_el.get_attribute("src") if img_el else ""
                                cosmetics.append({
                                    "id": len(cosmetics) + 1,
                                    "name": name,
                                    "category": "Items",
                                    "rarity": "Common",
                                    "value": 10000,
                                    "demand": 5,
                                    "salesExistingRatio": 50,
                                    "priceHistory": [8000, 8500, 9000, 9500, 10000],
                                    "imageUrl": img_url or ""
                                })
                except Exception:
                    pass

        browser.close()

        # Save outputs
        os.makedirs("data", exist_ok=True)
        output_file = "data/cosmetics.json"

        unique_cosmetics = {c["name"]: c for c in cosmetics if c.get("name")}.values()
        final_list = list(unique_cosmetics)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_list, f, indent=2)

        print(f"Scrape completed! Saved {len(final_list)} cosmetics to {output_file}.")

if __name__ == "__main__":
    run_scraper()
