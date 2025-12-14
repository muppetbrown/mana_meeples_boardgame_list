"""
Comprehensive test suite for helper utility functions

Tests cover all utility functions including:
- Category parsing and categorization
- JSON field parsing
- URL handling
- Game-to-dict conversion
- Response formatting
- Category counting
"""
import pytest
from datetime import datetime
from unittest.mock import Mock

from utils.helpers import (
    parse_categories,
    parse_json_field,
    categorize_game,
    make_absolute_url,
    game_to_dict,
    calculate_category_counts,
    success_response,
    error_response,
    CATEGORY_KEYS,
)
from models import Game


# ============================================================================
# Test: Category Parsing
# ============================================================================

class TestParseCategories:
    """Test category parsing from various formats"""

    def test_parse_categories_from_list(self):
        """Should parse categories from list"""
        result = parse_categories(["Adventure", "Fantasy", "Cooperative"])
        assert result == ["Adventure", "Fantasy", "Cooperative"]

    def test_parse_categories_from_comma_separated(self):
        """Should parse categories from comma-separated string"""
        result = parse_categories("Adventure, Fantasy, Cooperative")
        assert result == ["Adventure", "Fantasy", "Cooperative"]

    def test_parse_categories_from_json_string(self):
        """Should parse categories from JSON string"""
        result = parse_categories('["Adventure", "Fantasy", "Cooperative"]')
        assert result == ["Adventure", "Fantasy", "Cooperative"]

    def test_parse_categories_empty_string(self):
        """Should return empty list for empty string"""
        result = parse_categories("")
        assert result == []

    def test_parse_categories_none(self):
        """Should return empty list for None"""
        result = parse_categories(None)
        assert result == []

    def test_parse_categories_strips_whitespace(self):
        """Should strip whitespace from categories"""
        result = parse_categories("  Adventure  ,  Fantasy  ")
        assert result == ["Adventure", "Fantasy"]

    def test_parse_categories_filters_empty(self):
        """Should filter out empty strings"""
        result = parse_categories("Adventure, , Fantasy,  ")
        assert result == ["Adventure", "Fantasy"]


# ============================================================================
# Test: JSON Field Parsing
# ============================================================================

class TestParseJSONField:
    """Test JSON field parsing"""

    def test_parse_json_field_from_list(self):
        """Should return list as-is"""
        result = parse_json_field(["Designer 1", "Designer 2"])
        assert result == ["Designer 1", "Designer 2"]

    def test_parse_json_field_from_json_string(self):
        """Should parse JSON string"""
        result = parse_json_field('["Designer 1", "Designer 2"]')
        assert result == ["Designer 1", "Designer 2"]

    def test_parse_json_field_none(self):
        """Should return empty list for None"""
        result = parse_json_field(None)
        assert result == []

    def test_parse_json_field_invalid_json(self):
        """Should return empty list for invalid JSON"""
        result = parse_json_field("not valid json")
        assert result == []

    def test_parse_json_field_non_list_json(self):
        """Should return empty list for non-list JSON"""
        result = parse_json_field('{"key": "value"}')
        assert result == []


# ============================================================================
# Test: Game Categorization
# ============================================================================

class TestCategorizeGame:
    """Test automatic game categorization"""

    def test_categorize_cooperative_game(self):
        """Should categorize cooperative games"""
        categories = ["Cooperative Game", "Adventure"]
        result = categorize_game(categories)
        assert result == "COOP_ADVENTURE"

    def test_categorize_party_game(self):
        """Should categorize party games"""
        categories = ["Party Game", "Humor"]
        result = categorize_game(categories)
        assert result == "PARTY_ICEBREAKERS"

    def test_categorize_strategy_game(self):
        """Should categorize strategy games"""
        categories = ["Wargame", "Strategy"]
        result = categorize_game(categories)
        assert result == "CORE_STRATEGY"

    def test_categorize_gateway_game(self):
        """Should categorize gateway games"""
        categories = ["Abstract Strategy", "Family Game"]
        result = categorize_game(categories)
        assert result == "GATEWAY_STRATEGY"

    def test_categorize_kids_game(self):
        """Should categorize kids/family games"""
        categories = ["Children's Game", "Memory"]
        result = categorize_game(categories)
        assert result == "KIDS_FAMILIES"

    def test_categorize_empty_categories(self):
        """Should return None for empty categories"""
        result = categorize_game([])
        assert result is None

    def test_categorize_case_insensitive(self):
        """Should be case-insensitive"""
        categories = ["COOPERATIVE GAME", "ADVENTURE"]
        result = categorize_game(categories)
        assert result == "COOP_ADVENTURE"

    def test_categorize_highest_score_wins(self):
        """Should return category with highest score"""
        # Cooperative exact match (score 10) should beat keyword matches
        categories = ["Cooperative Game", "Strategy"]
        result = categorize_game(categories)
        assert result == "COOP_ADVENTURE"


