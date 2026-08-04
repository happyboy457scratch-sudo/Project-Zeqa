import time
import subprocess

LOOP_INTERVAL_SECONDS = 300  # 5 minutes

def main():
    print("==========================================")
    print("Mineville Scraper Loop Active")
    print(f"Executing scrape_trades.py every {LOOP_INTERVAL_SECONDS} seconds")
    print("==========================================")

    while True:
        start_time = time.time()
        try:
            print("\nStarting scrape cycle...")
            subprocess.run(["python", "scrape_trades.py"], check=True)
        except Exception as e:
            print(f"Error during execution: {e}")

        elapsed = time.time() - start_time
        sleep_duration = max(0, LOOP_INTERVAL_SECONDS - elapsed)
        
        print(f"Sleeping for {int(sleep_duration)} seconds until next run...")
        time.sleep(sleep_duration)

if __name__ == "__main__":
    main()
