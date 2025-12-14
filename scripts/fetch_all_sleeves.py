"""
One-time migration script to fetch sleeve data for all existing games
Re-runs will update existing sleeve data
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal
from backend.models import Game, Sleeve
from backend.services.sleeve_scraper import scrape_sleeve_data
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def main():
    print("=" * 80)
    print("BULK SLEEVE DATA FETCH")
    print("=" * 80)
    
    # Setup Selenium
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # Point to chromium binary (GitHub Actions installs chromium-browser, not chrome)
    chrome_options.binary_location = '/usr/bin/chromium-browser'
    driver = webdriver.Chrome(options=chrome_options)
    
    db = SessionLocal()
    
    try:
        # Get all games with BGG IDs (can't scrape without BGG ID)
        games = db.query(Game).filter(Game.bgg_id.isnot(None)).all()
        total = len(games)

        print(f"\nFound {total} games with BGG IDs to process\n")

        for i, game in enumerate(games, 1):
            print(f"[{i}/{total}] {game.title} (BGG ID: {game.bgg_id})")

            try:
                # Delete existing sleeve data for this game
                db.query(Sleeve).filter(Sleeve.game_id == game.id).delete()

                # Scrape new data
                result = scrape_sleeve_data(game.bgg_id, game.title, driver)

                if result and result.get('status') == 'found' and result.get('card_types'):
                    # Save sleeve data
                    for card_type in result['card_types']:
                        sleeve = Sleeve(
                            game_id=game.id,
                            card_name=card_type.get('name'),
                            width_mm=card_type['width_mm'],
                            height_mm=card_type['height_mm'],
                            quantity=card_type['quantity'],
                            notes=result.get('notes')
                        )
                        db.add(sleeve)

                    game.has_sleeves = 'found'
                    print(f"  ✓ Found {len(result['card_types'])} sleeve type(s)")
                elif result:
                    game.has_sleeves = result.get('status', 'error')
                    print(f"  ✗ {result.get('status', 'unknown')}")
                else:
                    game.has_sleeves = 'error'
                    print(f"  ✗ error: scraper returned None")

                db.commit()

            except Exception as e:
                print(f"  ✗ ERROR: {str(e)}")
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
        driver.quit()
        db.close()

if __name__ == "__main__":
    main()