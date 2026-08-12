import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

VAULT_URL = "https://inpvp.net/mineville/vault?mode=pvp"

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
        # Launch headless Chromium browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Intercept network responses fired by client-side clicks
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

        # Give client-side JS time to hydrate
        await page.wait_for_timeout(3000)

        # -------------------------------------------------------------
        # ACTIVE CLICK SEQUENCE
        # -------------------------------------------------------------
        try:
            print("Executing browser interactions...")

            # 1. Wait for and click the category (e.g., Artifacts)
            await page.wait_for_selector("text='Artifacts'", timeout=10000)
            await page.click("text='Artifacts'")
            print("Clicked Artifacts tab!")
            await page.wait_for_timeout(1500)

            # 2. Click a specific item (e.g., Antler or Cat Mask)
            # You can also use page.locator("div").filter(has_text=...).first.click()
            await page.click("text='Antler'")
            print("Clicked Antler!")
            await page.wait_for_timeout(1500)

            # 3. Click the 'Shards' button to trigger the graph/trade data
            await page.click("text='Shards'")
            print("Clicked Shards graph button!")

            # Pause to let the network response complete
            await page.wait_for_timeout(3000)

        except Exception as e:
            print(f"Interaction warning: {e}")

        # Process all intercepted data streams
        for raw_text in captured_responses:
            chunks = re.findall(r'self\.__next_f\.push\((.*?)\)', raw_text)
            extracted = parse_trade_chunks(chunks if chunks else [raw_text])
            all_trades.extend(extracted)

        await browser.close()

    # Save output to data/trades.json
    output_path = "data/trades.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_trades, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Saved {len(all_trades)} trade entries to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
