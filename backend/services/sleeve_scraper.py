"""
Sleeve scraping service using Selenium for BGG's JavaScript-rendered pages
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from typing import Optional, List, Dict

def create_game_slug(title: str) -> str:
    """Convert game title to BGG URL slug"""
    return title.lower().replace(' ', '-').replace(':', '').replace("'", '').replace('.', '')

def scrape_sleeve_data(bgg_id: int, game_title: str, driver=None) -> Optional[Dict]:
    """
    Scrape sleeve data from BGG's sleeve page

    Args:
        bgg_id: BoardGameGeek game ID
        game_title: Game title for URL slug
        driver: Optional Selenium WebDriver instance

    Returns:
        Dict with sleeve data or None if not found
        {
            'status': 'found' | 'not_found' | 'error',
            'card_types': [...],
            'notes': '...'
        }
    """
    import logging
    logger = logging.getLogger(__name__)

    slug = create_game_slug(game_title)
    url = f"https://boardgamegeek.com/boardgame/{bgg_id}/{slug}/sleeves"

    close_driver = False
    if driver is None:
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            driver = webdriver.Chrome(options=chrome_options)
            close_driver = True
        except Exception as e:
            logger.error(f"Failed to create Chrome WebDriver: {e}")
            logger.error("Chrome/ChromeDriver may not be installed. Sleeve scraping requires Chrome browser and ChromeDriver.")
            return {'status': 'error', 'card_types': [], 'notes': 'Chrome not available for scraping'}

    try:
        # Set aggressive timeouts to prevent hanging
        driver.set_page_load_timeout(20)  # 20 second timeout for page load
        driver.set_script_timeout(10)     # 10 second timeout for scripts

        driver.get(url)
        wait = WebDriverWait(driver, 10)  # 10 seconds max wait for elements

        try:
            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "sleeve-visualizer__card-list"))
            )
        except TimeoutException:
            logger.debug(f"Timeout waiting for sleeve data on {url}")
            return {'status': 'not_found', 'card_types': [], 'notes': None}

        time.sleep(0.5)  # Brief pause to let Angular finish rendering
        
        cards = driver.find_elements(By.CSS_SELECTOR, "li.sleeve-visualizer__card")
        
        if not cards:
            return {'status': 'not_found', 'card_types': [], 'notes': None}
        
        card_types = []
        
        for card in cards:
            try:
                dimensions_btn = card.find_element(By.CLASS_NAME, "sleeve-visualizer__card-dimensions")
                dimensions = dimensions_btn.text.strip()
                
                quantity = None
                try:
                    quantity_elem = card.find_element(By.CLASS_NAME, "sleeve-visualizer__card-quantity")
                    qty_text = quantity_elem.text.strip()
                    quantity = int(qty_text.upper().replace('QTY', '').strip())
                except (NoSuchElementException, ValueError):
                    pass
                
                card_name = None
                try:
                    name_elem = card.find_element(By.CLASS_NAME, "sleeve-visualizer__card-name")
                    name_span = name_elem.find_element(By.TAG_NAME, "span")
                    card_name = name_span.text.strip()
                except NoSuchElementException:
                    pass
                
                try:
                    width, height = dimensions.split('x')
                    width = int(float(width.strip()))
                    height = int(float(height.strip()))
                except:
                    continue
                
                card_types.append({
                    'name': card_name,
                    'width_mm': width,
                    'height_mm': height,
                    'quantity': quantity
                })
            except Exception:
                continue
        
        # Get notes if available
        notes = None
        try:
            notes_elem = driver.find_element(By.CLASS_NAME, "sleeve-visualizer__overview-notes__primary")
            notes = notes_elem.text.strip()
        except NoSuchElementException:
            pass
        
        if not card_types:
            return {'status': 'not_found', 'card_types': [], 'notes': None}
        
        return {
            'status': 'found',
            'card_types': card_types,
            'notes': notes
        }
        
    except Exception as e:
        print(f"Error scraping sleeves for {game_title}: {e}")
        return {'status': 'error', 'card_types': [], 'notes': None}
    
    finally:
        if close_driver:
            driver.quit()