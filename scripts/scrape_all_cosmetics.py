import asyncio
import json
import os
import re
import subprocess
from playwright.async_api import async_playwright

VAULT_URL = "https://inpvp.net/mineville/vault?mode=pvp"

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
    """Parses standard numbers, decimals, and values with 'K' shorthand (e.g., '1.5K' -> 1500.0)."""
    if not line or not isinstance(line, str):
        return None
    line_clean = line.strip().replace(",", "")
    if not line_clean:
        return None
    
    try:
        if line_clean.lower().endswith('k'):
            num_part = float(line_clean[:-1])
            return num_part * 1000.0
        else:
            match = re.search(r'\d+(?:\.\d+)?', line_clean)
            if match:
                return float(match.group(0))
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

async def extract_shard_graph_data(page):
    """
    Extracts numerical values from the Shard graph using state props, 
    SVG chart nodes, and hover tooltips.
    """
    prices = []

    # Strategy 1: Extract directly from page data state if available (Next.js / React)
    try:
        page_state = await page.evaluate("""() => {
            const el = document.getElementById('__NEXT_DATA__');
            if (!el) return null;
            try { return JSON.parse(el.textContent); } catch(e) { return null; }
        }""")
        
        if page_state:
            def search_numbers(obj):
                found = []
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if any(term in k.lower() for term in ['trade', 'shard', 'price', 'history', 'value', 'graph']):
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, (int, float)) and item > 0:
                                        found.append(float(item))
                                    elif isinstance(item, dict):
                                        val = item.get('price') or item.get('value') or item.get('shards') or item.get('amount')
                                        if isinstance(val, (int, float)) and val > 0:
                                            found.append(float(val))
                        found.extend(search_numbers(v))
                elif isinstance(obj, list):
                    for item in obj:
                        found.extend(search_numbers(item))
                return found

            extracted = search_numbers(page_state)
            if extracted:
                return extracted
    except Exception:
        pass

    # Strategy 2: Hover over SVG graph dots/circles to trigger tooltips
    try:
        chart_dots = page.locator("svg circle, svg path, [class*='recharts-dot'], [class*='chart'] circle")
        dot_count = min(await chart_dots.count(), 20)
        
        for i in range(dot_count):
            try:
                await chart_dots.nth(i).hover(timeout=500)
                await page.wait_for_timeout(100)
            except Exception:
                continue

        # Extract text values from active tooltips or chart labels
        tooltips = page.locator("[role='tooltip'], [class*='tooltip'], svg title, svg text")
        t_count = await tooltips.count()
        for i in range(t_count):
            txt = await tooltips.nth(i).inner_text()
            parsed = parse_price(txt)
            if parsed is not None and parsed > 0:
                prices.append(parsed)
    except Exception:
        pass

    # Strategy 3: Fallback DOM text scan for shard/price values
    if not prices:
        try:
            page_text = await page.inner_text()
            for line in page_text.split('\n'):
                if any(w in line.lower() for w in ['shard', 'price', 'val', 'k']):
                    parsed = parse_price(line)
                    if parsed is not None and parsed > 0:
                        prices.append(parsed)
        except Exception:
            pass

    return list(set(prices))  # Deduplicate

