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

async def safe_click(element):
    """Bypasses fixed overlays or navigation headers using forced or JS clicks."""
    try:
        await element.click(timeout=4000)
    except Exception:
        try:
            await element.click(force=True, timeout=4000)
        except Exception:
            await element.evaluate("el => el.click()")

async def main():
    os.makedirs("data", exist_ok=True)
    all_trades = []
    captured_responses = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        # Listen for any JSON or streaming data coming back from the server
        async def handle_response(response):
            if response.status == 200:
                try:
                    text = await response.text()
                    if any(key in text for key in ["shards", "trade", "price", "history", "item"]):
                        captured_responses.append(text)
                except Exception:
                    pass

        page.on("response", handle_response)

        for cat in CATEGORIES:
            cat_name = cat["name"]
            total_pages = cat["pages"]

            print(f"\n==========================================")
            print(f" CATEGORY: {cat_name.upper()} ({total_pages} Pages)")
            print(f"==========================================")

            # Navigate fresh per category to clear any lingering modal/overlay state
            print(f"Navigating to Vault page...")
            await page.goto(VAULT_URL, wait_until="networkidle")
            await page.wait_for_timeout(3000)

            # Locate category tab using text containment
            category_tab = page.locator(f"text=/{cat_name}/i").first

            if await category_tab.count() > 0:
                await safe_click(category_tab)
                print(f"Clicked {cat_name} category tab!")
                await page.wait_for_timeout(2500)
            else:
                print(f"Could not find tab for {cat_name}, skipping...")
                continue

            for current_page in range(1, total_pages + 1):
                print(f"\n--- {cat_name} | Page {current_page} of {total_pages} ---")

                # Scroll down to lazy-load elements into DOM
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)

                # Collect item cards visible on page
                items = await page.locator("div[class*='item'], div[class*='card'], div[class*='cosmetic']").all()
                print(f"Found {len(items)} items on page {current_page}")

                # Extract text data directly from item cards
                for item in items:
                    try:
                        text_content = await item.inner_text()
                        if text_content.strip():
                            all_trades.append({
                                "category": cat_name,
                                "page": current_page,
                                "raw_data": text_content.strip()
                            })
                    except Exception:
                        continue

                # Click item cards to trigger network data fetches
                for item in items[:8]:
                    try:
                        await safe_click(item)
                        await page.wait_for_timeout(600)

                        shards_btn = page.locator("text=/Shards|History|Graph/i").first
                        if await shards_btn.count() > 0:
                            await safe_click(shards_btn)
                            await page.wait_for_timeout(800)

                        # Close modal/slideout if opened
                        close_btn = page.locator("button[aria-label*='Close'], button:has-text('✕')").first
                        if await close_btn.count() > 0:
                            await safe_click(close_btn)
                    except Exception:
                        continue

                # Handle pagination to next page
                if current_page < total_pages:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000)

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

        # Take a final debug screenshot for visual confirmation
        await page.screenshot(path="data/debug.png")
        print("\nSaved debug screenshot to data/debug.png")

        # Parse raw captured network responses into trades payload
        for raw in captured_responses:
            matches = re.findall(r'\{[^{}]*"(?:shards|price|trade|history|item)"[^{}]*\}', raw)
            for m in matches:
                try:
                    clean = m.replace('\\"', '"')
                    data = json.loads(clean)
                    all_trades.append(data)
                except Exception:
                    continue

        await browser.close()

    # Save output dataset
    output_path = "data/trades.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_trades, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Saved {len(all_trades)} entries to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
