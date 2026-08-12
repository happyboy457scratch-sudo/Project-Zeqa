import asyncio
import json
import os
from playwright.async_api import async_playwright

VAULT_URL = "https://inpvp.net/mineville/vault?mode=pvp"

CATEGORIES = [
    "Artifacts", 
    "Capes", 
    "Killphrases", 
    "Projectiles"
]

def load_target_cosmetics():
    """Loads cosmetics.json into a lookup set."""
    file_path = "cosmetics.json" if os.path.exists("cosmetics.json") else "data/cosmetics.json"
    if not os.path.exists(file_path):
        print("Warning: 'cosmetics.json' not found. 0 matches will occur.")
        return set()

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    target_set = set()
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                target_set.add(item.strip().lower())
            elif isinstance(item, dict):
                name = item.get("item_name") or item.get("name")
                if name:
                    target_set.add(name.strip().lower())
    elif isinstance(data, dict):
        for key in data.keys():
            target_set.add(key.strip().lower())

    print(f"Loaded {len(target_set)} unique target cosmetic names to match against.")
    return target_set

def extract_prices_and_items(obj, collected_data):
    """Recursively walks through API JSON payloads to find items and their corresponding shard values."""
    if isinstance(obj, dict):
        # Look for potential item name keys alongside value/shard keys
        item_name = obj.get("name") or obj.get("item_name") or obj.get("title")
        
        # Look for numerical values representing costs, shards, or prices
        prices = []
        for k, v in obj.items():
            if k.lower() in ["amount", "shards", "price", "value", "cost", "y", "val"] and isinstance(v, (int, float)) and v > 0:
                prices.append(float(v))
        
        if item_name and prices:
            collected_data[item_name.strip().lower()] = {
                "original_name": item_name.strip(),
                "prices": prices
            }
            
        for k, v in obj.items():
            extract_prices_and_items(v, collected_data)
            
    elif isinstance(obj, list):
        for item in obj:
            extract_prices_and_items(item, collected_data)

async def scrape_shard_history():
    os.makedirs("data", exist_ok=True)
    target_cosmetics = load_target_cosmetics()
    
    master_api_cache = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox"]
        )
        
        context_kwargs = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "viewport": {"width": 1400, "height": 900}
        }
        
        if os.path.exists("state.json"):
            context_kwargs["storage_state"] = "state.json"

        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()

        # Intercept background API responses containing vault data
        async def handle_response(response):
            try:
                if "inpvp.net" in response.url and response.status == 200:
                    url_lower = response.url.lower()
                    if any(x in url_lower for x in ["/item", "/history", "/trade", "/cosmetic", "/api/v1", "/vault"]):
                        ct = response.headers.get("content-type", "")
                        if "application/json" in ct:
                            data = await response.json()
                            extract_prices_and_items(data, master_api_cache)
            except Exception:
                pass

        page.on("response", handle_response)

        print(f"Navigating to Mineville Vault: {VAULT_URL}")
        try:
            await page.goto(VAULT_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            await page.goto(VAULT_URL, wait_until="load", timeout=60000)
            
        await page.wait_for_timeout(5000)

        # Click through categories to force the site to fire all background API calls
        for cat_name in CATEGORIES:
            print(f"Requesting category feed: {cat_name}")
            cat_tab = page.locator(f"button:has-text('{cat_name}'), a:has-text('{cat_name}')").first
            if await cat_tab.count() > 0:
                try:
                    await cat_tab.click()
                    await page.wait_for_timeout(3000)
                except Exception:
                    pass

        await browser.close()

    # Match intercepted API data against cosmetics.json targets
    all_items_shard_data = []
    
    for target_lower in target_cosmetics:
        if target_lower in master_api_cache:
            item_info = master_api_cache[target_lower]
            prices = item_info["prices"]
            avg_price = round(sum(prices) / len(prices)) if prices else 0
            
            all_items_shard_data.append({
                "category": "Matched from API",
                "item_name": item_info["original_name"],
                "page": 1,
                "shard_trade_history": [avg_price] if avg_price > 0 else []
            })

    # Save output
    with open("data/trades.json", "w", encoding="utf-8") as f:
        json.dump(all_items_shard_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nDone! Successfully matched and saved {len(all_items_shard_data)} items to data/trades.json.")

if __name__ == "__main__":
    asyncio.run(scrape_shard_history())