def auto_commit_and_push():
    """Commits and pushes data/trades.json to GitHub, ensuring git identity is set."""
    print("\n--- Checking Git Status & Pushing to GitHub ---")
    try:
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        
        if not status.stdout.strip():
            print("No changes detected in trades.json. Skipping Git commit/push.")
            return

        user_name = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True)
        user_email = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True)

        if not user_name.stdout.strip():
            print("Setting temporary Git user.name...")
            subprocess.run(["git", "config", "user.name", "Mineville Scraper Bot"], check=True)
            
        if not user_email.stdout.strip():
            print("Setting temporary Git user.email...")
            subprocess.run(["git", "config", "user.email", "bot@example.com"], check=True)

        subprocess.run(["git", "add", "data/trades.json"], check=True)
        subprocess.run(["git", "commit", "-m", "Auto-update shard trade data"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Successfully committed and pushed updated JSON to GitHub!")

    except subprocess.CalledProcessError as e:
        print(f"\nGit operation failed ({e}).")
    except Exception as e:
        print(f"An unexpected error occurred during Git sync: {e}")

async def scrape_artifact_shards():
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

        print("\n================ Processing Category: Artifacts ================")

        # Switch to Artifacts tab on vault
        cat_tab = page.locator("button, a, [role='tab']").filter(has_text=re.compile(r"Artifacts", re.I)).first
        if await cat_tab.count() > 0:
            await cat_tab.click()
            await page.wait_for_timeout(3000)

        current_page = 1
        artifact_targets = []

        # Step 1: Collect direct Artifact links/cards
        while True:
            print(f"--- Scanning Artifacts | Page {current_page} ---")
            await auto_scroll(page)

            raw_cards = page.locator("main div[class*='grid'] > div, main [class*='cursor-pointer'], main a, main div[class*='card']")
            count = await raw_cards.count()
            
            for i in range(count):
                try:
                    card = raw_cards.nth(i)
                    text = (await card.inner_text()).strip()
                    if not text:
                        continue
                    
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    matched_name = None
                    for line in lines:
                        if line.lower() in target_cosmetics:
                            matched_name = line
                            break

                    if matched_name and matched_name not in processed_item_names:
                        # Check if card is a direct link <a> tag
                        href = await card.get_attribute("href")
                        if not href:
                            link_elem = card.locator("a").first
                            if await link_elem.count() > 0:
                                href = await link_elem.get_attribute("href")

                        full_url = None
                        if href:
                            full_url = href if href.startswith("http") else f"https://inpvp.net{href}"

                        artifact_targets.append({
                            "name": matched_name,
                            "card_index": i,
                            "url": full_url,
                            "page_num": current_page
                        })
                        processed_item_names.add(matched_name)
                except Exception:
                    continue

            # Pagination advancement
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
                break
            await page.wait_for_timeout(3000)

        print(f"\nFound {len(artifact_targets)} target Artifacts to inspect directly.")

        # Step 2: Visit each artifact page, click "Shards", and extract graph values
        for idx, item in enumerate(artifact_targets, start=1):
            item_name = item["name"]
            item_url = item["url"]
            print(f"[{idx}/{len(artifact_targets)}] Processing Artifact: '{item_name}'")

            try:
                if item_url:
                    await page.goto(item_url, wait_until="domcontentloaded", timeout=30000)
                else:
                    # Fallback navigation if direct href wasn't present
                    print(f"  Navigating via vault click for {item_name}...")
                    await page.goto(VAULT_URL, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000)
                    card = page.locator(f"main :has-text('{item_name}')").last
                    await card.click()

                await page.wait_for_timeout(2000)

                # Immediately click the "Shards" button
                shards_btn = page.locator("button, a, [role='tab']").filter(has_text=re.compile(r"^shards$", re.I)).first
                if await shards_btn.count() > 0:
                    await shards_btn.click()
                    print("  Clicked 'Shards' button!")
                    await page.wait_for_timeout(2000)  # Wait for graph to load
                else:
                    # Fallback search for any button containing 'Shard'
                    alt_shards = page.locator("button:has-text('Shard'), a:has-text('Shard')").first
                    if await alt_shards.count() > 0:
                        await alt_shards.click()
                        print("  Clicked fallback 'Shard' button!")
                        await page.wait_for_timeout(2000)

                # Extract graph values
                graph_prices = await extract_shard_graph_data(page)
                avg_value = round(sum(graph_prices) / len(graph_prices), 2) if graph_prices else 0.0

                print(f"  Extracted {len(graph_prices)} graph points. Avg Shard Value: {avg_value}")

                all_items_shard_data.append({
                    "category": "Artifacts",
                    "item_name": item_name,
                    "url": item_url or page.url,
                    "average_shard_value": avg_value,
                    "shard_trade_history": graph_prices
                })

            except Exception as e:
                print(f"  Failed to process {item_name}: {e}")
                all_items_shard_data.append({
                    "category": "Artifacts",
                    "item_name": item_name,
                    "url": item_url,
                    "average_shard_value": 0.0,
                    "shard_trade_history": []
                })

        await browser.close()

    # Save to data/trades.json
    with open("data/trades.json", "w", encoding="utf-8") as f:
        json.dump(all_items_shard_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nDone! Successfully processed Artifacts and saved {len(all_items_shard_data)} items to data/trades.json.")

    auto_commit_and_push()

if __name__ == "__main__":
    asyncio.run(scrape_artifact_shards())
