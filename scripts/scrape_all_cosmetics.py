import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

VAULT_URL = "https://inpvp.net/mineville/vault?mode=pvp"

# Tradeable categories only
CATEGORIES = [
    {"name": "Artifacts", "pages": 7},
    {"name": "Capes", "pages": 8},
    {"name": "Killphrases", "pages": 2},
    {"name": "Projectiles", "pages": 1}
]

def parse_trade_chunks(raw_chunks):
    trades = []
    for chunk in raw_chunks:
        matches = re.findall(r'\{[^{}]*"(?:shards|price|trade|history|item)"[^{}]*\}', chunk)
        for m in matches:
            try:
                clean_json = m.replace('\\"', '"')
                data = json.loads(clean_json)
                trade_entry = {
                    "item": str(data.get("item", data.get("name", "Unknown Cosmetic"))),
                    "quantity": int(data.get("quantity", 1)),
                    "shards": str(data.get("shards", data.get("price", "0"))),
                    "total_shards": str(data.get("total_shards", data.get("shards", "0"))),
                    "raw_trade": str(data.get("raw_trade", f"{data.get('item', 'Item')} → {data.get('shards', '0')}"))
                }
                trades.append(trade_entry)
            except json.JSONDecodeError:
                continue
    return trades

async def safe_click(element):
    """Bypasses fixed overlays or navigation headers using forced clicks."""
    try:
        await element.click(timeout=3000)
    except Exception:
        try:
            await element.click(force=True, timeout=3000)
        except Exception:
            await element.evaluate("el => el.click()")

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
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type or "text/x-component" in content_type:
                        text = await response.text()
                        captured_responses.append(text)
                except Exception:
                    pass

        page.on("response", handle_response)

        print(f"Navigating to Vault page: {VAULT_URL}")
        await page.goto(VAULT_URL, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        for cat in CATEGORIES:
            cat_name = cat["name"]
            total_pages = cat["pages"]

            print(f"\n==========================================")
            print(f" CATEGORY: {cat_name.upper()} ({total_pages} Pages)")
            print(f"==========================================")

            category_tab = page.locator("button, div").filter(
                has_text=re.compile(rf"\b{cat_name}\b", re.I)
            ).first

            if await category_tab.count() > 0:
                await safe_click(category_tab)
                print(f"Clicked {cat_name} category button!")
                await page.wait_for_timeout(2000)
            else:
                print(f"Could not find category button for {cat_name}, skipping...")
                continue

            for current_page in range(1, total_pages + 1):
                print(f"\n--- {cat_name} | Page {current_page} of {total_pages} ---")

                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)

                items = await page.locator("div[class*='item'], div[class*='card'], div[class*='cosmetic']").all()
                print(f"Found {len(items)} items on page {current_page}")

                for item in items[:10]:
                    try:
                        await safe_click(item)
                        await page.wait_for_timeout(800)

                        shards_btn = page.locator("text=/Shards|History|Graph/i").first
                        if await shards_btn.count() > 0:
                            await safe_click(shards_btn)
                            await page.wait_for_timeout(1200)

                        close_btn = page.locator("button[aria-label*='Close'], button:has-text('✕')").first
                        if await close_btn.count() > 0:
                            await safe_click(close_btn)
                    except Exception:
                        continue

                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)

                if current_page < total_pages:
                    next_page_num = current_page + 1
                    next_btn = page.locator(f"button:has-text('{next_page_num}'), a:has-text('{next_page_num}')").first
                    
                    if await next_btn.count() == 0:
                        next_btn = page.locator("button:has(svg), a:has(svg)").last

                    if await next_btn.count() > 0:
                        await safe_click(next_btn)
                        print(f"Clicked Page {next_page_num} button!")
                        await page.wait_for_timeout(2500)
                    else:
                        print(f"Next button for page {next_page_num} not found.")

        for raw_text in captured_responses:
            extracted = parse_trade_chunks([raw_text])
            all_trades.extend(extracted)

        await browser.close()

    output_path = "data/trades.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_trades, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Scraped tradeable categories. Saved {len(all_trades)} entries to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
