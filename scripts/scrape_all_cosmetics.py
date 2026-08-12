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

            cat_tab = page.locator(f"button:has-text('{cat_name}'), a:has-text('{cat_name}')").first
            if await cat_tab.count() > 0:
                await cat_tab.click()
                await page.wait_for_timeout(2000)

            for current_page in range(1, total_pages + 1):
                print(f"--- Category: {cat_name} | Page {current_page}/{total_pages} ---")

                # Broadened selector to target item cards within the main content region
                item_cards = await page.locator("main article, main a[href*='item'], main div[class*='group'], main div.flex-col").all()

                valid_cards = []
                for card in item_cards:
                    try:
                        text = (await card.inner_text()).strip()
                        if not text:
                            continue
                        first_line = text.split("\n")[0].strip().lower()
                        
                        if first_line not in IGNORED_TITLES and "resolved" not in first_line and "online" not in first_line and len(text) > 3:
                            # Avoid duplicates from nested locators
                            if card not in valid_cards:
                                valid_cards.append(card)
                    except Exception:
                        continue

                print(f"Found {len(valid_cards)} valid cosmetic items on page {current_page}.")

                for idx in range(len(valid_cards)):
                    try:
                        # Re-query elements to avoid stale handles
                        raw_cards = await page.locator("main article, main a[href*='item'], main div[class*='group'], main div.flex-col").all()
                        refreshed_cards = []
                        for c in raw_cards:
                            try:
                                txt = (await c.inner_text()).strip()
                                if txt:
                                    fl = txt.split("\n")[0].strip().lower()
                                    if fl not in IGNORED_TITLES and "resolved" not in fl and "online" not in fl and len(txt) > 3:
                                        if c not in refreshed_cards:
                                            refreshed_cards.append(c)
                            except Exception:
                                continue

                        if idx >= len(refreshed_cards):
                            break
                        
                        target_card = refreshed_cards[idx]
                        full_text_block = (await target_card.inner_text()).strip()
                        item_name = full_text_block.split("\n")[0].strip()

                        print(f"[{idx+1}/{len(refreshed_cards)}] Fetching Shard History for: {item_name}")

                        await target_card.click()
                        await page.wait_for_timeout(1500)

                        # Click 'Shards' tab inside modal
                        shards_tab = page.locator("button:has-text('Shards'), div:has-text('Shards')").last
                        if await shards_tab.count() > 0 and await shards_tab.is_visible():
                            await shards_tab.click()
                            await page.wait_for_timeout(1500)

                        # Extract trade rows
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

                        # Close modal
                        close_btn = page.locator("button:has-text('×'), button[aria-label='Close'], [class*='close']").first
                        if await close_btn.count() > 0 and await close_btn.is_visible():
                            await close_btn.click()
                            await page.wait_for_timeout(1000)
                        else:
                            await page.keyboard.press("Escape")
                            await page.wait_for_timeout(1000)

                    except Exception as err:
                        print(f"Error processing item index {idx}: {err}")
                        await page.keyboard.press("Escape")
                        await page.wait_for_timeout(1000)

                # Pagination
                if current_page < total_pages:
                    next_btn = page.locator(f"button:has-text('{current_page + 1}')").first
                    if await next_btn.count() > 0:
                        await next_btn.click()
                        await page.wait_for_timeout(2000)

        await browser.close()

    with open("data/trades.json", "w", encoding="utf-8") as f:
        json.dump(all_items_shard_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nSuccessfully collected Shard Trade History for {len(all_items_shard_data)} items.")

if __name__ == "__main__":
    asyncio.run(scrape_shard_history())
