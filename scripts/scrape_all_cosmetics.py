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
    file_path = "cosmetics.json" if os.path.exists("cosmetics.json") else "data/cosmetics.json"
    if not os.path.exists(file_path):
        print("Warning: 'cosmetics.json' not found.")
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

async def auto_scroll(page):
    await page.evaluate("""async () => {
        await new Promise((resolve) => {
            let totalHeight = 0;
            const distance = 400;
            const timer = setInterval(() => {
                const scrollHeight = document.body.scrollHeight;
                window.scrollBy(0, distance);
                totalHeight += distance;
                if (totalHeight >= scrollHeight) {
                    clearInterval(timer);
                    window.scrollTo(0, 0);
                    resolve();
                }
            }, 50);
        });
    }""")
    await page.wait_for_timeout(1000)

async def scrape_shard_history():
    os.makedirs("data", exist_ok=True)
    target_cosmetics = load_target_cosmetics()
    
    all_items_shard_data = []
    processed_item_names = set()

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

        print(f"Navigating to Mineville Vault: {VAULT_URL}")
        try:
            await page.goto(VAULT_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            await page.goto(VAULT_URL, wait_until="load", timeout=60000)
            
        await page.wait_for_timeout(4000)

        for cat_name in CATEGORIES:
            print(f"\n================ Processing Category: {cat_name} ================")

            cat_tab = page.locator(f"button:has-text('{cat_name}'), a:has-text('{cat_name}')").first
            if await cat_tab.count() > 0:
                await cat_tab.click()
                await page.wait_for_timeout(3000)

            current_page = 1
            while True:
                print(f"--- Category: {cat_name} | Page {current_page} ---")
                
                await auto_scroll(page)

                raw_cards = page.locator("main [class*='cursor-pointer'], main a, main div[class*='card']")
                count = await raw_cards.count()
                matched_on_page = 0
                
                for i in range(count):
                    try:
                        card = raw_cards.nth(i)
                        text = (await card.inner_text()).strip()
                        if not text:
                            continue
                        
                        lines = [l.strip() for l in text.split("\n") if l.strip()]
                        if not lines:
                            continue
                        
                        name = lines[0]
                        name_lower = name.lower()

                        if name_lower in target_cosmetics and name not in processed_item_names:
                            processed_item_names.add(name)
                            matched_on_page += 1
                            
                            card_prices = []
                            for line in lines[1:]:
                                cleaned = "".join([c for c in line if c.isdigit()])
                                if cleaned and int(cleaned) > 0:
                                    card_prices.append(float(cleaned))

                            # Calculate the average of the graph data points if they exist
                            avg_value = 0
                            if card_prices:
                                avg_value = round(sum(card_prices) / len(card_prices), 2)

                            all_items_shard_data.append({
                                "category": cat_name,
                                "item_name": name,
                                "page": current_page,
                                "average_shard_value": avg_value,
                                "shard_trade_history": card_prices
                            })
                    except Exception:
                        continue

                print(f"Captured {matched_on_page} matched item(s) from page {current_page}.")

                # Pagination advancement logic
                next_page_num = str(current_page + 1)
                next_btn = page.locator(f"button:text-is('{next_page_num}'), a:text-is('{next_page_num}')").first
                generic_next = page.locator("button[aria-label*='Next' i], a[aria-label*='Next' i], button:has-text('Next'), nav button:has-text('>')").first
                
                advanced = False
                
                if await next_btn.count() > 0 and await next_btn.is_visible():
                    await next_btn.scroll_into_view_if_needed()
                    await next_btn.click()
                    current_page += 1
                    advanced = True
                elif await generic_next.count() > 0 and await generic_next.is_visible():
                    is_disabled = await generic_next.get_attribute("disabled") is not None
                    aria_disabled = await generic_next.get_attribute("aria-disabled") == "true"
                    
                    if not is_disabled and not aria_disabled:
                        await generic_next.scroll_into_view_if_needed()
                        await generic_next.click()
                        current_page += 1
                        advanced = True

                if not advanced:
                    print(f"Reached the end of category: {cat_name}")
                    break
                
                await page.wait_for_timeout(3000)

        await browser.close()

    with open("data/trades.json", "w", encoding="utf-8") as f:
        json.dump(all_items_shard_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nDone! Successfully calculated averages and saved {len(all_items_shard_data)} items to data/trades.json.")

if __name__ == "__main__":
    asyncio.run(scrape_shard_history())
