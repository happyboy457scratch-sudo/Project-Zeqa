import asyncio
import json
import os
from playwright.async_api import async_playwright

VAULT_URL = "https://inpvp.net/mineville/vault?mode=pvp"

CATEGORIES = [
    {"name": "Artifacts", "pages": 7},
    {"name": "Capes", "pages": 8},
    {"name": "Killphrases", "pages": 2},
    {"name": "Projectiles", "pages": 1}
]

IGNORED_TITLES = {
    "overview", "community", "bundles", "vault", "hall of fame", 
    "cities", "item market", "trades", "pvp leaderboards", "staff", 
    "orebits", "profile", "support", "ban appeal", "teams", "giveaways",
    "genwars", "airdrops", "megasmp", "oneblock online", "what are orebits?",
    "mineville zeqa", "back to general discussion", "sign in"
}

async def scrape_shard_history():
    os.makedirs("data", exist_ok=True)
    all_items_shard_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
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
                await page.wait_for_timeout(2500)

                # PASS 1: Identify True Cosmetic Items
                raw_cards = page.locator("main [class*='cursor-pointer'], main a")
                count = await raw_cards.count()
                valid_item_names = []
                
                for i in range(count):
                    try:
                        card = raw_cards.nth(i)
                        if not await card.is_visible():
                            continue
                            
                        text = (await card.inner_text()).strip()
                        if not text:
                            continue
                        
                        lines = [l.strip() for l in text.split("\n") if l.strip()]
                        if len(lines) < 2:
                            continue
                        
                        name = lines[0]
                        name_lower = name.lower()
                        
                        if name.startswith("#") or not name[0].isupper():
                            continue
                        if name_lower in IGNORED_TITLES:
                            continue
                        if any(x in name_lower for x in ["resolved", "open now", "online", "general discussion"]):
                            continue
                        
                        if name not in valid_item_names:
                            valid_item_names.append(name)
                    except Exception:
                        continue

                print(f"Found {len(valid_item_names)} true cosmetic items on page {current_page}.")

                # PASS 2: Click and Verify URL
                for idx, item_name in enumerate(valid_item_names):
                    try:
                        print(f"[{idx+1}/{len(valid_item_names)}] Fetching: {item_name}")

                        clickables_locator = page.locator("main [class*='cursor-pointer'], main a")
                        total_elements = await clickables_locator.count()
                        
                        target_idx = -1
                        for i in range(total_elements):
                            elem = clickables_locator.nth(i)
                            if await elem.is_visible():
                                txt = await elem.inner_text()
                                txt_lines = [l.strip() for l in txt.strip().split("\n") if l.strip()]
                                if txt_lines and txt_lines[0] == item_name:
                                    target_idx = i
                                    break
                        
                        if target_idx != -1:
                            await clickables_locator.nth(target_idx).click()
                            await page.wait_for_timeout(2000)
                            
                            current_url = page.url.lower()

                            # YOUR IDEA: Verify if current URL is a valid cosmetic page or stayed on vault modal
                            is_valid_item_page = (
                                "inpvp.net/mineville/cosmetic" in current_url 
                                or "inpvp.net/mineville/item" in current_url
                                or "vault" in current_url
                            )

                            if not is_valid_item_page:
                                print(f"  -> Navigated to unintended page ({page.url}). Reverting...")
                                await page.go_back(wait_until="domcontentloaded")
                                await page.wait_for_timeout(2000)
                                continue

                            # Locate and click 'Shards' tab on the page or modal
                            shards_tab = page.locator("button:has-text('Shards'), div:has-text('Shards'), a:has-text('Shards')").last
                            if await shards_tab.count() > 0 and await shards_tab.is_visible():
                                await shards_tab.click()
                                await page.wait_for_timeout(1500)

                                trade_rows = await page.locator("tr, [class*='trade-row'], [class*='overflow-x-auto'] div, table div").all()
                                item_trades = []
                                for row in trade_rows:
                                    row_text = (await row.inner_text()).strip()
                                    if row_text and ("Shards" in row_text or "Shard" in row_text or "Bought" in row_text or "Sold" in row_text):
                                        item_trades.append(row_text)

                                all_items_shard_data.append({
                                    "category": cat_name,
                                    "item_name": item_name,
                                    "page": current_page,
                                    "shard_trade_history": item_trades
                                })
                                print(f"  -> Scraped shard history for {item_name}!")
                            else:
                                print(f"  -> No 'Shards' tab found for {item_name}.")

                            # Return back if navigated to separate URL, or close modal if stayed on vault
                            if "vault" not in current_url:
                                await page.go_back(wait_until="domcontentloaded")
                                await page.wait_for_timeout(2000)
                            else:
                                close_btn = page.locator("button:has-text('×'), button[aria-label='Close'], [class*='close']").first
                                if await close_btn.count() > 0 and await close_btn.is_visible():
                                    await close_btn.click()
                                else:
                                    await page.keyboard.press("Escape")
                                await page.wait_for_timeout(1000)
                        else:
                            print(f"  -> Could not locate target element for {item_name}, skipping.")

                    except Exception as err:
                        print(f"Error processing item '{item_name}': {err}")
                        await page.keyboard.press("Escape")
                        await page.wait_for_timeout(1000)

                # Next page navigation
                if current_page < total_pages:
                    next_page_num = str(current_page + 1)
                    next_btn = page.locator(f"button:text-is('{next_page_num}'), a:text-is('{next_page_num}')").first
                    
                    if await next_btn.count() > 0:
                        await next_btn.click()
                        await page.wait_for_timeout(3000)
                    else:
                        arrow_btn = page.locator("button:has-text('>')").first
                        if await arrow_btn.count() > 0:
                            await arrow_btn.click()
                            await page.wait_for_timeout(3000)
                        else:
                            print(f"Warning: Could not locate pagination button for page {next_page_num}")

        await browser.close()

    with open("data/trades.json", "w", encoding="utf-8") as f:
        json.dump(all_items_shard_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nSuccessfully collected Shard Trade History for {len(all_items_shard_data)} items.")

if __name__ == "__main__":
    asyncio.run(scrape_shard_history())
