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

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            page = context.new_page()

            print(f"Connecting to {url}...")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            # Scroll down quickly to load lazily rendered elements
            print("Scrolling page...")
            for _ in range(5):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(500)

            # Extract ALL data inside the browser context in one fast JavaScript call
            print("Extracting items...")
            raw_items = page.evaluate("""
                () => {
                    const systemLabels = new Set([
                        "home", "value", "values", "compare", "collection", "settings",
                        "item list", "my favorites", "no favorites yet.", "tags",
                        "shard value range", "existing items range", "primary color",
                        "subcategory", "type", "rarity", "search"
                    ]);

                    const items = [];
                    const cardElements = document.querySelectorAll("div, article, section");

                    cardElements.forEach(el => {
                        const titleEl = el.querySelector("h1, h2, h3, h4, h5, p, span");
                        if (!titleEl) return;

                        const name = titleEl.innerText ? titleEl.innerText.trim() : "";
                        if (!name || name.length <= 1) return;

                        const lowerName = name.toLowerCase();
                        if (systemLabels.has(lowerName)) return;

                        // Skip price strings like "0 coins" or "500,000 shards"
                        if ((lowerName.endsWith("coins") || lowerName.endsWith("shards")) && !isNaN(parseInt(name.split(" ")[0].replace(/,/g, "")))) {
                            return;
                        }

                        const rarityEl = el.querySelector("[class*='rarity'], [class*='badge']");
                        const catEl = el.querySelector("[class*='category'], [class*='type']");
                        const imgEl = el.querySelector("img");

                        items.push({
                            name: name,
                            rarity: rarityEl ? rarityEl.innerText.trim() : "Common",
                            category: catEl ? catEl.innerText.trim() : "Cosmetic",
                            imageUrl: imgEl ? imgEl.src : ""
                        });
                    });

                    return items;
                }
            """)

            browser.close()

            # Deduplicate by name
            cosmetics = {}
            for item in raw_items:
                name = item["name"]
                if name not in cosmetics:
                    rarity_raw = str(item.get("rarity", "Common")).lower()
                    cosmetics[name] = {
                        "name": name,
                        "rarity": rarity_map.get(rarity_raw, "Common"),
                        "category": item.get("category", "Cosmetic"),
                        "imageUrl": item.get("imageUrl", "")
                    }

    except Exception as e:
        print(f"Scraper notice: {e}")
        cosmetics = {}

    # Save to JSON
    os.makedirs("data", exist_ok=True)
    output_file = "data/cosmetics.json"
    final_list = list(cosmetics.values())

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_list, f, indent=2)

    print(f"Done! Cleanly saved {len(final_list)} items to {output_file}.")

if __name__ == "__main__":
    run_scraper()
