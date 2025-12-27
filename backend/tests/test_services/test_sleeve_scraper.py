"""
Comprehensive tests for services/sleeve_scraper.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from services.sleeve_scraper import create_game_slug, scrape_sleeve_data


class TestCreateGameSlug:
    """Test create_game_slug function"""

    def test_create_game_slug_basic(self):
        """Test basic game title slug creation"""
        assert create_game_slug("Catan") == "catan"

    def test_create_game_slug_with_spaces(self):
        """Test slug creation with spaces"""
        assert create_game_slug("Ticket to Ride") == "ticket-to-ride"

    def test_create_game_slug_with_colon(self):
        """Test slug creation removes colons"""
        assert create_game_slug("Pandemic: Legacy") == "pandemic-legacy"

    def test_create_game_slug_with_apostrophe(self):
        """Test slug creation removes apostrophes"""
        assert create_game_slug("King's Dilemma") == "kings-dilemma"

    def test_create_game_slug_with_period(self):
        """Test slug creation removes periods"""
        assert create_game_slug("Mr. Jack") == "mr-jack"

    def test_create_game_slug_complex(self):
        """Test slug creation with multiple special characters"""
        assert create_game_slug("Dungeons & Dragons: Castle Ravenloft") == "dungeons-&-dragons-castle-ravenloft"

    def test_create_game_slug_uppercase(self):
        """Test slug creation converts to lowercase"""
        assert create_game_slug("CATAN") == "catan"

    def test_create_game_slug_mixed_case(self):
        """Test slug creation with mixed case"""
        assert create_game_slug("Ticket To Ride") == "ticket-to-ride"

    def test_create_game_slug_empty_string(self):
        """Test slug creation with empty string"""
        assert create_game_slug("") == ""

    def test_create_game_slug_whitespace_only(self):
        """Test slug creation with whitespace"""
        assert create_game_slug("   ") == "---"


class TestScrapeSleevDataDriverCreation:
    """Test scrape_sleeve_data driver creation and error handling"""

    @patch('services.sleeve_scraper.webdriver.Chrome')
    def test_scrape_sleeve_data_creates_driver_when_none(self, mock_chrome):
        """Test that driver is created when not provided"""
        # Setup mock driver
        mock_driver_instance = Mock()
        mock_chrome.return_value = mock_driver_instance
        mock_driver_instance.find_elements.return_value = []

        # Mock WebDriverWait to raise TimeoutException
        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.side_effect = TimeoutException()

            result = scrape_sleeve_data(123, "Test Game")

        # Verify Chrome was instantiated
        mock_chrome.assert_called_once()
        # Verify driver was closed
        mock_driver_instance.quit.assert_called_once()
        assert result['status'] == 'not_found'

    @patch('services.sleeve_scraper.webdriver.Chrome')
    def test_scrape_sleeve_data_chrome_creation_fails(self, mock_chrome):
        """Test handling when Chrome driver creation fails"""
        mock_chrome.side_effect = Exception("Chrome not found")

        result = scrape_sleeve_data(123, "Test Game")

        assert result['status'] == 'error'
        assert result['card_types'] == []
        assert 'Chrome not available' in result['notes']

    def test_scrape_sleeve_data_uses_provided_driver(self):
        """Test that provided driver is used and not closed"""
        mock_driver = Mock()
        mock_driver.find_elements.return_value = []

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.side_effect = TimeoutException()

            result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        # Verify driver.quit() was NOT called since we provided the driver
        mock_driver.quit.assert_not_called()
        assert result['status'] == 'not_found'


class TestScrapeSleevDataTimeout:
    """Test timeout and error scenarios"""

    def test_scrape_sleeve_data_timeout(self):
        """Test timeout when waiting for elements"""
        mock_driver = Mock()

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.side_effect = TimeoutException()

            result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        assert result['status'] == 'not_found'
        assert result['card_types'] == []
        assert result['notes'] is None

    def test_scrape_sleeve_data_page_load_timeout(self):
        """Test page load timeout handling"""
        mock_driver = Mock()
        mock_driver.get.side_effect = TimeoutException("Page load timeout")

        result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        assert result['status'] == 'error'
        assert result['card_types'] == []

    def test_scrape_sleeve_data_sets_timeouts(self):
        """Test that timeouts are set on driver"""
        mock_driver = Mock()

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.side_effect = TimeoutException()

            scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        # Verify timeouts were set
        mock_driver.set_page_load_timeout.assert_called_once_with(20)
        mock_driver.set_script_timeout.assert_called_once_with(10)


class TestScrapeSleevDataNoCards:
    """Test scenarios with no card data"""

    def test_scrape_sleeve_data_no_cards_found(self):
        """Test when sleeve page exists but has no cards"""
        mock_driver = Mock()
        mock_driver.find_elements.return_value = []

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.return_value = True

            with patch('services.sleeve_scraper.time.sleep'):
                result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        assert result['status'] == 'not_found'
        assert result['card_types'] == []
        assert result['notes'] is None

    def test_scrape_sleeve_data_empty_card_list(self):
        """Test when card list element exists but is empty"""
        mock_driver = Mock()

        # First find_elements returns empty (no cards)
        mock_driver.find_elements.return_value = []

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.return_value = True

            with patch('services.sleeve_scraper.time.sleep'):
                result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        assert result['status'] == 'not_found'
        assert result['card_types'] == []


class TestScrapeSleevDataSuccess:
    """Test successful sleeve data scraping"""

    def test_scrape_sleeve_data_success_single_card(self):
        """Test successful scraping with single card type"""
        mock_driver = Mock()

        # Mock card element
        mock_card = Mock()
        mock_dimensions_btn = Mock()
        mock_dimensions_btn.text = "63.5 x 88"

        def card_find_element(by, value):
            if value == 'sleeve-visualizer__card-dimensions':
                return mock_dimensions_btn
            raise NoSuchElementException()

        mock_card.find_element = Mock(side_effect=card_find_element)

        # Mock driver to return the card list
        def driver_find_elements(by, value):
            if value == "li.sleeve-visualizer__card":
                return [mock_card]
            return []

        mock_driver.find_elements = Mock(side_effect=driver_find_elements)
        mock_driver.find_element = Mock(side_effect=NoSuchElementException())  # No notes

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.return_value = True

            with patch('services.sleeve_scraper.time.sleep'):
                result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        assert result['status'] == 'found'
        assert len(result['card_types']) == 1
        assert result['card_types'][0]['width_mm'] == 63
        assert result['card_types'][0]['height_mm'] == 88
        assert result['card_types'][0]['quantity'] == 0
        assert result['card_types'][0]['name'] is None
        assert result['notes'] is None

    def test_scrape_sleeve_data_success_with_quantity(self):
        """Test successful scraping with quantity data"""
        mock_driver = Mock()

        # Mock card element with quantity
        mock_card = Mock()
        mock_dimensions_btn = Mock()
        mock_dimensions_btn.text = "63.5 x 88"
        mock_quantity_elem = Mock()
        mock_quantity_elem.text = "Qty 52"

        def find_element_side_effect(by, value):
            if value == 'sleeve-visualizer__card-dimensions':
                return mock_dimensions_btn
            elif value == 'sleeve-visualizer__card-quantity':
                return mock_quantity_elem
            raise NoSuchElementException()

        mock_card.find_element.side_effect = find_element_side_effect

        mock_driver.find_elements.return_value = [mock_card]
        mock_driver.find_element.side_effect = NoSuchElementException()

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.return_value = True

            with patch('services.sleeve_scraper.time.sleep'):
                result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        assert result['status'] == 'found'
        assert len(result['card_types']) == 1
        assert result['card_types'][0]['quantity'] == 52

    def test_scrape_sleeve_data_success_with_card_name(self):
        """Test successful scraping with card name"""
        mock_driver = Mock()

        # Mock card element with name
        mock_card = Mock()
        mock_dimensions_btn = Mock()
        mock_dimensions_btn.text = "63.5 x 88"
        mock_name_elem = Mock()
        mock_name_span = Mock()
        mock_name_span.text = "Standard Card"
        mock_name_elem.find_element.return_value = mock_name_span

        def find_element_side_effect(by, value):
            if value == 'sleeve-visualizer__card-dimensions':
                return mock_dimensions_btn
            elif value == 'sleeve-visualizer__card-name':
                return mock_name_elem
            raise NoSuchElementException()

        mock_card.find_element.side_effect = find_element_side_effect

        mock_driver.find_elements.return_value = [mock_card]
        mock_driver.find_element.side_effect = NoSuchElementException()

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.return_value = True

            with patch('services.sleeve_scraper.time.sleep'):
                result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        assert result['status'] == 'found'
        assert len(result['card_types']) == 1
        assert result['card_types'][0]['name'] == "Standard Card"

    def test_scrape_sleeve_data_success_with_notes(self):
        """Test successful scraping with notes"""
        mock_driver = Mock()

        # Mock card element
        mock_card = Mock()
        mock_dimensions_btn = Mock()
        mock_dimensions_btn.text = "63.5 x 88"

        def card_find_element(by, value):
            if value == 'sleeve-visualizer__card-dimensions':
                return mock_dimensions_btn
            raise NoSuchElementException()

        mock_card.find_element = Mock(side_effect=card_find_element)

        # Mock notes element
        mock_notes_elem = Mock()
        mock_notes_elem.text = "Important note about sleeves"

        def driver_find_elements(by, value):
            if value == "li.sleeve-visualizer__card":
                return [mock_card]
            return []

        def driver_find_element(by, value):
            if value == 'sleeve-visualizer__overview-notes__primary':
                return mock_notes_elem
            raise NoSuchElementException()

        mock_driver.find_elements = Mock(side_effect=driver_find_elements)
        mock_driver.find_element = Mock(side_effect=driver_find_element)

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.return_value = True

            with patch('services.sleeve_scraper.time.sleep'):
                result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        assert result['status'] == 'found'
        assert result['notes'] == "Important note about sleeves"

    def test_scrape_sleeve_data_success_multiple_cards(self):
        """Test successful scraping with multiple card types"""
        mock_driver = Mock()

        # Mock first card
        mock_card1 = Mock()
        mock_dimensions_btn1 = Mock()
        mock_dimensions_btn1.text = "63.5 x 88"

        def card1_find_element(by, value):
            if value == 'sleeve-visualizer__card-dimensions':
                return mock_dimensions_btn1
            raise NoSuchElementException()

        mock_card1.find_element = Mock(side_effect=card1_find_element)

        # Mock second card
        mock_card2 = Mock()
        mock_dimensions_btn2 = Mock()
        mock_dimensions_btn2.text = "70 x 120"

        def card2_find_element(by, value):
            if value == 'sleeve-visualizer__card-dimensions':
                return mock_dimensions_btn2
            raise NoSuchElementException()

        mock_card2.find_element = Mock(side_effect=card2_find_element)

        def driver_find_elements(by, value):
            if value == "li.sleeve-visualizer__card":
                return [mock_card1, mock_card2]
            return []

        mock_driver.find_elements = Mock(side_effect=driver_find_elements)
        mock_driver.find_element = Mock(side_effect=NoSuchElementException())

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.return_value = True

            with patch('services.sleeve_scraper.time.sleep'):
                result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        assert result['status'] == 'found'
        assert len(result['card_types']) == 2
        assert result['card_types'][0]['width_mm'] == 63
        assert result['card_types'][0]['height_mm'] == 88
        assert result['card_types'][1]['width_mm'] == 70
        assert result['card_types'][1]['height_mm'] == 120


class TestScrapeSleevDataEdgeCases:
    """Test edge cases and error handling"""

    def test_scrape_sleeve_data_invalid_dimensions_format(self):
        """Test handling of invalid dimension format"""
        mock_driver = Mock()

        # Mock card with invalid dimensions
        mock_card = Mock()
        mock_dimensions_btn = Mock()
        mock_dimensions_btn.text = "invalid"
        mock_card.find_element.side_effect = lambda by, value: {
            'sleeve-visualizer__card-dimensions': mock_dimensions_btn,
        }.get(value, Mock(side_effect=NoSuchElementException()))

        mock_driver.find_elements.return_value = [mock_card]
        mock_driver.find_element.side_effect = NoSuchElementException()

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.return_value = True

            with patch('services.sleeve_scraper.time.sleep'):
                result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        # Card with invalid dimensions should be skipped
        assert result['status'] == 'not_found'
        assert result['card_types'] == []

    def test_scrape_sleeve_data_invalid_quantity_format(self):
        """Test handling of invalid quantity format"""
        mock_driver = Mock()

        # Mock card with invalid quantity
        mock_card = Mock()
        mock_dimensions_btn = Mock()
        mock_dimensions_btn.text = "63.5 x 88"
        mock_quantity_elem = Mock()
        mock_quantity_elem.text = "invalid"

        def find_element_side_effect(by, value):
            if value == 'sleeve-visualizer__card-dimensions':
                return mock_dimensions_btn
            elif value == 'sleeve-visualizer__card-quantity':
                return mock_quantity_elem
            raise NoSuchElementException()

        mock_card.find_element.side_effect = find_element_side_effect

        mock_driver.find_elements.return_value = [mock_card]
        mock_driver.find_element.side_effect = NoSuchElementException()

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.return_value = True

            with patch('services.sleeve_scraper.time.sleep'):
                result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        # Should still succeed with quantity=0
        assert result['status'] == 'found'
        assert result['card_types'][0]['quantity'] == 0

    def test_scrape_sleeve_data_decimal_dimensions(self):
        """Test handling of decimal dimensions (should be rounded to int)"""
        mock_driver = Mock()

        # Mock card with decimal dimensions
        mock_card = Mock()
        mock_dimensions_btn = Mock()
        mock_dimensions_btn.text = "63.5 x 88.9"

        def card_find_element(by, value):
            if value == 'sleeve-visualizer__card-dimensions':
                return mock_dimensions_btn
            raise NoSuchElementException()

        mock_card.find_element = Mock(side_effect=card_find_element)

        def driver_find_elements(by, value):
            if value == "li.sleeve-visualizer__card":
                return [mock_card]
            return []

        mock_driver.find_elements = Mock(side_effect=driver_find_elements)
        mock_driver.find_element = Mock(side_effect=NoSuchElementException())

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.return_value = True

            with patch('services.sleeve_scraper.time.sleep'):
                result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        assert result['status'] == 'found'
        assert result['card_types'][0]['width_mm'] == 63
        assert result['card_types'][0]['height_mm'] == 88

    def test_scrape_sleeve_data_card_exception(self):
        """Test handling of exception while parsing individual card"""
        mock_driver = Mock()

        # Mock card that throws exception
        mock_card = Mock()
        mock_card.find_element.side_effect = Exception("Card parsing error")

        mock_driver.find_elements.return_value = [mock_card]
        mock_driver.find_element.side_effect = NoSuchElementException()

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.return_value = True

            with patch('services.sleeve_scraper.time.sleep'):
                result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        # Card with exception should be skipped
        assert result['status'] == 'not_found'
        assert result['card_types'] == []

    def test_scrape_sleeve_data_mixed_valid_invalid_cards(self):
        """Test scraping with mix of valid and invalid cards"""
        mock_driver = Mock()

        # Mock valid card
        mock_card1 = Mock()
        mock_dimensions_btn1 = Mock()
        mock_dimensions_btn1.text = "63.5 x 88"

        def card1_find_element(by, value):
            if value == 'sleeve-visualizer__card-dimensions':
                return mock_dimensions_btn1
            raise NoSuchElementException()

        mock_card1.find_element = Mock(side_effect=card1_find_element)

        # Mock invalid card (throws exception)
        mock_card2 = Mock()
        mock_card2.find_element = Mock(side_effect=Exception("Error"))

        def driver_find_elements(by, value):
            if value == "li.sleeve-visualizer__card":
                return [mock_card1, mock_card2]
            return []

        mock_driver.find_elements = Mock(side_effect=driver_find_elements)
        mock_driver.find_element = Mock(side_effect=NoSuchElementException())

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.return_value = True

            with patch('services.sleeve_scraper.time.sleep'):
                result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        # Should return only valid card
        assert result['status'] == 'found'
        assert len(result['card_types']) == 1
        assert result['card_types'][0]['width_mm'] == 63

    def test_scrape_sleeve_data_general_exception(self):
        """Test handling of general exception during scraping"""
        mock_driver = Mock()
        mock_driver.get.side_effect = Exception("General error")

        result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        assert result['status'] == 'error'
        assert result['card_types'] == []
        assert result['notes'] is None

    def test_scrape_sleeve_data_whitespace_in_text(self):
        """Test handling of whitespace in scraped text"""
        mock_driver = Mock()

        # Mock card with whitespace in text
        mock_card = Mock()
        mock_dimensions_btn = Mock()
        mock_dimensions_btn.text = "  63.5  x  88  "

        def card_find_element(by, value):
            if value == 'sleeve-visualizer__card-dimensions':
                return mock_dimensions_btn
            raise NoSuchElementException()

        mock_card.find_element = Mock(side_effect=card_find_element)

        def driver_find_elements(by, value):
            if value == "li.sleeve-visualizer__card":
                return [mock_card]
            return []

        mock_driver.find_elements = Mock(side_effect=driver_find_elements)
        mock_driver.find_element = Mock(side_effect=NoSuchElementException())

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.return_value = True

            with patch('services.sleeve_scraper.time.sleep'):
                result = scrape_sleeve_data(123, "Test Game", driver=mock_driver)

        assert result['status'] == 'found'
        assert result['card_types'][0]['width_mm'] == 63
        assert result['card_types'][0]['height_mm'] == 88


class TestScrapeSleevDataURL:
    """Test URL construction and navigation"""

    def test_scrape_sleeve_data_url_construction(self):
        """Test that correct URL is constructed"""
        mock_driver = Mock()

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.side_effect = TimeoutException()

            scrape_sleeve_data(271512, "Ticket to Ride", driver=mock_driver)

        # Verify correct URL was loaded
        expected_url = "https://boardgamegeek.com/boardgame/271512/ticket-to-ride/sleeves"
        mock_driver.get.assert_called_once_with(expected_url)

    def test_scrape_sleeve_data_url_with_special_chars(self):
        """Test URL construction with special characters in title"""
        mock_driver = Mock()

        with patch('services.sleeve_scraper.WebDriverWait') as mock_wait:
            mock_wait.return_value.until.side_effect = TimeoutException()

            scrape_sleeve_data(123, "Dungeons & Dragons: Castle Ravenloft", driver=mock_driver)

        # Verify slug was created correctly
        expected_url = "https://boardgamegeek.com/boardgame/123/dungeons-&-dragons-castle-ravenloft/sleeves"
        mock_driver.get.assert_called_once_with(expected_url)