# ============================================================================
# Test: URL Handling
# ============================================================================

class TestMakeAbsoluteURL:
    """Test URL conversion to absolute"""

    def test_make_absolute_url_already_absolute(self):
        """Should return URL as-is if already absolute"""
        mock_request = Mock()
        url = "https://example.com/image.jpg"
        result = make_absolute_url(mock_request, url)
        assert result == url

    def test_make_absolute_url_http_already_absolute(self):
        """Should handle http URLs"""
        mock_request = Mock()
        url = "http://example.com/image.jpg"
        result = make_absolute_url(mock_request, url)
        assert result == url

    def test_make_absolute_url_relative(self):
        """Should convert relative URL to absolute"""
        mock_request = Mock()
        mock_request.base_url = "https://api.example.com/"

        result = make_absolute_url(mock_request, "/thumbs/image.jpg")
        assert result == "https://api.example.com/thumbs/image.jpg"

    def test_make_absolute_url_none(self):
        """Should return None for None input"""
        mock_request = Mock()
        result = make_absolute_url(mock_request, None)
        assert result is None

    def test_make_absolute_url_empty_string(self):
        """Should return None for empty string"""
        mock_request = Mock()
        result = make_absolute_url(mock_request, "")
        assert result is None


# ============================================================================
# Test: Game to Dictionary Conversion
# ============================================================================

class TestGameToDict:
    """Test game model to dictionary conversion"""

    def test_game_to_dict_basic_fields(self):
        """Should convert basic game fields"""
        mock_request = Mock()
        mock_request.base_url = "https://api.example.com/"

        game = Game(
            id=1,
            title="Test Game",
            year=2020,
            players_min=2,
            players_max=4,
        )

        result = game_to_dict(mock_request, game)

        assert result["id"] == 1
        assert result["title"] == "Test Game"
        assert result["year"] == 2020
        assert result["players_min"] == 2
        assert result["players_max"] == 4

    def test_game_to_dict_with_categories(self):
        """Should parse and include categories"""
        mock_request = Mock()
        mock_request.base_url = "https://api.example.com/"

        game = Game(
            id=1,
            title="Test Game",
            categories="Adventure, Fantasy",
        )

        result = game_to_dict(mock_request, game)

        assert result["categories"] == ["Adventure", "Fantasy"]

    def test_game_to_dict_with_json_fields(self):
        """Should parse JSON fields"""
        mock_request = Mock()
        mock_request.base_url = "https://api.example.com/"

        game = Game(
            id=1,
            title="Test Game",
            designers='["Designer 1", "Designer 2"]',
            mechanics='["Worker Placement", "Deck Building"]',
        )

        result = game_to_dict(mock_request, game)

        assert result["designers"] == ["Designer 1", "Designer 2"]
        assert result["mechanics"] == ["Worker Placement", "Deck Building"]

    def test_game_to_dict_aliases(self):
        """Should include frontend-friendly aliases"""
        mock_request = Mock()
        mock_request.base_url = "https://api.example.com/"

        game = Game(
            id=1,
            title="Test Game",
            year=2020,
            players_min=2,
            players_max=4,
            playtime_min=30,
        )

        result = game_to_dict(mock_request, game)

        # Check aliases exist
        assert result["year_published"] == 2020
        assert result["min_players"] == 2
        assert result["max_players"] == 4
        assert result["playing_time"] == 30

    def test_game_to_dict_missing_optional_fields(self):
        """Should handle missing optional fields"""
        mock_request = Mock()
        mock_request.base_url = "https://api.example.com/"

        game = Game(id=1, title="Test Game")

        result = game_to_dict(mock_request, game)

        # Should not crash, should use None for missing fields
        assert result["complexity"] is None
        assert result["average_rating"] is None
        assert result["description"] is None


