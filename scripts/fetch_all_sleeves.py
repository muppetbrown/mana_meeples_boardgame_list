"""
One-time migration script to fetch sleeve data for all existing games
Re-runs will update existing sleeve data
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("DEBUG: Starting imports...")
from backend.database import SessionLocal
print("DEBUG: Imported SessionLocal")
from backend.models import Game, Sleeve
print("DEBUG: Imported models")
from backend.services.sleeve_scraper import scrape_sleeve_data
print("DEBUG: Imported scraper")
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
print("DEBUG: Imported Selenium")
import time
import threading
print("DEBUG: All imports complete")


class TimeoutException(Exception):
    pass


def scrape_with_timeout(bgg_id, game_title, driver, timeout_seconds=30):
    """
    Scrape with hard timeout using threading to prevent hanging
    Threading is more reliable than signal.SIGALRM for blocking I/O operations
    """
    result_container = {'result': None, 'exception': None}

    def run_scrape():
        try:
            result_container['result'] = scrape_sleeve_data(bgg_id, game_title, driver)
        except Exception as e:
            result_container['exception'] = e

    thread = threading.Thread(target=run_scrape, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        # Thread is still running - timeout occurred
        print(f"  ⏱ Timeout after {timeout_seconds}s - thread still running", flush=True)
        # Note: We can't kill the thread, but making it daemon means it won't prevent exit
        # We'll need to restart the driver to recover
        return {'status': 'timeout', 'card_types': [], 'notes': None, 'restart_driver': True}

    if result_container['exception']:
        raise result_container['exception']

    return result_container['result']

def create_driver():
    """Create a new Selenium WebDriver instance"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    # Point to chromium binary (GitHub Actions installs chromium-browser, not chrome)
    chrome_options.binary_location = '/usr/bin/chromium-browser'
    return webdriver.Chrome(options=chrome_options)


def main():
    print("=" * 80)
    print("BULK SLEEVE DATA FETCH")
    print("=" * 80)

    # Setup Selenium
    driver = create_driver()

    db = SessionLocal()

    try:
        # Get all games with BGG IDs (can't scrape without BGG ID)
        games = db.query(Game).filter(Game.bgg_id.isnot(None)).all()
        total = len(games)

        print(f"\nFound {total} games with BGG IDs to process\n")

        for i, game in enumerate(games, 1):
            # Periodically restart driver to prevent resource buildup (every 50 games)
            if i > 1 and (i - 1) % 50 == 0:
                print(f"  🔄 Periodic driver restart (every 50 games)...", flush=True)
                try:
                    driver.quit()
                except:
                    pass
                driver = create_driver()
                print(f"  ✓ Driver restarted", flush=True)

            print(f"[{i}/{total}] {game.title} (BGG ID: {game.bgg_id})", flush=True)

            try:
                # Delete existing sleeve data for this game
                db.query(Sleeve).filter(Sleeve.game_id == game.id).delete()

                # Scrape new data with hard timeout (30 seconds per game)
                result = scrape_with_timeout(game.bgg_id, game.title, driver, timeout_seconds=30)

                # If timeout occurred, restart the driver
                if result and result.get('restart_driver'):
                    print(f"  🔄 Restarting driver after timeout...", flush=True)
                    try:
                        driver.quit()
                    except:
                        pass  # Ignore errors when quitting hung driver
                    driver = create_driver()
                    print(f"  ✓ Driver restarted", flush=True)

                if result and result.get('status') == 'found' and result.get('card_types'):
                    # Save sleeve data
                    for card_type in result['card_types']:
                        # Ensure quantity is never None (fallback to 0)
                        quantity = card_type.get('quantity') or 0
                        sleeve = Sleeve(
                            game_id=game.id,
                            card_name=card_type.get('name'),
                            width_mm=card_type['width_mm'],
                            height_mm=card_type['height_mm'],
                            quantity=quantity,
                            notes=result.get('notes')
                        )
                        db.add(sleeve)

                    game.has_sleeves = 'found'
                    print(f"  ✓ Found {len(result['card_types'])} sleeve type(s)", flush=True)
                elif result:
                    game.has_sleeves = result.get('status', 'error')
                    status_msg = result.get('status', 'unknown')
                    print(f"  ✗ {status_msg}", flush=True)
                else:
                    game.has_sleeves = 'error'
                    print(f"  ✗ error: scraper returned None", flush=True)

                db.commit()

            except Exception as e:
                print(f"  ✗ ERROR: {str(e)}", flush=True)
                game.has_sleeves = 'error'
                db.rollback()  # Rollback failed transaction
                db.commit()    # Commit the error status
                # Continue with next game instead of crashing

            # Rate limiting - be nice to BGG
            time.sleep(1)  # 1 second between requests (faster processing)

        print("\n" + "=" * 80)
        print("COMPLETE")
        print("=" * 80)

    finally:
        try:
            driver.quit()
        except:
            pass  # Ignore errors on final cleanup
        db.close()

if __name__ == "__main__":
    main()