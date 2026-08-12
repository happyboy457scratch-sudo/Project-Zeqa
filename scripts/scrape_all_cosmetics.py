import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

VAULT_URL = "https://inpvp.net/mineville/vault?mode=pvp"

CATEGORIES = [
    {"name": "Artifacts", "pages": 7},
    {"name": "Capes", "pages": 8},
    {"name": "Killphrases", "pages": 2},
    {"name": "Projectiles", "pages": 1}
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

def extract_numbers_from_json(obj):
    """Recursively pulls non-zero numerical price values from JSON structures."""
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
    """Scrolls down and back up to trigger dynamic image and card loading."""
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
    await page.wait_for_timeout(800)

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

        # Catch ANY successful JSON response from inpvp.net
        async def handle_response(response):
            try:
                if "inpvp.net" in response.url and response.status == 200:
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
            await page.goto(VAULT_URL, wait_until="networkidle", timeout=60000)
        except Exception:
            await page.goto(VAULT_URL, wait_until="load", timeout=60000)
            
        await page.wait_for_timeout(3000)

        for cat in CATEGORIES:
            cat_name = cat["name"]
            total_pages = cat["pages"]

            print(f"\n================ Processing Category: {cat_name} ================")

            cat_tab = page.locator(f"button:has-text('{cat_name}'), a:has-text('{cat_name}')").first
            if await cat_tab.count() > 0:
                await cat_tab.click()
                await page.wait_for_timeout(3000)

            for current_page in range(1, total_pages + 1):
                print(f"--- Category: {cat_name} | Page {current_page}/{total_pages} ---")
                
                await auto_scroll(page)

                # Find matching cosmetic cards on current page
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

                # Scrape each matched item
                for idx, item_name in enumerate(matched_items_on_page):
                    try:
                        print(f"[{idx+1}/{len(matched_items_on_page)}] Fetching match: {item_name}")
                        captured_api_prices.clear()

                        clickables = page.locator("main [class*='cursor-pointer'], main a, main div[class*='card']")
                        total_elements = await clickables.count()
                        
                        target_idx = -1
                        for i in range(total_elements):
                            elem = clickables.nth(i)
                            txt = await elem.inner_text()
                            txt_lines = [l.strip() for l in txt.strip().split("\n") if l.strip()]
                            if txt_lines and txt_lines[0] == item_name:
                                target_idx = i
                                break
                        
                        if target_idx != -1:
                            target_elem = clickables.nth(target_idx)
                            await target_elem.scroll_into_view_if_needed()
                            await target_elem.click()
                            await page.wait_for_timeout(2500)

                            # Click 'Shards' tab
                            shards_tab = page.locator("button:has-text('Shards'), div:has-text('Shards'), a:has-text('Shards')").last
                            if await shards_tab.count() > 0 and await shards_tab.is_visible():
                                await shards_tab.click()
                                await page.wait_for_timeout(2000)

                            # DOM / SVG fallback for graph values
                            dom_prices = []
                            try:
                                # Extract SVG chart node numbers
                                svg_nodes = await page.locator("svg text, svg title, [class*='recharts'], [class*='chart']").all_inner_texts()
                                for node_text in svg_nodes:
                                    cleaned = node_text.replace(",", "").strip()
                                    if cleaned.isdigit() and int(cleaned) > 0:
                                        dom_prices.append(float(cleaned))

                                # Extract page text matches
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

                            # Navigation return logic
                            if "vault" not in page.url.lower():
                                await page.go_back(wait_until="domcontentloaded")
                                await page.wait_for_timeout(2000)
                            else:
                                close_btn = page.locator("button:has-text('×'), button[aria-label='Close'], [class*='close']").first
                                if await close_btn.count() > 0 and await close_btn.is_visible():
                                    await close_btn.click()
                                else:
                                    await page.keyboard.press("Escape")
                                await page.wait_for_timeout(1000)

                    except Exception as err:
                        print(f"Error processing '{item_name}': {err}")
                        await page.keyboard.press("Escape")
                        await page.wait_for_timeout(1000)

                # Pagination handling
                if current_page < total_pages:
                    next_page_num = str(current_page + 1)
                    next_btn = page.locator(f"button:text-is('{next_page_num}'), a:text-is('{next_page_num}')").first
                    
                    if await next_btn.count() > 0:
                        await next_btn.click()
                    else:
                        arrow_btn = page.locator("button:has-text('>'), a:has-text('>')").first
                        if await arrow_btn.count() > 0:
                            await arrow_btn.click()
                    
                    # Force waiting for network idle so page 2, 3, etc. populate completely
                    try:
                        await page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:
                        await page.wait_for_timeout(3500)

        await browser.close()

    # Save output
    with open("data/trades.json", "w", encoding="utf-8") as f:
        json.dump(all_items_shard_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nDone! Saved {len(all_items_shard_data)} matched items to data/trades.json.")

if __name__ == "__main__":
    asyncio.run(scrape_shard_history())
