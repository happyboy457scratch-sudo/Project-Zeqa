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

# Words to ignore so the bot doesn't try to click navigation menus
IGNORED_TITLES = {
    "overview", "community", "bundles", "vault", "hall of fame", 
    "cities", "item market", "trades", "pvp leaderboards", "staff", 
    "orebits", "profile", "support", "ban appeal", "teams", "giveaways",
    "genwars", "airdrops", "megasmp", "oneblock online", "what are orebits?"
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
        await page.goto(VAULT_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        for cat in CATEGORIES:
            cat_name = cat["name"]
            total_pages = cat["pages"]

            print(f"\n================ Processing Category: {cat_name} ================")

            # Click the category tab
            cat_tab = page.locator(f"button:has-text('{cat_name}'), a:has-text('{cat_name}')").first
            if await cat_tab.count() > 0:
                await cat_tab.click()
                await page.wait_for_timeout(3000)

            for current_page in range(1, total_pages + 1):
                print(f"--- Category: {cat_name} | Page {current_page}/{total_pages} ---")
                await page.wait_for_timeout(2000) # Give grid time to load

                # PASS 1: Collect Exact Item Names
                raw_cards = await page.locator("main div[class*='cursor-pointer'], main div.flex.flex-col, main a").all()
                valid_item_names = []
                
                for card in raw_cards:
                    try:
                        text = (await card.inner_text()).strip()
                        if not text:
                            continue
                        
                        # The item name is usually the very first line of text in the card block
                        first_line = text.split("\n")[0].strip()
                        fl_lower = first_line.lower()
                        
                        # If it's a navigation button, support ticket, or too short, skip it
                        if fl_lower in IGNORED_TITLES or "resolved" in fl_lower or "online" in fl_lower or len(first_line) < 3:
                            continue
                        
                        if first_line not in valid_item_names:
                            valid_item_names.append(first_line)
                    except Exception:
                        continue

                print(f"Found {len(valid_item_names)} items to process on page {current_page}.")

                # PASS 2: Search the DOM for the exact names and click them
                for idx, item_name in enumerate(valid_item_names):
                    try:
                        print(f"[{idx+1}/{len(valid_item_names)}] Fetching: {item_name}")

                        # Locate by exact text match within the main block, preventing index shift issues
                        target_card = page.locator("main").get_by_text(item_name, exact=True).first
                        
                        if await target_card.count() > 0 and await target_card.is_visible():
                            await target_card.click()
                            await page.wait_for_timeout(1500)
                        else:
                            print(f"  -> Could not locate card for {item_name}, skipping.")
                            continue

                        # Click 'Shards' tab inside modal
                        shards_tab = page.locator("button:has-text('Shards'), div:has-text('Shards')").last
                        if await shards_tab.count() > 0 and await shards_tab.is_visible():
                            await shards_tab.click()
                            await page.wait_for_timeout(1500)

                        # Extract trade rows from modal history
                        trade_rows = await page.locator("[class*='modal'] tr, [class*='history'] tr, [class*='trade-row'], [class*='overflow-x-auto'] div").all()
                        
                        item_trades = []
                        for row in trade_rows:
                            row_text = (await row.inner_text()).strip()
                            if row_text and ("Shards" in row_text or "Shard" in row_text):
                                item_trades.append(row_text)

                        all_items_shard_data.append({
                            "category": cat_name,
                            "item_name": item_name,
                            "page": current_page,
                            "shard_trade_history": item_trades
                        })

                        # Close modal gracefully
                        close_btn = page.locator("button:has-text('×'), button[aria-label='Close'], [class*='close']").first
                        if await close_btn.count() > 0 and await close_btn.is_visible():
                            await close_btn.click()
                            await page.wait_for_timeout(1000)
                        else:
                            await page.keyboard.press("Escape")
                            await page.wait_for_timeout(1000)

                    except Exception as err:
                        print(f"Error processing item '{item_name}': {err}")
                        await page.keyboard.press("Escape")
                        await page.wait_for_timeout(1000)

                # Pagination: Move to the next page
                if current_page < total_pages:
                    next_page_num = current_page + 1
                    next_btn = page.locator(f"button:has-text('{next_page_num}'), a:has-text('{next_page_num}')").first
                    if await next_btn.count() > 0:
                        await next_btn.click()
                        await page.wait_for_timeout(2500)
                    else:
                        print(f"Warning: Could not locate pagination button for page {next_page_num}")

        await browser.close()

    with open("data/trades.json", "w", encoding="utf-8") as f:
        json.dump(all_items_shard_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nSuccessfully collected Shard Trade History for {len(all_items_shard_data)} items.")

if __name__ == "__main__":
    asyncio.run(scrape_shard_history())
