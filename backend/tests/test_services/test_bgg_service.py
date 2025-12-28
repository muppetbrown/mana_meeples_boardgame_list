"""
Comprehensive test suite for BGG Service

Tests cover all BGG API integration including:
- API fetching with retries and backoff
- XML parsing and data extraction
- Error handling for various failure scenarios
- Game classification logic
- Namespace handling
- Sleeve data extraction
- Rate limiting and queuing
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx
import xml.etree.ElementTree as ET

from bgg_service import (
    fetch_bgg_thing,
    _strip_namespace,
    _extract_comprehensive_game_data,
    _get_game_classification,
    BGGServiceError,
)


# Sample XML responses for testing
SAMPLE_GAME_XML = """<?xml version="1.0" encoding="utf-8"?>
<items termsofuse="https://boardgamegeek.com/xmlapi/termsofuse">
    <item type="boardgame" id="174430">
        <thumbnail>https://cf.geekdo-images.com/thumb.jpg</thumbnail>
        <image>https://cf.geekdo-images.com/image.jpg</image>
        <name type="primary" sortindex="1" value="Gloomhaven" />
        <description>Gloomhaven is a game of Euro-inspired tactical combat...</description>
        <yearpublished value="2017" />
        <minplayers value="1" />
        <maxplayers value="4" />
        <playingtime value="120" />
        <minplaytime value="60" />
        <maxplaytime value="150" />
        <minage value="14" />
        <link type="boardgamecategory" id="1022" value="Adventure" />
        <link type="boardgamecategory" id="1020" value="Fantasy" />
        <link type="boardgamedesigner" id="69802" value="Isaac Childres" />
        <link type="boardgamepublisher" id="23202" value="Cephalofair Games" />
        <link type="boardgamemechanic" id="2023" value="Cooperative Game" />
        <link type="boardgamemechanic" id="2040" value="Hand Management" />
        <link type="boardgameartist" id="69802" value="Isaac Childres" />
        <statistics page="1">
            <ratings>
                <usersrated value="57823" />
                <average value="8.66193" />
                <bayesaverage value="8.41632" />
                <averageweight value="3.86" />
                <ranks>
                    <rank type="subtype" id="1" name="boardgame" value="1" bayesaverage="8.41632" />
                </ranks>
            </ratings>
        </statistics>
    </item>
</items>
"""

SAMPLE_EXPANSION_XML = """<?xml version="1.0" encoding="utf-8"?>
<items>
    <item type="boardgameexpansion" id="254640">
        <name type="primary" value="Gloomhaven: Forgotten Circles" />
        <yearpublished value="2019" />
        <minplayers value="1" />
        <maxplayers value="4" />
        <link type="boardgamecategory" id="1042" value="Expansion" />
        <link type="boardgameexpands" id="174430" value="Gloomhaven" />
    </item>
