import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

VAULT_URL = "https://inpvp.net/mineville/vault?mode=pvp"

CATEGORIES = {
    "Artifacts": 7,
    "Capes": 8,
    "Killphrases": 2,
    "Projectiles": 1
}

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

        for category_name, total_pages in CATEGORIES.items():
            print(f"\n==========================================")
            print(f" CATEGORY: {category_name.upper()} ({total_pages} Pages)")
            print(f"==========================================")

            try:
                # 1. Flexible Category Tab Locator
                category_tab = page.locator("button, [role='tab'], div[class*='tab'], div[class*='category'], a").filter(has_text=re.compile(category_name, re.I)).first
                
                if await category_tab.count() > 0:
                    await category_tab.click()
                    print(f"Clicked {category_name} tab!")
                    await page.wait_for_timeout(2000)
                else:
                    # Fallback: Click text node directly if tab wrapper isn't caught
                    text_node = page.locator(f"text=/{category_name}/i").first
                    if await text_node.count() > 0:
                        await text_node.click()
                        print(f"Clicked {category_name} via text fallback!")
                        await page.wait_for_timeout(2000)
                    else:
                        print(f"Could not find tab for {category_name}, skipping...")
                        continue

            except Exception as e:
                print(f"Error switching to category {category_name}: {e}")
                continue

            # 2. Loop through pages for this category
            for current_page in range(1, total_pages + 1):
                print(f"\n--- {category_name} | Page {current_page} of {total_pages} ---")

                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)

                items = await page.locator("div[class*='item'], div[class*='card']").all()
                print(f"Found {len(items)} items on page {current_page}")

                for idx, item in enumerate(items[:10]):
                    try:
                        await item.click()
                        await page.wait_for_timeout(800)

                        shards_btn = page.locator("text=/Shards/i").first
                        if await shards_btn.count() > 0:
                            await shards_btn.click()
                            await page.wait_for_timeout(1200)
                    except Exception:
                        continue

                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)

                if current_page < total_pages:
                    next_btn = page.locator("button, a").filter(has_text=re.compile(r"Next|>", re.I)).first
                    if await next_btn.count() > 0:
                        await next_btn.click()
                        print(f"Clicked Next -> Loading page {current_page + 1}...")
                        await page.wait_for_timeout(2500)
                    else:
                        print(f"Next button not found on page {current_page}!")

        for raw_text in captured_responses:
            chunks = re.findall(r'self\.__next_f\.push\((.*?)\)', raw_text)
            extracted = parse_trade_chunks(chunks if chunks else [raw_text])
            all_trades.extend(extracted)

        await browser.close()

    output_path = "data/trades.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_trades, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Successfully scraped across all categories. Saved {len(all_trades)} entries to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
