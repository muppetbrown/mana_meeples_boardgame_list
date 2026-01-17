"""
Comprehensive tests for BGG service (bgg_service.py)
Target: 12.1% → 90% coverage
Focus: Rate limiting, circuit breaker, fetch logic, error handling
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import httpx

from bgg_service import (
    BGGRateLimiter,
    bgg_circuit_breaker,
    bgg_rate_limiter,
    fetch_bgg_thing,
    BGGServiceError,
    _extract_comprehensive_game_data,
    _is_bgg_available,
    _get_game_classification
)


class TestBGGRateLimiter:
    """Test BGG rate limiter token bucket algorithm"""

    @pytest.mark.asyncio
    async def test_acquire_token_within_limit(self):
        """Should allow requests within rate limit"""
        limiter = BGGRateLimiter(max_requests=5, time_window=10)

        # Make 5 requests (within limit)
        for i in range(5):
            await limiter.acquire()

        # All requests should succeed immediately
        assert len(limiter.requests) == 5

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excess_requests(self):
        """Should block requests when rate limit exceeded"""
        limiter = BGGRateLimiter(max_requests=2, time_window=2)

        # Make 2 requests (fill the bucket)
        await limiter.acquire()
        await limiter.acquire()

        # Third request should block
        start_time = datetime.now()
        await limiter.acquire()
        elapsed = (datetime.now() - start_time).total_seconds()

        # Should have waited at least 1 second (likely ~2 seconds)
        assert elapsed >= 1.0

    @pytest.mark.asyncio
    async def test_sliding_window_removes_old_requests(self):
        """Should remove old requests from sliding window"""
        limiter = BGGRateLimiter(max_requests=2, time_window=1)

        # Make 2 requests
        await limiter.acquire()
        await limiter.acquire()

        # Wait for time window to expire
        await asyncio.sleep(1.1)

        # Old requests should be removed, new request should succeed immediately
        start_time = datetime.now()
        await limiter.acquire()
        elapsed = (datetime.now() - start_time).total_seconds()

        # Should be nearly instant (< 0.1s)
        assert elapsed < 0.5

    @pytest.mark.asyncio
    async def test_exponential_backoff_capped_at_60s(self):
        """Should cap wait time at 60 seconds max"""
        limiter = BGGRateLimiter(max_requests=1, time_window=100)

        # Fill bucket
        await limiter.acquire()

        # Next request should wait, but capped at 60s
        # We'll mock the sleep to verify the cap
        with patch('bgg_service.asyncio.sleep') as mock_sleep:
            mock_sleep.return_value = AsyncMock()
            await limiter.acquire()

            # Should have been called with max 60 seconds
            call_args = mock_sleep.call_args[0][0]
            assert call_args <= 60

    @pytest.mark.asyncio
    async def test_concurrent_requests_thread_safety(self):
        """Should handle concurrent async requests safely"""
        limiter = BGGRateLimiter(max_requests=10, time_window=60)

        # Make 20 concurrent requests
        tasks = [limiter.acquire() for _ in range(20)]
        await asyncio.gather(*tasks)

        # Should have 10 in the bucket (others waited)
        assert len(limiter.requests) == 10


class TestCircuitBreaker:
    """Test circuit breaker pattern for BGG API failures"""

    def test_circuit_breaker_initial_state_closed(self):
        """Circuit should start in closed state"""
        assert _is_bgg_available() is True

    def test_circuit_opens_after_failures(self):
        """Circuit should open after threshold failures"""
        # Reset circuit breaker
        bgg_circuit_breaker._state_storage.state = bgg_circuit_breaker.STATE_CLOSED
        bgg_circuit_breaker._failure_count = 0

        # Trigger failures
        for _ in range(5):
            try:
                bgg_circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Network error")))
            except Exception:
                pass

        # Circuit should now be open
        from pybreaker import CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            bgg_circuit_breaker.call(lambda: None)

    def test_circuit_excludes_bgg_service_errors(self):
        """BGGServiceError should not trip circuit breaker"""
        # Reset circuit breaker
        bgg_circuit_breaker._state_storage.state = bgg_circuit_breaker.STATE_CLOSED
        bgg_circuit_breaker._failure_count = 0

        # Trigger BGGServiceError (should not count towards circuit break)
        for _ in range(10):
            with pytest.raises(BGGServiceError):
                bgg_circuit_breaker.call(lambda: (_ for _ in ()).throw(BGGServiceError("Invalid ID")))

        # Circuit should still be closed (BGGServiceError excluded)
        assert _is_bgg_available() is True


class TestFetchBGGThing:
    """Test main BGG fetch function with various scenarios"""

    @pytest.mark.asyncio
    async def test_successful_fetch_base_game(self, sample_bgg_xml):
        """Should successfully fetch and parse a base game"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_bgg_xml
        mock_response.headers = {'content-type': 'application/xml'}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            # Mock rate limiter to avoid waiting
            with patch('bgg_service.bgg_rate_limiter.acquire', new_callable=AsyncMock):
                result = await fetch_bgg_thing(174430)

        assert result['bgg_id'] == 174430
        assert result['title'] == 'Gloomhaven'
        assert result['year'] == 2017
        assert result['players_min'] == 1
        assert result['players_max'] == 4
        assert result['complexity'] == 3.87
        assert result['average_rating'] == 8.67883
        assert 'Isaac Childres' in result['designers']
        assert result['is_cooperative'] is True

    @pytest.mark.asyncio
    async def test_retry_logic_on_202_accepted(self):
        """Should retry when BGG returns 202 (request queued)"""
        mock_response_202 = MagicMock()
        mock_response_202.status_code = 202

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.text = '<?xml version="1.0"?><items><item type="boardgame" id="1"><name type="primary" value="Test"/></item></items>'
        mock_response_200.headers = {'content-type': 'application/xml'}
        mock_response_200.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            # First call returns 202, second returns 200
            mock_client.get = AsyncMock(side_effect=[mock_response_202, mock_response_200])
            mock_client_class.return_value = mock_client

            with patch('bgg_service.bgg_rate_limiter.acquire', new_callable=AsyncMock), \
                 patch('bgg_service.asyncio.sleep', new_callable=AsyncMock):
                result = await fetch_bgg_thing(1)

        # Should have made 2 requests (1 retry)
        assert mock_client.get.call_count == 2
        assert result['title'] == 'Test'

    @pytest.mark.asyncio
    async def test_timeout_after_max_retries(self):
        """Should raise BGGServiceError after max retries exhausted"""
        mock_response = MagicMock()
        mock_response.status_code = 503  # Service unavailable

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch('bgg_service.bgg_rate_limiter.acquire', new_callable=AsyncMock), \
                 patch('bgg_service.asyncio.sleep', new_callable=AsyncMock):
                # Should fail after HTTP_RETRIES attempts
                # The function will keep retrying 503 errors
                with pytest.raises(Exception):  # Will eventually raise some error
                    await fetch_bgg_thing(1, retries=2)

    @pytest.mark.asyncio
    async def test_invalid_xml_handling(self):
        """Should raise BGGServiceError for invalid XML"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = 'Invalid XML <unclosed'
        mock_response.headers = {'content-type': 'application/xml'}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch('bgg_service.bgg_rate_limiter.acquire', new_callable=AsyncMock):
                with pytest.raises(BGGServiceError, match="Failed to parse"):
                    await fetch_bgg_thing(1)

    @pytest.mark.asyncio
    async def test_network_error_propagation(self):
        """Should handle network errors gracefully"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Network timeout"))
            mock_client_class.return_value = mock_client

            with patch('bgg_service.bgg_rate_limiter.acquire', new_callable=AsyncMock), \
                 patch('bgg_service.asyncio.sleep', new_callable=AsyncMock):
                with pytest.raises(BGGServiceError, match="Timeout"):
                    await fetch_bgg_thing(1, retries=1)

    @pytest.mark.asyncio
    async def test_empty_response_handling(self):
        """Should raise BGGServiceError for empty response"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ''
        mock_response.headers = {'content-type': 'application/xml'}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch('bgg_service.bgg_rate_limiter.acquire', new_callable=AsyncMock):
                with pytest.raises(BGGServiceError, match="empty response"):
                    await fetch_bgg_thing(999999)

    @pytest.mark.asyncio
    async def test_non_existent_game_id(self):
        """Should raise BGGServiceError for non-existent game ID"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<?xml version="1.0"?><items></items>'
        mock_response.headers = {'content-type': 'application/xml'}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch('bgg_service.bgg_rate_limiter.acquire', new_callable=AsyncMock):
                with pytest.raises(BGGServiceError, match="does not exist"):
                    await fetch_bgg_thing(999999)

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_rejection(self):
        """Should reject requests when circuit breaker is open"""
        # Force circuit breaker to open
        bgg_circuit_breaker._state_storage.state = bgg_circuit_breaker.STATE_OPEN

        with pytest.raises(BGGServiceError, match="circuit breaker open"):
            await fetch_bgg_thing(1)

        # Reset circuit breaker for other tests
        bgg_circuit_breaker._state_storage.state = bgg_circuit_breaker.STATE_CLOSED
        bgg_circuit_breaker._failure_count = 0

    @pytest.mark.asyncio
    async def test_400_invalid_bgg_id(self):
        """Should raise BGGServiceError for 400 Bad Request"""
        mock_response = MagicMock()
        mock_response.status_code = 400

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch('bgg_service.bgg_rate_limiter.acquire', new_callable=AsyncMock):
                with pytest.raises(BGGServiceError, match="Invalid BGG ID"):
                    await fetch_bgg_thing(-1)

    @pytest.mark.asyncio
    async def test_html_error_page_detection(self):
        """Should detect HTML error pages and raise appropriate error"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>404 Not Found</body></html>'
        mock_response.headers = {'content-type': 'text/html'}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch('bgg_service.bgg_rate_limiter.acquire', new_callable=AsyncMock):
                with pytest.raises(BGGServiceError, match="does not exist|error page"):
                    await fetch_bgg_thing(999999)


class TestExtractComprehensiveGameData:
    """Test data extraction from BGG XML"""

    def test_extract_data_from_complete_xml(self, sample_bgg_xml):
        """Should extract all data from complete BGG XML"""
        root = ET.fromstring(sample_bgg_xml)
        item = root.find('item')

        result = _extract_comprehensive_game_data(item, 174430)

        assert result['bgg_id'] == 174430
        assert result['title'] == 'Gloomhaven'
        assert result['year'] == 2017
        assert result['players_min'] == 1
        assert result['players_max'] == 4
        assert result['playtime_min'] == 60
        assert result['playtime_max'] == 120
        assert result['min_age'] == 14
        assert result['complexity'] == 3.87
        assert result['average_rating'] == 8.67883
        assert result['bgg_rank'] == 1
        assert 'Adventure' in result['categories']
        assert 'Cooperative Game' in result['mechanics']
        assert 'Isaac Childres' in result['designers']
        assert result['is_cooperative'] is True

    def test_extract_data_from_expansion_xml(self, sample_bgg_xml_expansion):
        """Should correctly identify and process expansions"""
        root = ET.fromstring(sample_bgg_xml_expansion)
        item = root.find('item')

        result = _extract_comprehensive_game_data(item, 239188)

        assert result['is_expansion'] is True
        assert result['base_game_bgg_id'] == 174430
        assert result['base_game_name'] == 'Gloomhaven'

    def test_extract_data_with_missing_fields(self, sample_bgg_xml_minimal):
        """Should handle missing optional fields gracefully"""
        root = ET.fromstring(sample_bgg_xml_minimal)
        item = root.find('item')

        result = _extract_comprehensive_game_data(item, 999)

        # Should have basic fields
        assert result['title'] == 'Minimal Game'
        assert result['year'] == 2020

        # Optional fields should be None or empty lists
        assert result.get('complexity') is None
        assert result.get('average_rating') is None
        assert result.get('designers', []) == []


class TestGetGameClassification:
    """Test fallback game classification logic"""

    def test_classification_party_game(self):
        """Should classify party games correctly"""
        xml = '''<item type="boardgame" id="1">
            <link type="boardgamecategory" id="1" value="Party Game"/>
        </item>'''
        item = ET.fromstring(xml)

        result = _get_game_classification(item)
        assert result == 'Party'

    def test_classification_cooperative_mechanic(self):
        """Should classify cooperative games from mechanics"""
        xml = '''<item type="boardgame" id="1">
            <link type="boardgamemechanic" id="1" value="Cooperative Game"/>
        </item>'''
        item = ET.fromstring(xml)

        result = _get_game_classification(item)
        assert result == 'Co-op'

    def test_classification_deck_builder(self):
        """Should classify deck building games"""
        xml = '''<item type="boardgame" id="1">
            <link type="boardgamemechanic" id="1" value="Deck Building"/>
        </item>'''
        item = ET.fromstring(xml)

        result = _get_game_classification(item)
        assert result == 'Deck Builder'

    def test_classification_fallback_to_strategy(self):
        """Should fallback to Strategy when no matches"""
        xml = '''<item type="boardgame" id="1">
            <link type="boardgamecategory" id="1" value="Unknown Category"/>
        </item>'''
        item = ET.fromstring(xml)

        result = _get_game_classification(item)
        assert result == 'Strategy'

    def test_classification_priority_order(self):
        """Should respect priority order in classification"""
        # Party games should take precedence over mechanics
        xml = '''<item type="boardgame" id="1">
            <link type="boardgamecategory" id="1" value="Party Game"/>
            <link type="boardgamemechanic" id="2" value="Deck Building"/>
        </item>'''
        item = ET.fromstring(xml)

        result = _get_game_classification(item)
        assert result == 'Party'
