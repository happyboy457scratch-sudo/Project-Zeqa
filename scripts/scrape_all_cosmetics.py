import asyncio
import json
import os
import subprocess
from playwright.async_api import async_playwright

VAULT_URL = "https://inpvp.net/mineville/vault?mode=pvp"

CATEGORIES = [
    "Artifacts", 
    "Capes", 
    "Killphrases", 
    "Projectiles"
]

def load_target_cosmetics():
    """Loads target cosmetic names from cosmetics.json or data/cosmetics.json."""
    file_path = "cosmetics.json" if os.path.exists("cosmetics.json") else "data/cosmetics.json"
    if not os.path.exists(file_path):
        print("Warning: 'cosmetics.json' not found.")
        return set()

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    target_set = set()
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                target_set.add(item.strip().lower())
            elif isinstance(item, dict):
                name = item.get("item_name") or item.get("name")
                if name:
                    target_set.add(name.strip().lower())
    elif isinstance(data, dict):
        for key in data.keys():
            target_set.add(key.strip().lower())

    print(f"Loaded {len(target_set)} unique target cosmetic names to match against.")
    return target_set

def parse_price(line):
    """Parses numbers, decimals, and values with 'K' shorthand (e.g., '1.5K' -> 1500.0)."""
    line_clean = line.strip().replace(",", "")
    if not line_clean:
        return None
    
    try:
        if line_clean.lower().endswith('k'):
            num_part = float(line_clean[:-1])
            return num_part * 1000.0
        else:
            digits_only = "".join([c for c in line_clean if c.isdigit() or c == '.'])
            if digits_only:
                return float(digits_only)
    except ValueError:
        pass
    return None

async def auto_scroll(page):
    """Scrolls down smoothly to trigger lazy-loaded cards."""
    await page.evaluate("""async () => {
        await new Promise((resolve) => {
            let totalHeight = 0;
            const distance = 400;
            const timer = setInterval(() => {
                const scrollHeight = document.body.scrollHeight;
                window.scrollBy(0, distance);
                totalHeight += distance;
                if (totalHeight >= scrollHeight) {
                    clearInterval(timer);
                    window.scrollTo(0, 0);
                    resolve();
                }
            }, 50);
        });
    }""")
    await page.wait_for_timeout(1000)

def auto_commit_and_push():
    """Commits and pushes data/trades.json to GitHub safely without throwing status 128."""
    print("\n--- Checking Git Status & Pushing to GitHub ---")
    try:
        # Check if any modified files exist
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        
        if not status.stdout.strip():
            print("No changes detected in trades.json. Skipping Git commit/push.")
            return

        subprocess.run(["git", "add", "data/trades.json"], check=True)
        subprocess.run(["git", "commit", "-m", "Auto-update shard trade data"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Successfully committed and pushed updated JSON to GitHub!")
    except subprocess.CalledProcessError as e:
        print(f"\nGit push failed ({e}).")
        print("If Git configuration is missing on this machine, run:")
        print('  git config --global user.email "your_email@example.com"')
        print('  git config --global user.name "Your Name"')
    except Exception as e:
        print(f"An unexpected error occurred during Git sync: {e}")

async def scrape_shard_history():
    os.makedirs("data", exist_ok=True)
    target_cosmetics = load_target_cosmetics()
    
    all_items_shard_data = []
    processed_item_names = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox"]
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
        try:
            await page.goto(VAULT_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            await page.goto(VAULT_URL, wait_until="load", timeout=60000)
            
        await page.wait_for_timeout(4000)

        for cat_name in CATEGORIES:
            print(f"\n================ Processing Category: {cat_name} ================")

            # Exact matching tab locator to properly register category buttons
            cat_tab = page.locator(f"button:text-is('{cat_name}'), a:text-is('{cat_name}'), [role='tab']:has-text('{cat_name}')").first
            if await cat_tab.count() > 0:
                await cat_tab.click()
                await page.wait_for_timeout(3000)

            current_page = 1
            while True:
                print(f"--- Category: {cat_name} | Page {current_page} ---")
                
                await auto_scroll(page)

                # Broader card selector for varying UI templates (Artifacts vs Killphrases)
                raw_cards = page.locator("main div[class*='grid'] > div, main [class*='cursor-pointer'], main a, main div[class*='card']")
                count = await raw_cards.count()
                matched_on_page = 0
                
                for i in range(count):
                    try:
                        card = raw_cards.nth(i)
                        text = (await card.inner_text()).strip()
                        if not text:
                            continue
                        
                        lines = [l.strip() for l in text.split("\n") if l.strip()]
                        if not lines:
                            continue
                        
                        name = lines[0]
                        name_lower = name.lower()

                        if name_lower in target_cosmetics and name not in processed_item_names:
                            processed_item_names.add(name)
                            matched_on_page += 1
                            
                            card_prices = []
                            for line in lines[1:]:
                                parsed_val = parse_price(line)
                                if parsed_val is not None and parsed_val > 0:
                                    card_prices.append(parsed_val)

                            avg_value = 0
                            if card_prices:
                                avg_value = round(sum(card_prices) / len(card_prices), 2)

                            all_items_shard_data.append({
                                "category": cat_name,
                                "item_name": name,
                                "page": current_page,
                                "average_shard_value": avg_value,
                                "shard_trade_history": card_prices
                            })
                    except Exception:
                        continue

                print(f"Captured {matched_on_page} matched item(s) from page {current_page}.")

                # Page navigation handling
                next_page_num = str(current_page + 1)
                next_btn = page.locator(f"button:text-is('{next_page_num}'), a:text-is('{next_page_num}')").first
                generic_next = page.locator("button[aria-label*='Next' i], a[aria-label*='Next' i], button:has-text('Next'), nav button:has-text('>')").first
                
                advanced = False
                
                if await next_btn.count() > 0 and await next_btn.is_visible():
                    await next_btn.scroll_into_view_if_needed()
                    await next_btn.click()
                    current_page += 1
                    advanced = True
                elif await generic_next.count() > 0 and await generic_next.is_visible():
                    is_disabled = await generic_next.get_attribute("disabled") is not None
                    aria_disabled = await generic_next.get_attribute("aria-disabled") == "true"
                    
                    if not is_disabled and not aria_disabled:
                        await generic_next.scroll_into_view_if_needed()
                        await generic_next.click()
                        current_page += 1
                        advanced = True

                if not advanced:
                    print(f"Reached the end of category: {cat_name}")
                    break
                
                await page.wait_for_timeout(3000)

        await browser.close()

    # Save to data/trades.json
    with open("data/trades.json", "w", encoding="utf-8") as f:
        json.dump(all_items_shard_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nDone! Successfully processed all categories, calculated averages, and saved {len(all_items_shard_data)} items to data/trades.json.")

    # Commit and push changes
    auto_commit_and_push()

if __name__ == "__main__":
    asyncio.run(scrape_shard_history())
