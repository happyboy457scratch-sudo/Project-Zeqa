import os
import json
import subprocess
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_category_items(base_url, category, max_id):
    """
    Loops through item IDs for a given category, pulls the real name/info,
    and builds the dictionary matching your target format.
    """
    category_results = []
    
    print(f"Scraping category: {category} (IDs 1 to {max_id})...")
    
    for item_id in range(1, max_id + 1):
        info_endpoint = f"{base_url}/{category}/{item_id}?section=info"
        
        try:
            response = requests.get(info_endpoint, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # Extract item details safely
                item_info = data.get("item", {})
                item_name = item_info.get("name")
                item_rarity = item_info.get("rarity", "Common") # Fallback to Common if missing
                
                if item_name:
                    formatted_category = category.capitalize()
                    
                    entry = {
                        "name": item_name,
                        "rarity": item_rarity,
                        "category": formatted_category,
                        "imageUrl": f"https://app.zeqa.net/cosmetic/preview/{category}/{item_id}.webp"
                    }
                    category_results.append(entry)
        except Exception:
            pass
            
    print(f"Finished {category}: Found {len(category_results)} valid items.")
    return category_results

def generate_cosmetics_json():
    base_url = "https://inpvp.net/api/zeqa-cosmetics"
    
    categories_to_scrape = [
        ("artifact", 230),
        ("cape", 385),
        ("killphrase", 65),
        ("projectile", 7)
    ]
    
    all_cosmetics = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_cat = {
            executor.submit(fetch_category_items, base_url, cat, max_id): cat 
            for cat, max_id in categories_to_scrape
        }
        
        for future in as_completed(future_to_cat):
            try:
                items = future.result()
                if items:
                    all_cosmetics.extend(items)
            except Exception as exc:
                print(f"Category generation error: {exc}")

    # Set path to data/cosmetics.json as requested
    target_dir = os.path.join(os.getcwd(), "data")
    output_path = os.path.join(target_dir, "cosmetics.json")
    
    os.makedirs(target_dir, exist_ok=True)
    
    # Overwrites/clears the file completely and writes the fresh bracket array list
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_cosmetics, f, indent=2)
        
    print(f"\n==========================================")
    print(f" SUCCESS! Saved {len(all_cosmetics)} items to {output_path}")
    print(f"==========================================")

    # Git Automation
    try:
        print("\n--- RUNNING GIT AUTOMATION ---")
        subprocess.run(["git", "add", output_path], check=True)
        commit_message = f"Update cosmetics.json with {len(all_cosmetics)} fresh items"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        print("Successfully committed cosmetics.json to Git!")
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e}")
    except Exception as ex:
        print(f"Error running git automation: {ex}")

if __name__ == "__main__":
    generate_cosmetics_json()