# ============================================================================
# Test: Category Counting
# ============================================================================

class TestCalculateCategoryCounts:
    """Test category counting functionality"""

    def test_calculate_category_counts_basic(self):
        """Should count games by category"""
        games = [
            Mock(mana_meeple_category="COOP_ADVENTURE"),
            Mock(mana_meeple_category="COOP_ADVENTURE"),
            Mock(mana_meeple_category="PARTY_ICEBREAKERS"),
            Mock(mana_meeple_category="CORE_STRATEGY"),
        ]

        result = calculate_category_counts(games)

        assert result["all"] == 4
        assert result["COOP_ADVENTURE"] == 2
        assert result["PARTY_ICEBREAKERS"] == 1
        assert result["CORE_STRATEGY"] == 1

    def test_calculate_category_counts_uncategorized(self):
        """Should count uncategorized games"""
        games = [
            Mock(mana_meeple_category="COOP_ADVENTURE"),
            Mock(mana_meeple_category=None),
            Mock(mana_meeple_category=None),
        ]

        result = calculate_category_counts(games)

        assert result["all"] == 3
        assert result["uncategorized"] == 2
        assert result["COOP_ADVENTURE"] == 1

    def test_calculate_category_counts_tuple_format(self):
        """Should handle tuple format from select queries"""
        games = [
            (1, "COOP_ADVENTURE"),
            (2, "PARTY_ICEBREAKERS"),
            (3, None),
        ]

        result = calculate_category_counts(games)

        assert result["all"] == 3
        assert result["COOP_ADVENTURE"] == 1
        assert result["PARTY_ICEBREAKERS"] == 1
        assert result["uncategorized"] == 1

    def test_calculate_category_counts_empty_list(self):
        """Should handle empty list"""
        result = calculate_category_counts([])

        assert result["all"] == 0
        assert result["uncategorized"] == 0
        # All categories should be initialized to 0
        for key in CATEGORY_KEYS:
            assert result[key] == 0


# ============================================================================
# Test: Response Formatting
# ============================================================================

class TestSuccessResponse:
    """Test success response formatting"""

    def test_success_response_with_data(self):
        """Should format success response with data"""
        data = {"game": "Test Game"}
        result = success_response(data, "Game created")

        assert result["success"] is True
        assert result["message"] == "Game created"
        assert result["data"] == data
        assert "timestamp" in result

    def test_success_response_without_data(self):
        """Should format success response without data"""
        result = success_response(message="Operation successful")

        assert result["success"] is True
        assert result["message"] == "Operation successful"
        assert "data" not in result
        assert "timestamp" in result

    def test_success_response_default_message(self):
        """Should use default message"""
        result = success_response({"key": "value"})

        assert result["message"] == "Success"

    def test_success_response_timestamp_format(self):
        """Should include ISO format timestamp"""
        result = success_response()

        # Should be ISO format with Z suffix
        assert result["timestamp"].endswith("Z")
        # Should be parseable as ISO datetime
        datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))


class TestErrorResponse:
    """Test error response formatting"""

    def test_error_response_basic(self):
        """Should format error response"""
        result = error_response("Something went wrong", "GAME_NOT_FOUND")

        assert result["success"] is False
        assert result["error"]["code"] == "GAME_NOT_FOUND"
        assert result["error"]["message"] == "Something went wrong"
        assert "timestamp" in result

    def test_error_response_with_details(self):
        """Should include details if provided"""
        details = {"field": "bgg_id", "value": 12345}
        result = error_response("Validation failed", "VALIDATION_ERROR", details)

        assert result["error"]["details"] == details

    def test_error_response_default_code(self):
        """Should use default error code"""
        result = error_response("Generic error")

        assert result["error"]["code"] == "GENERAL_ERROR"

    def test_error_response_timestamp_format(self):
        """Should include ISO format timestamp"""
        result = error_response("Error occurred")

        assert result["timestamp"].endswith("Z")
        # Should be parseable as ISO datetime
        datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
