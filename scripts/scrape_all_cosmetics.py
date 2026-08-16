import os
import json
import subprocess
import requests

def get_nexus_wing_average(base_url, item_id):
    """
    Fetches trades for Nexus Wing and calculates a basic average of all valid shard trades.
    """
    trades_endpoint = f"{base_url}/artifact/{item_id}?section=trades"
    item_shards = []
    
    try:
        response = requests.get(trades_endpoint, timeout=10)
        if response.status_code == 200:
            data = response.json()
            trades = data.get("trades", [])
            
            for trade in trades:
                challenger_items = trade.get("challengerItems", [])
                defender_items = trade.get("defenderItems", [])
                
                # Discard one-sided or empty trades
                if not challenger_items or not defender_items:
                    continue
                
                all_items = challenger_items + defender_items
                
                # Ensure Nexus Wing is part of this trade
                item_found = False
                for ci in all_items:
                    if ci.get("type") == "artifact" and str(ci.get("id")) == str(item_id):
                        item_found = True
                        break
                
                if item_found:
                    # Sum up shard counts in the trade
                    trade_shard_total = 0
                    for ci in all_items:
                        if ci.get("type") == "shard":
                            count = ci.get("count", 0)
                            if isinstance(count, (int, float)) and 0 < count < 1000000:
                                trade_shard_total += count
                                
                    if trade_shard_total > 0:
                        item_shards.append(trade_shard_total)
    except Exception as e:
        print(f"Error fetching trade data: {e}")

    if not item_shards:
        return None

    # Basic average of the graph (no right-side weighting)
    return sum(item_shards) / len(item_shards)

def run_nexus_wing_scraper():
    base_url = "https://inpvp.net/api/mineville-cosmetics" # Adjust base URL if needed based on your setup
    item_id = 105
    item_name = "Nexus Wing"
    
    print(f"Fetching data for {item_name} (ID: {item_id})...")
    
    avg_shards = get_nexus_wing_average(base_url, item_id)
    
    if avg_shards is None:
        print("No valid trades found for Nexus Wing. Defaulting to 300,000 as requested.")
        shards_str = "300000"
    else:
        shards_str = str(int(round(avg_shards)))
    
    print(f"Calculated average shards for {item_name}: {shards_str}")

    # Path to trades.json inside data/ folder
    target_dir = os.path.join(os.getcwd(), "data")
    output_path = os.path.join(target_dir, "trades.json")
    
    existing_entries = []
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing_entries = json.load(f)
            print(f"Loaded existing trades.json ({len(existing_entries)} total entries).")
        except Exception as e:
            print(f"Warning: Could not parse trades.json: {e}")

    # DELETE EVERYTHING mentioning Nexus Wing
    filtered_entries = []
    for entry in existing_entries:
        entry_item_name = str(entry.get("item", "")).lower()
        if "nexus wing" not in entry_item_name:
            filtered_entries.append(entry)
            
    print(f"Removed old Nexus Wing entries. Remaining entries: {len(filtered_entries)}")

    # Create exactly 10 new entries for Nexus Wing
    new_entries = []
    for _ in range(10):
        new_entries.append({
            "item": f"{item_id} {item_name}",
            "quantity": 1,
            "shards": shards_str,
            "total_shards": shards_str,
            "raw_trade": ""
        })

    combined_entries = filtered_entries + new_entries

    # Save back to data/trades.json
    os.makedirs(target_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(combined_entries, f, indent=2)
    print(f"Saved updated trades to {output_path}")

    # Git Automation
    try:
        print("\n--- RUNNING GIT AUTOMATION ---")
        subprocess.run(["git", "add", output_path], check=True)
        commit_message = f"Update Nexus Wing data to {shards_str} shards"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        print("Successfully committed trades.json to Git!")
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e}")
    except Exception as ex:
        print(f"Error running git automation: {ex}")

if __name__ == "__main__":
    run_nexus_wing_scraper()
