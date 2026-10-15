"""
Comprehensive test suite for schemas module

Tests cover:
- Pydantic model validation
- Field validators and their error cases
- Schema serialization and deserialization
- Model configuration (from_attributes, extra)
- Edge cases and boundary conditions
- All schema types: Range, GameOut, etc.
"""
import pytest
from pydantic import ValidationError as PydanticValidationError

from schemas import (
    Range,
    GameOut,
    AdminLogin,
    FixSequenceRequest,
    BuyListGameCreate,
    BuyListGameUpdate,
)


class TestRangeSchema:
    """Test Range schema for min/max values"""

    def test_range_with_both_values(self):
        """Test Range with both min and max"""
        r = Range(min=1, max=4)
        assert r.min == 1
        assert r.max == 4

    def test_range_with_only_min(self):
        """Test Range with only min value"""
        r = Range(min=2)
        assert r.min == 2
        assert r.max is None

    def test_range_with_only_max(self):
        """Test Range with only max value"""
        r = Range(max=6)
        assert r.min is None
        assert r.max == 6

    def test_range_with_no_values(self):
        """Test Range with no values"""
        r = Range()
        assert r.min is None
        assert r.max is None

    def test_range_serialization(self):
        """Test Range serialization to dict"""
        r = Range(min=1, max=4)
        data = r.model_dump()
        assert data == {"min": 1, "max": 4}


class TestGameOutSchema:
    """Test GameOut schema for public game data"""

    def test_game_out_required_fields(self):
        """Test GameOut with only required fields"""
        game = GameOut(
            id=1,
            title="Test Game",
            categories=["Strategy", "Adventure"]
        )

        assert game.id == 1
        assert game.title == "Test Game"
        assert game.categories == ["Strategy", "Adventure"]
        assert game.year is None
        assert game.players_min is None

    def test_game_out_all_fields(self):
        """Test GameOut with all fields"""
        game = GameOut(
            id=1,
            title="Gloomhaven",
            categories=["Strategy", "Fantasy"],
            year=2017,
            players_min=1,
            players_max=4,
            playtime_min=60,
            playtime_max=120,
            thumbnail_url="https://example.com/thumb.jpg",
            game_type="board_game"
        )

        assert game.id == 1
        assert game.title == "Gloomhaven"
        assert game.year == 2017
        assert game.players_min == 1
        assert game.players_max == 4
        assert game.playtime_min == 60
        assert game.playtime_max == 120
        assert game.thumbnail_url == "https://example.com/thumb.jpg"
        assert game.game_type == "board_game"

    def test_game_out_from_attributes(self):
        """Test GameOut can be created from ORM objects"""
        # Simulate ORM object with attributes
        class FakeGame:
            id = 1
            title = "Test"
            categories = ["Strategy"]
            year = 2020
            players_min = 2
            players_max = 4
            playtime_min = 30
            playtime_max = 60
            thumbnail_url = None
            game_type = None

        game = GameOut.model_validate(FakeGame())
        assert game.id == 1
        assert game.title == "Test"
        assert game.categories == ["Strategy"]


class TestAdminLoginSchema:
    """Test AdminLogin schema validation"""

    def test_admin_login_valid(self):
        """Test AdminLogin with valid token"""
        login = AdminLogin(token="valid-token-12345")
        assert login.token == "valid-token-12345"

    def test_admin_login_strips_whitespace(self):
        """Test AdminLogin strips whitespace from token"""
        login = AdminLogin(token="  token-with-spaces  ")
        assert login.token == "token-with-spaces"

    def test_admin_login_too_short(self):
        """Test AdminLogin rejects short tokens"""
        with pytest.raises(PydanticValidationError) as exc_info:
            AdminLogin(token="short")

        errors = exc_info.value.errors()
        assert any("at least 10 characters" in str(e.get("msg", "")).lower() for e in errors)

    def test_admin_login_empty(self):
        """Test AdminLogin rejects empty token"""
        with pytest.raises(PydanticValidationError) as exc_info:
            AdminLogin(token="")

        errors = exc_info.value.errors()
        assert any("at least 10 characters" in str(e.get("msg", "")).lower() for e in errors)

    def test_admin_login_whitespace_only(self):
        """Test AdminLogin rejects whitespace-only token"""
        with pytest.raises(PydanticValidationError) as exc_info:
            AdminLogin(token="          ")

        errors = exc_info.value.errors()
        assert any("at least 10 characters" in str(e.get("msg", "")).lower() for e in errors)

    def test_admin_login_boundary(self):
        """Test AdminLogin with exactly 10 characters"""
        login = AdminLogin(token="1234567890")
        assert login.token == "1234567890"


