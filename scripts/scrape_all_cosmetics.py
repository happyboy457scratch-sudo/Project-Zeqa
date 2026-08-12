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
        
        # Inject saved authentication state if present
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

            # Click category tab
            cat_tab = page.locator(f"button:has-text('{cat_name}'), a:has-text('{cat_name}')").first
            if await cat_tab.count() > 0:
                await cat_tab.click()
                await page.wait_for_timeout(2000)

            for current_page in range(1, total_pages + 1):
                print(f"--- Category: {cat_name} | Page {current_page}/{total_pages} ---")

                # Get all cosmetic item cards present on this page
                item_cards = await page.locator("main [class*='item'], main [class*='card']").all()

                for idx in range(len(item_cards)):
                    try:
                        # Re-fetch cards to avoid stale element handle exceptions
                        cards = await page.locator("main [class*='item'], main [class*='card']").all()
                        if idx >= len(cards):
                            break
                        
                        card = cards[idx]
                        item_name = (await card.inner_text()).split("\n")[0].strip()

                        print(f"Fetching Shard History for: {item_name}")

                        # Click item card to open detail view / modal
                        await card.click()
                        await page.wait_for_timeout(1500)

                        # Click 'Shards' tab under Trade History inside the item view
                        shards_tab = page.locator("button:has-text('Shards'), div:has-text('Shards')").last
                        if await shards_tab.count() > 0 and await shards_tab.is_visible():
                            await shards_tab.click()
                            await page.wait_for_timeout(1500)

                        # Extract historical trade records/table rows
                        trade_rows = await page.locator("[class*='history'] tr, [class*='trade'] tr, [class*='TradeHistory'] tr").all()
                        
                        item_trades = []
                        for row in trade_rows:
                            row_text = (await row.inner_text()).strip()
                            if row_text and ("Shards" in row_text or "Shard" in row_text or any(c.isdigit() for c in row_text)):
                                item_trades.append(row_text)

                        all_items_shard_data.append({
                            "category": cat_name,
                            "item_name": item_name,
                            "page": current_page,
                            "shard_trade_history": item_trades
                        })

                        # Close modal / navigate back to main grid
                        close_btn = page.locator("button:has-text('×'), button[aria-label='Close'], a:has-text('Back to Cosmetics')").first
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

                # Move to next page in pagination
                if current_page < total_pages:
                    next_btn = page.locator(f"button:has-text('{current_page + 1}')").first
                    if await next_btn.count() > 0:
                        await next_btn.click()
                        await page.wait_for_timeout(2000)

        await browser.close()

    # Save output to data/trades.json
    with open("data/trades.json", "w", encoding="utf-8") as f:
        json.dump(all_items_shard_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nSuccessfully collected Shard Trade History for {len(all_items_shard_data)} items.")

if __name__ == "__main__":
    asyncio.run(scrape_shard_history())
