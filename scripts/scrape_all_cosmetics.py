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

    print("--- STARTING NAMED PER-ITEM SHARD AVERAGE SCRAPER & GIT PUSHER ---")

    for category, max_id in targets:
        print(f"\nProcessing category: '{category}' (IDs 1 to {max_id})...")

        for item_id in range(1, max_id + 1):
            print(f"Checking id {item_id} for {category}...")
            
            # 1. Fetch info endpoint to get the item's name
            item_name = f"{item_id} {category.capitalize()}"
            info_endpoint = f"{base_url}/{category}/{item_id}?section=info"
            try:
                info_resp = requests.get(info_endpoint, timeout=10)
                if info_resp.status_code == 200:
                    info_data = info_resp.json()
                    fetched_name = info_data.get("item", {}).get("name")
                    if fetched_name:
                        item_name = f"{item_id} {fetched_name}"
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

            # Format values as strings/integers per your requested layout
            shards_str = str(int(item_avg_rounded))
            total_shards_str = shards_str # Quantity is 1, so total matches single shard value
            
            # Add 10 trade entries for this specific item with quantity fixed to 1
            for _ in range(10):
                all_trade_entries.append({
                    "item": item_name,
                    "quantity": 1,
                    "shards": shards_str,
                    "total_shards": total_shards_str,
                    "raw_trade": ""
                })

            print(f" -> '{item_name}': Shards = {shards_str}")

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
        subprocess.run(["git", "add", "data/trades.json"], check=True)
        commit_message = "Update data/trades.json with quantity 1 structured averages"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Successfully committed and pushed updates to GitHub!")
    except subprocess.CalledProcessError as git_err:
        print(f"Git operation failed: {git_err}")
    except Exception as e:
        print(f"An error occurred during git automation: {e}")

if __name__ == "__main__":
    run_and_push_scraper()
