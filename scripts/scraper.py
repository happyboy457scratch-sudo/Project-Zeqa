import os
import json
from playwright.sync_api import sync_playwright

def load_reference_names():
    """Loads valid cosmetic names from cosmetics.json if it exists."""
    ref_file = "data/cosmetics.json"
    if os.path.exists(ref_file):
        try:
            with open(ref_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {item.get("name") for item in data if "name" in item}
                elif isinstance(data, dict):
                    return set(data.keys())
        except Exception as e:
            print(f"Could not load reference names: {e}")
    return set()

def clean_and_match_name(raw_name, valid_names):
    """
    Checks if any known valid name is present within the raw scraped string.
    If a match is found, it returns only the matched name.
    """
    if not valid_names:
        return raw_name

    if raw_name in valid_names:
        return raw_name

    matched_name = None
    for valid_name in sorted(valid_names, key=len, reverse=True):
        if valid_name.lower() in raw_name.lower():
            matched_name = valid_name
            break
            
    return matched_name

def run_scraper():
    url = "https://milkyclan.com/values"
    output_file = "data/cosmetics.json"
    
    # 1. Load valid names before wiping the file
    valid_names = load_reference_names()

    # 2. ALWAYS DELETE THE OLD FILE IF IT EXISTS TO WIPE GLITCHED DATA
    if os.path.exists(output_file):
        try:
            os.remove(output_file)
            print(f"Deleted old {output_file} to clear previous data.")
        except Exception as e:
            print(f"Error removing old file: {e}")

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

            print("Scrolling page...")
            for _ in range(5):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(500)

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

            # Process, filter, and clean items
            for item in raw_items:
                raw_name = item["name"]
                
                # Autodelete filter: Must start with a capital letter (A-Z) or a number (0-9)
                if not raw_name or not (raw_name[0].isupper() or raw_name[0].isdigit()):
                    continue

                # Match and trim name against valid cosmetics list
                matched_name = clean_and_match_name(raw_name, valid_names)
                
                # If a reference list exists and this item couldn't be matched, skip it
                if valid_names and not matched_name:
                    continue
                
                name = matched_name if matched_name else raw_name

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

    # 3. WRITE FRESH CLEAN DATA
    os.makedirs("data", exist_ok=True)
    final_list = list(cosmetics.values())

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_list, f, indent=2)

    print(f"Done! Cleanly replaced file and saved {len(final_list)} items to {output_file}.")

if __name__ == "__main__":
    run_scraper()
