import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

VAULT_URL = "https://inpvp.net/mineville/vault?mode=pvp"
TOTAL_PAGES = 7

def parse_trade_chunks(raw_chunks, default_item_name="Unknown Item"):
    trades = []
    for chunk in raw_chunks:
        if "shards" in chunk or "trade" in chunk:
            matches = re.findall(r'\{[^{}]*"shards"[^{}]*\}', chunk)
            for m in matches:
                try:
                    clean_json = m.replace('\\"', '"')
                    data = json.loads(clean_json)
                    trade_entry = {
                        "item": str(data.get("item", default_item_name)),
                        "quantity": int(data.get("quantity", 1)),
                        "shards": str(data.get("shards", "0")),
                        "total_shards": str(data.get("total_shards", data.get("shards", "0"))),
                        "raw_trade": str(data.get("raw_trade", f"{data.get('item', default_item_name)} → {data.get('shards', '0')}"))
                    }
                    trades.append(trade_entry)
                except json.JSONDecodeError:
                    continue
    return trades

async def main():
    os.makedirs("data", exist_ok=True)
    all_trades = []
    captured_responses = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Network listener to capture trade payloads
        async def handle_response(response):
            if response.status == 200:
                try:
                    text = await response.text()
                    if "shards" in text or "trade" in text:
                        captured_responses.append(text)
                except Exception:
                    pass

        page.on("response", handle_response)

        print(f"Navigating to Vault page: {VAULT_URL}")
        await page.goto(VAULT_URL, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Loop through all 7 pages
        for current_page in range(1, TOTAL_PAGES + 1):
            print(f"\n--- Processing Page {current_page} of {TOTAL_PAGES} ---")

            # 1. Scroll down to trigger lazy loading for all items on the page
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            # 2. Click visible item cards on the current page
            items = await page.locator("div[class*='item'], div[class*='card']").all()
            print(f"Found {len(items)} items on page {current_page}")

            for idx, item in enumerate(items[:10]):  # Clicks items on current page
                try:
                    await item.click()
                    await page.wait_for_timeout(1000)

                    # Click 'Shards' button if present
                    shards_btn = page.locator("text=/Shards/i").first
                    if await shards_btn.count() > 0:
                        await shards_btn.click()
                        await page.wait_for_timeout(1500)
                except Exception as e:
                    continue

            # 3. Scroll all the way down to reach the Next Page button
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)

            # 4. Click Next Page button if not on the last page
            if current_page < TOTAL_PAGES:
                next_btn = page.locator("button:has-text('Next'), [aria-label*='next'], text='>'").first
                if await next_btn.count() > 0:
                    await next_btn.click()
                    print(f"Clicked Next Page button -> Loading page {current_page + 1}...")
                    await page.wait_for_timeout(3000)
                else:
                    print("Next Page button not found by text, searching for pagination control...")

        # Process all intercepted network chunks across all 7 pages
        for raw_text in captured_responses:
            chunks = re.findall(r'self\.__next_f\.push\((.*?)\)', raw_text)
            extracted = parse_trade_chunks(chunks if chunks else [raw_text])
            all_trades.extend(extracted)

        await browser.close()

    # Save output to data/trades.json
    output_path = "data/trades.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_trades, f, indent=2, ensure_ascii=False)

    print(f"\nFinished all pages! Saved {len(all_trades)} trade entries to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
