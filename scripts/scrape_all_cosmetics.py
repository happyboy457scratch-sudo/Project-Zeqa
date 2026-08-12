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

NAVIGATION_NOISE = [
    "Sign in with Microsoft",
    "PLAYER SAFETY",
    "Minecraft UGC Ecosystem",
    "All rights reserved",
    "Browse Servers"
]

async def scrape_vault():
    os.makedirs("data", exist_ok=True)
    all_trades = []

    async with async_playwright() as p:
        # Headless is set to True for CI/CD environments like GitHub Actions
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
        
        # Load authenticated session if stored in repository/CI
        if os.path.exists("state.json"):
            context_kwargs["storage_state"] = "state.json"

        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()

        print(f"Navigating to: {VAULT_URL}")
        await page.goto(VAULT_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        for cat in CATEGORIES:
            cat_name = cat["name"]
            total_pages = cat["pages"]

            print(f"--- Processing Category: {cat_name} ---")

            cat_tab = page.locator(f"button:has-text('{cat_name}'), a:has-text('{cat_name}')").first
            if await cat_tab.count() > 0:
                await cat_tab.click()
                await page.wait_for_timeout(2000)

            for current_page in range(1, total_pages + 1):
                # Target items specifically within the main content area
                cards = await page.locator("main [class*='item'], main [class*='card']").all()

                for card in cards:
                    text = (await card.inner_text()).strip()
                    
                    if text and not any(noise in text for noise in NAVIGATION_NOISE):
                        all_trades.append({
                            "category": cat_name,
                            "page": current_page,
                            "item_data": text
                        })

                if current_page < total_pages:
                    next_page_btn = page.locator(f"button:has-text('{current_page + 1}')").first
                    if await next_page_btn.count() > 0:
                        await next_page_btn.click()
                        await page.wait_for_timeout(1500)

        await browser.close()

    with open("data/trades.json", "w", encoding="utf-8") as f:
        json.dump(all_trades, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully collected {len(all_trades)} cosmetic items.")

if __name__ == "__main__":
    asyncio.run(scrape_vault())