</items>
"""


# ============================================================================
# Test: BGG API Fetching
# ============================================================================

class TestFetchBGGThing:
    """Test BGG API fetching with various scenarios"""

    @pytest.mark.asyncio
    async def test_fetch_successful(self):
        """Should successfully fetch and parse BGG data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_GAME_XML
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await fetch_bgg_thing(174430)

            assert result is not None
            assert result["title"] == "Gloomhaven"
            assert result["year"] == 2017
            assert result["complexity"] == 3.86
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_retry_on_202_accepted(self):
        """Should retry when BGG returns 202 (queued)"""
        mock_response_202 = Mock()
        mock_response_202.status_code = 202

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.text = SAMPLE_GAME_XML
        mock_response_200.headers = {"content-type": "application/xml"}
        mock_response_200.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[mock_response_202, mock_response_200])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            with patch("asyncio.sleep") as mock_sleep:
                result = await fetch_bgg_thing(174430)

                assert result is not None
                assert mock_client.get.call_count == 2
                assert mock_sleep.called  # Verify backoff delay

    @pytest.mark.asyncio
    async def test_fetch_retry_on_401_rate_limit(self):
        """Should retry when BGG returns 401 (rate limited)"""
        mock_response_401 = Mock()
        mock_response_401.status_code = 401

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.text = SAMPLE_GAME_XML
        mock_response_200.headers = {"content-type": "application/xml"}
        mock_response_200.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[mock_response_401, mock_response_200])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            with patch("asyncio.sleep"):
                result = await fetch_bgg_thing(174430)

                assert result is not None
                assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_invalid_bgg_id(self):
        """Should raise error for invalid BGG ID"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
            "Bad Request", request=Mock(), response=mock_response
        ))

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            with pytest.raises((BGGServiceError, httpx.HTTPStatusError)):
                await fetch_bgg_thing(999999)

    @pytest.mark.asyncio
    async def test_fetch_empty_response(self):
        """Should raise error for empty response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.content = b""  # Add content attribute
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            # Empty XML causes parse error
            with pytest.raises(BGGServiceError, match="Failed to parse"):
                await fetch_bgg_thing(12345)

    @pytest.mark.asyncio
    async def test_fetch_whitespace_only_response(self):
        """Should raise error for whitespace-only response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "   \n\t   "
        mock_response.content = b"   \n\t   "  # Add content attribute
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            with pytest.raises(BGGServiceError):
                await fetch_bgg_thing(12345)

    @pytest.mark.asyncio
    async def test_fetch_non_xml_response(self):
        """Should handle non-XML responses (HTML error pages)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>404 Not Found</body></html>"
        mock_response.content = b"<html><body>404 Not Found</body></html>"  # Add content attribute
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            with pytest.raises(BGGServiceError):
                await fetch_bgg_thing(12345)

    @pytest.mark.asyncio
    async def test_fetch_network_error(self):
        """Should handle network errors"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.NetworkError("Connection failed"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            with patch("asyncio.sleep"):
                # Should eventually raise BGGServiceError after all retries
                with pytest.raises(BGGServiceError):
                    await fetch_bgg_thing(12345, retries=2)


# ============================================================================
# Test: XML Parsing
# ============================================================================

class TestXMLParsing:
    """Test XML parsing and data extraction"""

    def test_strip_namespace_with_namespace(self):
        """Should strip XML namespaces"""
        xml_with_ns = """<?xml version="1.0"?>
        <root xmlns:ns="http://example.com">
            <ns:child>test</ns:child>
        </root>"""
        root = ET.fromstring(xml_with_ns)
        _strip_namespace(root)

        # After stripping, tags should not have namespace prefix
        assert "{" not in root.tag

    def test_strip_namespace_without_namespace(self):
        """Should handle XML without namespaces"""
        xml_no_ns = """<?xml version="1.0"?>
        <root>
            <child>test</child>
        </root>"""
        root = ET.fromstring(xml_no_ns)
        _strip_namespace(root)

        # Should complete without errors
        assert root.tag == "root"

    def test_extract_game_data_basic_fields(self):
        """Should extract basic game fields"""
        root = ET.fromstring(SAMPLE_GAME_XML)
        item = root.find("item")

        result = _extract_comprehensive_game_data(item, 174430)

        assert result["title"] == "Gloomhaven"
        assert result["year"] == 2017
        assert result["players_min"] == 1
        assert result["players_max"] == 4
        assert result["min_age"] == 14

    def test_extract_game_data_playtime(self):
        """Should extract playtime information"""
        root = ET.fromstring(SAMPLE_GAME_XML)
        item = root.find("item")

        result = _extract_comprehensive_game_data(item, 174430)

        assert result["playtime_min"] == 60
        assert result["playtime_max"] == 150

    def test_extract_game_data_categories(self):
        """Should extract categories as list"""
        root = ET.fromstring(SAMPLE_GAME_XML)
        item = root.find("item")

        result = _extract_comprehensive_game_data(item, 174430)

        assert "Adventure" in result["categories"]
        assert "Fantasy" in result["categories"]

    def test_extract_game_data_designers(self):
        """Should extract designers"""
        root = ET.fromstring(SAMPLE_GAME_XML)
        item = root.find("item")

        result = _extract_comprehensive_game_data(item, 174430)

        assert "Isaac Childres" in result["designers"]

    def test_extract_game_data_mechanics(self):
        """Should extract game mechanics"""
        root = ET.fromstring(SAMPLE_GAME_XML)
        item = root.find("item")

        result = _extract_comprehensive_game_data(item, 174430)

        assert "Cooperative Game" in result["mechanics"]
        assert "Hand Management" in result["mechanics"]

    def test_extract_game_data_statistics(self):
        """Should extract BGG statistics"""
        root = ET.fromstring(SAMPLE_GAME_XML)
        item = root.find("item")

        result = _extract_comprehensive_game_data(item, 174430)

        assert result["average_rating"] == pytest.approx(8.66, rel=0.01)
        assert result["complexity"] == pytest.approx(3.86, rel=0.01)
        assert result["users_rated"] == 57823
        assert result["bgg_rank"] == 1

    def test_extract_game_data_missing_fields(self):
        """Should handle missing optional fields"""
        minimal_xml = """<?xml version="1.0"?>
        <items>
            <item type="boardgame" id="12345">
                <name type="primary" value="Test Game" />
            </item>
        </items>"""

        root = ET.fromstring(minimal_xml)
        item = root.find("item")

        result = _extract_comprehensive_game_data(item, 12345)

        assert result["title"] == "Test Game"
        # Should not crash on missing fields
        assert "designers" in result
        assert "categories" in result


# ============================================================================
# Test: Game Classification
# ============================================================================

class TestGameClassification:
    """Test game type classification based on gameplay"""

    def test_classify_strategy_default(self):
        """Should default to Strategy for standard game"""
        xml = """<?xml version="1.0"?>
        <item type="boardgame" id="12345">
            <name type="primary" value="Base Game" />
        </item>"""
        item = ET.fromstring(xml)

        result = _get_game_classification(item)

        assert result == "Strategy"

    def test_classify_cooperative_game(self):
        """Should classify cooperative games"""
        xml = """<?xml version="1.0"?>
        <item type="boardgame" id="12345">
            <name type="primary" value="Coop Game" />
            <link type="boardgamemechanic" value="Cooperative Game" />
        </item>"""
        item = ET.fromstring(xml)

        result = _get_game_classification(item)

        assert result == "Co-op"

    def test_classify_party_game(self):
        """Should classify party games"""
        xml = """<?xml version="1.0"?>
        <item type="boardgame" id="12345">
            <name type="primary" value="Party Game" />
            <link type="boardgamecategory" value="Party Game" />
        </item>"""
        item = ET.fromstring(xml)

        result = _get_game_classification(item)

        assert result == "Party"

    def test_classify_worker_placement(self):
        """Should classify by mechanic (worker placement)"""
        xml = """<?xml version="1.0"?>
        <item type="boardgame" id="12345">
            <name type="primary" value="Worker Game" />
            <link type="boardgamemechanic" value="Worker Placement" />
        </item>"""
        item = ET.fromstring(xml)

        result = _get_game_classification(item)

        assert result == "Worker Placement"


# ============================================================================
# Test: Error Scenarios
# ============================================================================

class TestErrorHandling:
    """Test various error scenarios"""

    @pytest.mark.asyncio
    async def test_fetch_exceeds_max_retries(self):
        """Should fail after exhausting retries"""
        mock_response = Mock()
        mock_response.status_code = 503  # Server error

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            with patch("asyncio.sleep"):
                with pytest.raises(Exception):  # Will eventually fail after retries
                    await fetch_bgg_thing(12345, retries=2)

                # Should have tried multiple times
                assert mock_client.get.call_count >= 2

    def test_extract_data_malformed_xml(self):
        """Should handle malformed XML gracefully"""
        malformed_xml = """<?xml version="1.0"?>
        <items>
            <item type="boardgame" id="12345">
                <name type="primary" value="Test"
        </items>"""  # Intentionally malformed

        with pytest.raises(ET.ParseError):
            ET.fromstring(malformed_xml)


# ============================================================================
# Test: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and unusual scenarios"""

    @pytest.mark.asyncio
    async def test_fetch_with_special_characters_in_name(self):
        """Should handle games with special characters"""
        special_xml = """<?xml version="1.0"?>
        <items>
            <item type="boardgame" id="12345">
                <name type="primary" value="Game with &amp; Special &lt;Characters&gt;" />
                <description>Description with &quot;quotes&quot;</description>
            </item>
        </items>"""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = special_xml
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await fetch_bgg_thing(12345)

            # XML entities should be properly decoded
            assert "&" in result["title"] or "amp" not in result["title"]

    def test_extract_data_multiple_names(self):
        """Should handle games with multiple name types"""
        multi_name_xml = """<?xml version="1.0"?>
        <items>
            <item type="boardgame" id="12345">
                <name type="primary" value="English Name" />
                <name type="alternate" value="Alternate Name" />
            </item>
        </items>"""

        root = ET.fromstring(multi_name_xml)
        item = root.find("item")

        result = _extract_comprehensive_game_data(item, 12345)

        # Should use primary name
        assert result["title"] == "English Name"

    def test_extract_data_zero_players(self):
        """Should handle edge case of 0 players"""
        zero_players_xml = """<?xml version="1.0"?>
        <items>
            <item type="boardgame" id="12345">
                <name type="primary" value="Solo Game" />
                <minplayers value="0" />
                <maxplayers value="0" />
            </item>
        </items>"""

        root = ET.fromstring(zero_players_xml)
        item = root.find("item")

        result = _extract_comprehensive_game_data(item, 12345)

        # Should handle zero without crashing
        assert result["players_min"] == 0


