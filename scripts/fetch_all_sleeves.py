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
    driver = webdriver.Chrome(options=chrome_options)
    
    db = SessionLocal()
    
    try:
        # Get all games
        games = db.query(Game).all()
        total = len(games)
        
        print(f"\nFound {total} games to process\n")
        
        for i, game in enumerate(games, 1):
            print(f"[{i}/{total}] {game.title} (ID: {game.id})")
            
            # Delete existing sleeve data for this game
            db.query(Sleeve).filter(Sleeve.game_id == game.id).delete()
            
            # Scrape new data
            result = scrape_sleeve_data(game.bgg_id, game.title, driver)
            
            if result['status'] == 'found' and result['card_types']:
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
            else:
                game.has_sleeves = result['status']
                print(f"  ✗ {result['status']}")
            
            db.commit()
            
            # Rate limiting - be nice to BGG
            time.sleep(2)  # 2 seconds between requests
        
        print("\n" + "=" * 80)
        print("COMPLETE")
        print("=" * 80)
        
    finally:
        driver.quit()
        db.close()

if __name__ == "__main__":
    main()