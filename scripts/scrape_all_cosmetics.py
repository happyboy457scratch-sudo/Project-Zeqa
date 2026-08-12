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

async def main():
    os.makedirs("data", exist_ok=True)
    all_trades = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900}
        )
        page = await context.new_page()

        # Stealth script to prevent automated browser detection redirects
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print(f"Navigating to Vault page: {VAULT_URL}")
        response = await page.goto(VAULT_URL, wait_until="networkidle")
        
        # Verify if redirected away from vault
        if "vault" not in page.url:
            print(f"Redirect detected! Landing page was: {page.url}")
            print("Attempting forced navigation to vault sub-route...")
            await page.goto(VAULT_URL, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

        for cat in CATEGORIES:
            cat_name = cat["name"]
            total_pages = cat["pages"]

            print(f"\n==========================================")
            print(f" CATEGORY: {cat_name.upper()} ({total_pages} Pages)")
            print(f"==========================================")

            # Look specifically for category tab elements inside the Vault UI
            category_tab = page.locator(f"button:has-text('{cat_name}'), a:has-text('{cat_name}')").first

            if await category_tab.count() > 0:
                await category_tab.click(force=True)
                print(f"Clicked {cat_name} category tab!")
                await page.wait_for_timeout(2000)
            else:
                print(f"Tab for {cat_name} not found on current view. Current URL: {page.url}")

            for current_page in range(1, total_pages + 1):
                print(f"--- {cat_name} | Page {current_page} of {total_pages} ---")

                # Target ONLY actual cosmetic cards (ignoring site footer/header cards)
                cards = await page.locator("[class*='Vault_item'], [class*='CosmeticCard'], [class*='vault-card']").all()
                
                # Fallback to general grid items if specific classes aren't matched
                if len(cards) == 0:
                    cards = await page.locator("main div[class*='card'], main div[class*='item']").all()

                print(f"Extracted {len(cards)} valid cosmetic cards.")

                for card in cards:
                    try:
                        text = await card.inner_text()
                        if text and "Sign in" not in text and "PLAYER SAFETY" not in text:
                            all_trades.append({
                                "category": cat_name,
                                "page": current_page,
                                "item_data": text.strip()
                            })
                    except Exception:
                        continue

                # Pagination
                if current_page < total_pages:
                    next_btn = page.locator(f"button:has-text('{current_page + 1}')").first
                    if await next_btn.count() > 0:
                        await next_btn.click(force=True)
                        await page.wait_for_timeout(2000)

        await browser.close()

    output_path = "data/trades.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_trades, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(all_trades)} legitimate item records to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