class TestFixSequenceRequestSchema:
    """Test FixSequenceRequest schema validation"""

    def test_fix_sequence_default(self):
        """Test FixSequenceRequest with default table name"""
        req = FixSequenceRequest()
        assert req.table_name == "boardgames"

    def test_fix_sequence_valid_tables(self):
        """Test FixSequenceRequest with all valid table names"""
        valid_tables = ["boardgames", "buy_list_games", "sleeves"]

        for table in valid_tables:
            req = FixSequenceRequest(table_name=table)
            assert req.table_name == table

    def test_fix_sequence_invalid_table(self):
        """Test FixSequenceRequest rejects invalid table names"""
        with pytest.raises(PydanticValidationError) as exc_info:
            FixSequenceRequest(table_name="invalid_table")

        errors = exc_info.value.errors()
        assert any("invalid table name" in str(e.get("msg", "")).lower() for e in errors)

    def test_fix_sequence_sql_injection_attempt(self):
        """Test FixSequenceRequest rejects SQL injection attempts"""
        malicious_inputs = [
            "boardgames; DROP TABLE users;",
            "boardgames--",
            "boardgames/*comment*/",
            "boardgames OR 1=1",
        ]

        for malicious in malicious_inputs:
            with pytest.raises(PydanticValidationError):
                FixSequenceRequest(table_name=malicious)


class TestBuyListGameCreateSchema:
    """Test BuyListGameCreate schema validation"""

    def test_buy_list_create_minimal(self):
        """Test BuyListGameCreate with minimal required fields"""
        create = BuyListGameCreate(bgg_id=174430)
        assert create.bgg_id == 174430
        assert create.rank is None
        assert create.notes is None

    def test_buy_list_create_all_fields(self):
        """Test BuyListGameCreate with all fields"""
        create = BuyListGameCreate(
            bgg_id=174430,
            rank=1,
            notes="Fills a gap in Party & Icebreakers"
        )

        assert create.bgg_id == 174430
        assert create.rank == 1
        assert create.notes == "Fills a gap in Party & Icebreakers"

    def test_buy_list_create_invalid_bgg_id(self):
        """Test BuyListGameCreate rejects invalid BGG IDs"""
        with pytest.raises(PydanticValidationError):
            BuyListGameCreate(bgg_id=0)

        with pytest.raises(PydanticValidationError):
            BuyListGameCreate(bgg_id=-1)

        with pytest.raises(PydanticValidationError):
            BuyListGameCreate(bgg_id=1000000)


class TestBuyListGameUpdateSchema:
    """Test BuyListGameUpdate schema validation"""

    def test_buy_list_update_all_none(self):
        """Test BuyListGameUpdate with all fields as None"""
        update = BuyListGameUpdate()
        assert update.rank is None
        assert update.notes is None
        assert update.on_buy_list is None

    def test_buy_list_update_partial(self):
        """Test BuyListGameUpdate with partial fields"""
        update = BuyListGameUpdate(rank=5, on_buy_list=False)
        assert update.rank == 5
        assert update.on_buy_list is False
        assert update.notes is None

    def test_buy_list_update_all_fields(self):
        """Test BuyListGameUpdate with all fields"""
        update = BuyListGameUpdate(
            rank=2,
            notes="Looks good for the gap in 7-8 player games",
            on_buy_list=True
        )

        assert update.rank == 2
        assert update.notes == "Looks good for the gap in 7-8 player games"
        assert update.on_buy_list is True


class TestSchemaSeralization:
    """Test schema serialization and deserialization"""

    def test_game_out_to_dict(self):
        """Test GameOut serialization to dict"""
        game = GameOut(
            id=1,
            title="Test",
            categories=["Strategy"],
            year=2020
        )

        data = game.model_dump()
        assert data["id"] == 1
        assert data["title"] == "Test"
        assert data["categories"] == ["Strategy"]
        assert data["year"] == 2020

    def test_game_out_to_json(self):
        """Test GameOut serialization to JSON"""
        game = GameOut(
            id=1,
            title="Test",
            categories=["Strategy"]
        )

        json_str = game.model_dump_json()
        assert "\"id\":1" in json_str.replace(" ", "")
        assert "\"title\":\"Test\"" in json_str.replace(" ", "")

    def test_schema_from_dict(self):
        """Test creating schema from dictionary"""
        data = {
            "bgg_id": 174430,
            "rank": 1,
            "notes": "Fills a gap in Party & Icebreakers"
        }

        create = BuyListGameCreate(**data)
        assert create.bgg_id == 174430
        assert create.rank == 1
        assert create.notes == "Fills a gap in Party & Icebreakers"
