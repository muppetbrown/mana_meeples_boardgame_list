#!/usr/bin/env python3
"""
Test scraper for BGG sleeve data using Selenium for JavaScript-rendered pages
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time


def scrape_sleeve_data(bgg_id, game_name=None, driver=None):
    """
    Scrape sleeve information from BGG's sleeve page
    
    Args:
        bgg_id: BoardGameGeek game ID
        game_name: Game name (will be slugified for URL)
        driver: Selenium WebDriver instance (optional, will create if None)
        
    Returns:
        dict with sleeve data or None if no data found
    """
    # Create slug from game name (spaces to dashes, lowercase)
    if game_name:
        slug = game_name.lower().replace(' ', '-').replace(':', '').replace("'", '')
        url = f"https://boardgamegeek.com/boardgame/{bgg_id}/{slug}/sleeves"
    else:
        url = f"https://boardgamegeek.com/boardgame/{bgg_id}/sleeves"
    
    print(f"Fetching sleeve data from: {url}")
    
    close_driver = False
    if driver is None:
        # Create a new driver
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(options=chrome_options)
        close_driver = True
    
    try:
        # Load the page
        driver.get(url)
        
        # Wait for the Angular app to load and render the sleeve visualizer
        wait = WebDriverWait(driver, 10)
        
        # Wait for the card list to appear
        try:
            card_list = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "sleeve-visualizer__card-list"))
            )
        except TimeoutException:
            print("  ✗ Timeout waiting for sleeve data to load (page might not have sleeve info)")
            return None
        
        # Give Angular a moment to fully render
        time.sleep(1)
        
        # Find all card elements
        cards = driver.find_elements(By.CSS_SELECTOR, "li.sleeve-visualizer__card")
        
        if not cards:
            print("  ✗ No card types found")
            return None
        
        card_types = []
        
        for card in cards:
            try:
                # Get dimensions
                dimensions_btn = card.find_element(By.CLASS_NAME, "sleeve-visualizer__card-dimensions")
                dimensions = dimensions_btn.text.strip()
                
                # Get quantity
                quantity = None
                try:
                    quantity_elem = card.find_element(By.CLASS_NAME, "sleeve-visualizer__card-quantity")
                    qty_text = quantity_elem.text.strip()
                    # Extract number from "QTY 73" or "Qty 73"
                    quantity = int(qty_text.upper().replace('QTY', '').strip())
                except NoSuchElementException:
                    pass
                
                # Get card name
                card_name = None
                try:
                    name_elem = card.find_element(By.CLASS_NAME, "sleeve-visualizer__card-name")
                    name_span = name_elem.find_element(By.TAG_NAME, "span")
                    card_name = name_span.text.strip()
                except NoSuchElementException:
                    pass
                
                # Parse dimensions (e.g., "44 x 68" -> width: 44, height: 68)
                try:
                    width, height = dimensions.split('x')
                    width = int(width.strip())
                    height = int(height.strip())
                except:
                    width = None
                    height = None
                
                card_types.append({
                    'name': card_name,
                    'dimensions': dimensions,
                    'width_mm': width,
                    'height_mm': height,
                    'quantity': quantity
                })
            except Exception as e:
                print(f"  Warning: Error parsing card element: {e}")
                continue
        
        if not card_types:
            print("  ✗ No card types parsed successfully")
            return None
        
        # Try to get notes if available
        notes = None
        try:
            notes_elem = driver.find_element(By.CLASS_NAME, "sleeve-visualizer__overview-notes__primary")
            notes = notes_elem.text.strip()
        except NoSuchElementException:
            pass
        
        result = {
            'bgg_id': bgg_id,
            'card_types': card_types,
            'total_cards': sum(ct['quantity'] for ct in card_types if ct['quantity']),
            'notes': notes
        }
        
        print(f"  ✓ Found {len(card_types)} card type(s)")
        return result
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        if close_driver:
            driver.quit()


def main():
    """Test the scraper with a few games"""
    
    print("=" * 80)
    print("BGG SLEEVE DATA SCRAPER - TEST VERSION (Selenium)")
    print("=" * 80)
    print()
    
    # Setup Selenium driver once for all tests
    print("Setting up Chrome WebDriver...")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("✓ WebDriver initialized\n")
    except Exception as e:
        print(f"✗ Failed to initialize WebDriver: {e}")
        print("\nMake sure you have Chrome and chromedriver installed:")
        print("  pip install selenium")
        print("  Download chromedriver: https://chromedriver.chromium.org/downloads")
        return
    
    # Test games
    test_games = [
        (173346, "7 Wonders Duel"),
        (68448, "7 Wonders"),
        (174430, "Gloomhaven"),
    ]
    
    results = []
    
    try:
        for bgg_id, name in test_games:
            print(f"\n{name} (BGG ID: {bgg_id})")
            print("-" * 80)
            
            data = scrape_sleeve_data(bgg_id, name, driver)
            
            if data:
                results.append(data)
                print("\n  Results:")
                for card_type in data['card_types']:
                    print(f"    • {card_type['name'] or 'Unnamed'}: "
                          f"{card_type['dimensions']} mm, "
                          f"Qty {card_type['quantity'] or 'unknown'}")
                print(f"\n    Total cards: {data['total_cards']}")
                if data.get('notes'):
                    print(f"    Note: {data['notes']}")
            
            print()
    
    finally:
        driver.quit()
        print("✓ WebDriver closed")
    
    # Save results to JSON
    if results:
        output_file = 'sleeve_data_test.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ Saved results to: {output_file}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()