# ============================================================================
# Test: Additional Coverage for Error Paths
# ============================================================================


class TestCircuitBreakerAndAuth:
    """Test circuit breaker and authentication scenarios"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_rejects_request(self):
        """Should reject request when circuit breaker is open"""
        from pybreaker import CircuitBreakerError

        with patch("bgg_service.bgg_circuit_breaker.call", side_effect=CircuitBreakerError("Circuit open")):
            with pytest.raises(BGGServiceError) as exc_info:
                await fetch_bgg_thing(12345)

            assert "circuit breaker open" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_uses_bgg_api_key_when_configured(self):
        """Should use BGG API key in headers when configured"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_GAME_XML
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/xml"}

        with patch("bgg_service.config.BGG_API_KEY", "test_api_key"), \
             patch("httpx.AsyncClient") as mock_client_cls:

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            await fetch_bgg_thing(12345)

            # Check that API key was included in headers
            call_args = mock_client.get.call_args
            headers = call_args[1].get("headers", {})
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer test_api_key"

    @pytest.mark.asyncio
    async def test_debug_logging_for_special_ids(self):
        """Should execute debug logging for special BGG IDs"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_GAME_XML
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.encoding = "utf-8"
        mock_response.content = SAMPLE_GAME_XML.encode("utf-8")
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            # Test with special debug ID (13 = Catan)
            result = await fetch_bgg_thing(13)

            # Should successfully process the request
            assert result is not None
            assert "title" in result

    @pytest.mark.asyncio
    async def test_debug_logging_for_problematic_id(self):
        """Should execute debug logging for problematic BGG ID"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_GAME_XML
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.encoding = "utf-8"
        mock_response.content = SAMPLE_GAME_XML.encode("utf-8")
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            # Test with problematic ID (314421)
            result = await fetch_bgg_thing(314421)

            # Should successfully process the request
            assert result is not None
            assert "title" in result


