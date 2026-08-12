import asyncio
import json
import os
import re
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

def extract_numbers_from_json(obj):
    prices = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in ["amount", "shards", "price", "value", "cost", "y", "val"] and isinstance(v, (int, float)) and v > 0:
                prices.append(float(v))
            else:
                prices.extend(extract_numbers_from_json(v))
    elif isinstance(obj, list):
        for item in obj:
            prices.extend(extract_numbers_from_json(item))
    return prices

async def auto_scroll(page):
    await page.evaluate("""async () => {
        await new Promise((resolve) => {
            let totalHeight = 0;
            const distance = 300;
            const timer = setInterval(() => {
                const scrollHeight = document.body.scrollHeight;
                window.scrollBy(0, distance);
                totalHeight += distance;
                if (totalHeight >= scrollHeight) {
                    clearInterval(timer);
                    window.scrollTo(0, 0);
                    resolve();
                }
            }, 80);
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

        captured_api_prices = []

        async def handle_response(response):
            try:
                if "inpvp.net" in response.url and response.status == 200:
                    url_lower = response.url.lower()
                    if any(x in url_lower for x in ["/item", "/history", "/trade", "/cosmetic", "/api/v1"]):
                        ct = response.headers.get("content-type", "")
                        if "application/json" in ct:
                            data = await response.json()
                            found = extract_numbers_from_json(data)
                            if found:
                                captured_api_prices.extend(found)
            except Exception:
                pass

        page.on("response", handle_response)

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
                matched_items_on_page = []
                
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

                        if name_lower in target_cosmetics and name not in processed_item_names and name not in matched_items_on_page:
                            matched_items_on_page.append(name)
                    except Exception:
                        continue

                print(f"Matched {len(matched_items_on_page)} item(s) on page {current_page} with cosmetics.json.")

                for idx, item_name in enumerate(matched_items_on_page):
                    print(f"[{idx+1}/{len(matched_items_on_page)}] Fetching match: {item_name}")
                    captured_api_prices.clear()

                    try:
                        # Absolute target locator using exact text match inside card elements
                        target_card = page.locator("main div[class*='card']").filter(
                            has_text=re.compile(f"^{re.escape(item_name)}$", re.IGNORECASE)
                        ).first

                        if await target_card.count() == 0:
                            # Fallback broad match if exact line regex fails
                            target_card = page.locator("main div[class*='card']").filter(has_text=item_name).first

                        if await target_card.count() > 0:
                            await target_card.scroll_into_view_if_needed()
                            await target_card.click(force=True)
                            
                            await page.wait_for_timeout(2500)

                            shards_tab = page.locator("button:has-text('Shards'), div:has-text('Shards'), a:has-text('Shards')").last
                            if await shards_tab.count() > 0:
                                try:
                                    await shards_tab.wait_for(state="visible", timeout=3000)
                                    await shards_tab.click(force=True)
                                    await page.wait_for_timeout(1500)
                                except Exception:
                                    pass

                            dom_prices = []
                            try:
                                svg_nodes = await page.locator("svg text, svg title, [class*='recharts'], [class*='chart']").all_inner_texts()
                                for node_text in svg_nodes:
                                    cleaned = node_text.replace(",", "").strip()
                                    if cleaned.isdigit() and int(cleaned) > 0:
                                        dom_prices.append(float(cleaned))

                                dom_html = await page.content()
                                dom_matches = re.findall(r'(\d[\d,]*)\s*Shards|Shards:\s*(\d[\d,]*)', dom_html, re.IGNORECASE)
                                for m in dom_matches:
                                    v_str = (m[0] or m[1]).replace(",", "")
                                    if v_str.isdigit() and int(v_str) > 0:
                                        dom_prices.append(float(v_str))
                            except Exception:
                                pass

                            all_prices = captured_api_prices + dom_prices

                            if all_prices:
                                average_val = round(sum(all_prices) / len(all_prices))
                                shard_history = [average_val]
                                print(f"  -> Averaged trade value: {average_val}")
                            else:
                                shard_history = []
                                print(f"  -> No shard trades found.")

                            all_items_shard_data.append({
                                "category": cat_name,
                                "item_name": item_name,
                                "page": current_page,
                                "shard_trade_history": shard_history
                            })
                            processed_item_names.add(item_name)

                            # Close modal cleanly and ensure DOM state resets
                            await page.keyboard.press("Escape")
                            await page.wait_for_timeout(1000)
                            
                            close_btn = page.locator("button:has-text('×'), [role='dialog'] button[aria-label='Close']").first
                            if await close_btn.count() > 0 and await close_btn.is_visible():
                                try:
                                    await close_btn.click(force=True)
                                except Exception:
                                    pass
                                    
                            await page.wait_for_timeout(1500)
                        else:
                            print(f"  -> Element for {item_name} could not be located in DOM.")

                    except Exception as err:
                        print(f"  -> Error fetching '{item_name}': {err}")
                        await page.keyboard.press("Escape")
                        await page.wait_for_timeout(1000)

                # Pagination Advance
                next_page_num = str(current_page + 1)
                next_btn = page.locator(f"button:text-is('{next_page_num}'), a:text-is('{next_page_num}')").first
                arrow_btn = page.locator("button:has-text('>'), a:has-text('>')").first
                
                if await next_btn.count() > 0 and await next_btn.is_visible():
                    await next_btn.scroll_into_view_if_needed()
                    await next_btn.click()
                    current_page += 1
                elif await arrow_btn.count() > 0 and await arrow_btn.is_visible():
                    if not await arrow_btn.get_attribute("disabled"):
                        await arrow_btn.scroll_into_view_if_needed()
                        await arrow_btn.click()
                        current_page += 1
                    else:
                        break
                else:
                    break
                
                await page.wait_for_timeout(4000)

        await browser.close()

    with open("data/trades.json", "w", encoding="utf-8") as f:
        json.dump(all_items_shard_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nDone! Saved {len(all_items_shard_data)} matched items to data/trades.json.")

if __name__ == "__main__":
    asyncio.run(scrape_shard_history())
