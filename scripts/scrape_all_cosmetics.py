import os
import json
import subprocess
import requests

def run_and_push_scraper():
    base_url = "https://inpvp.net/api/zeqa-cosmetics"
    
    targets = [
        ("artifact", 327),
        ("cape", 385),
        ("killphrase", 65),
        ("projectile", 7)
    ]
    
    all_trade_entries = []
    trade_index_counter = 1

    print("--- STARTING NAMED PER-ITEM SHARD AVERAGE SCRAPER & GIT PUSHER ---")

    for category, max_id in targets:
        print(f"\nProcessing category: '{category}' (IDs 1 to {max_id})...")

        for item_id in range(1, max_id + 1):
            print(f"Checking id {item_id} for {category}...")
            
            # 1. Fetch info endpoint to get the item's name
            item_name = f"Unknown {category.capitalize()} {item_id}"
            info_endpoint = f"{base_url}/{category}/{item_id}?section=info"
            try:
                info_resp = requests.get(info_endpoint, timeout=10)
                if info_resp.status_code == 200:
                    info_data = info_resp.json()
                    item_name = info_data.get("item", {}).get("name", item_name)
            except Exception:
                pass

            # 2. Fetch trades endpoint to calculate the unique average for this item
            trades_endpoint = f"{base_url}/{category}/{item_id}?section=trades"
            item_shards = []

            try:
                response = requests.get(trades_endpoint, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    trades = data.get("trades", [])
                    
                    for trade in trades:
                        all_items = trade.get("challengerItems", []) + trade.get("defenderItems", [])
                        
                        item_found = False
                        for ci in all_items:
                            if ci.get("type") == category and str(ci.get("id")) == str(item_id):
                                item_found = True
                                break
                        
                        if item_found:
                            for ci in all_items:
                                if ci.get("type") == "shard":
                                    count = ci.get("count", 0)
                                    if isinstance(count, (int, float)) and count > 0:
                                        item_shards.append(count)
            except Exception:
                pass

            # Calculate average for this specific item
            if item_shards:
                item_avg = sum(item_shards) / len(item_shards)
                item_avg_rounded = round(item_avg, 2)
            else:
                item_avg_rounded = 0.0

            # Add 10 trade entries for this specific item
            for _ in range(10):
                all_trade_entries.append({
                    "trade_index": trade_index_counter,
                    "category": category,
                    "item_id": item_id,
                    "name": item_name,
                    "shard_value": item_avg_rounded
                })
                trade_index_counter += 1

            print(f" -> '{item_name}' (ID {item_id}): Avg Shards = {item_avg_rounded}")

    # Ensure data directory exists and save to data/trades.json
    os.makedirs("data", exist_ok=True)
    output_path = os.path.abspath("data/trades.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_trade_entries, f, indent=2)

    print(f"\n==========================================")
    print(f" SCRAPING COMPLETE. FILE SAVED TO data/trades.json")
    print(f"==========================================")

    # --- AUTOMATED GIT COMMIT AND PUSH ---
    print("\nCommitting and pushing data/trades.json to GitHub...")
    try:
        # 1. Git Add
        subprocess.run(["git", "add", "data/trades.json"], check=True)
        
        # 2. Git Commit
        commit_message = "Update data/trades.json with latest cosmetic shard averages"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        
        # 3. Git Push
        subprocess.run(["git", "push"], check=True)
        
        print("Successfully committed and pushed updates to GitHub!")
    except subprocess.CalledProcessError as git_err:
        print(f"Git operation failed: {git_err}")
    except Exception as e:
        print(f"An error occurred during git automation: {e}")

if __name__ == "__main__":
    run_and_push_scraper()