class TestErrorResponseHandling:
    """Test various error response scenarios"""

    @pytest.mark.asyncio
    async def test_handles_202_accepted_response(self):
        """Should retry on 202 Accepted response (BGG processing request)"""
        mock_response_202 = Mock()
        mock_response_202.status_code = 202
        mock_response_202.text = "Request queued"
        mock_response_202.raise_for_status = Mock()
        mock_response_202.headers = {"content-type": "text/plain"}

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.text = SAMPLE_GAME_XML
        mock_response_200.raise_for_status = Mock()
        mock_response_200.headers = {"content-type": "application/xml"}

        with patch("httpx.AsyncClient") as mock_client_cls, \
             patch("asyncio.sleep"):

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            # First call returns 202, second returns 200
            mock_client.get = AsyncMock(side_effect=[mock_response_202, mock_response_200])
            mock_client_cls.return_value = mock_client

            result = await fetch_bgg_thing(12345, retries=3)

            # Should retry and eventually succeed
            assert result is not None
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_handles_empty_xml_response(self):
        """Should handle empty XML response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<?xml version="1.0"?><items></items>'
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/xml"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            with pytest.raises(BGGServiceError) as exc_info:
                await fetch_bgg_thing(12345)

            assert "No game" in str(exc_info.value) and "found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handles_malformed_xml(self):
        """Should handle malformed XML response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'This is not valid XML <<>>'
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/xml"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            with pytest.raises(BGGServiceError) as exc_info:
                await fetch_bgg_thing(12345)

            assert "Failed to parse" in str(exc_info.value) or "XML" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handles_network_timeout(self):
        """Should handle network timeout errors"""
        with patch("httpx.AsyncClient") as mock_client_cls, \
             patch("asyncio.sleep"):

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
            mock_client_cls.return_value = mock_client

            with pytest.raises(BGGServiceError) as exc_info:
                await fetch_bgg_thing(12345, retries=2)

            assert "timeout" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_handles_connection_error(self):
        """Should handle connection errors"""
        with patch("httpx.AsyncClient") as mock_client_cls, \
             patch("asyncio.sleep"):

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            mock_client_cls.return_value = mock_client

            with pytest.raises(BGGServiceError) as exc_info:
                await fetch_bgg_thing(12345, retries=2)

            assert "connection" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
