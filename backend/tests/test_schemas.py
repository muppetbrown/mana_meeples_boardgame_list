"""
Comprehensive test suite for schemas module

Tests cover:
- Pydantic model validation
- Field validators and their error cases
- Schema serialization and deserialization
- Model configuration (from_attributes, extra)
- Edge cases and boundary conditions
- All schema types: Range, GameOut, PagedGames, etc.
"""
import pytest
from pydantic import ValidationError as PydanticValidationError

from schemas import (
    Range,
    GameOut,
    PagedGames,
    CategoryCounts,
    BGGGameImport,
    CSVImport,
    AdminLogin,
    FixSequenceRequest,
    BuyListGameCreate,
    BuyListGameUpdate,
    PriceSnapshotOut,
    BuyListGameOut,
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


class TestPagedGamesSchema:
    """Test PagedGames schema for paginated responses"""

    def test_paged_games_structure(self):
        """Test PagedGames structure"""
        games = [
            GameOut(id=1, title="Game 1", categories=[]),
            GameOut(id=2, title="Game 2", categories=[]),
        ]

        paged = PagedGames(
            total=10,
            page=1,
            page_size=2,
            items=games
        )

        assert paged.total == 10
        assert paged.page == 1
        assert paged.page_size == 2
        assert len(paged.items) == 2
        assert paged.items[0].title == "Game 1"

    def test_paged_games_empty(self):
        """Test PagedGames with empty items"""
        paged = PagedGames(
            total=0,
            page=1,
            page_size=10,
            items=[]
        )

        assert paged.total == 0
        assert len(paged.items) == 0


class TestCategoryCountsSchema:
    """Test CategoryCounts schema"""

    def test_category_counts_basic(self):
        """Test CategoryCounts with basic data"""
        counts = CategoryCounts(root={
            "GATEWAY_STRATEGY": 50,
            "CORE_STRATEGY": 30,
            "PARTY_ICEBREAKERS": 25
        })

        assert counts.root["GATEWAY_STRATEGY"] == 50
        assert counts.root["CORE_STRATEGY"] == 30
        assert counts.root["PARTY_ICEBREAKERS"] == 25

    def test_category_counts_empty(self):
        """Test CategoryCounts with empty dict"""
        counts = CategoryCounts(root={})
        assert counts.root == {}


class TestBGGGameImportSchema:
    """Test BGGGameImport schema validation"""

    def test_bgg_import_valid(self):
        """Test BGGGameImport with valid BGG ID"""
        import_data = BGGGameImport(bgg_id=174430)
        assert import_data.bgg_id == 174430

    def test_bgg_import_invalid_zero(self):
        """Test BGGGameImport rejects zero"""
        with pytest.raises(PydanticValidationError) as exc_info:
            BGGGameImport(bgg_id=0)

        errors = exc_info.value.errors()
        assert any("must be between 1 and 999999" in str(e.get("msg", "")).lower() for e in errors)

    def test_bgg_import_invalid_negative(self):
        """Test BGGGameImport rejects negative values"""
        with pytest.raises(PydanticValidationError) as exc_info:
            BGGGameImport(bgg_id=-1)

        errors = exc_info.value.errors()
        assert any("must be between 1 and 999999" in str(e.get("msg", "")).lower() for e in errors)

    def test_bgg_import_invalid_too_large(self):
        """Test BGGGameImport rejects values over 999999"""
        with pytest.raises(PydanticValidationError) as exc_info:
            BGGGameImport(bgg_id=1000000)

        errors = exc_info.value.errors()
        assert any("must be between 1 and 999999" in str(e.get("msg", "")).lower() for e in errors)

    def test_bgg_import_boundary_values(self):
        """Test BGGGameImport boundary values"""
        # Minimum valid value
        import_min = BGGGameImport(bgg_id=1)
        assert import_min.bgg_id == 1

        # Maximum valid value
        import_max = BGGGameImport(bgg_id=999999)
        assert import_max.bgg_id == 999999


class TestCSVImportSchema:
    """Test CSVImport schema validation"""

    def test_csv_import_valid(self):
        """Test CSVImport with valid CSV data"""
        csv_data = CSVImport(csv_data="bgg_id,title\n174430,Gloomhaven")
        assert csv_data.csv_data == "bgg_id,title\n174430,Gloomhaven"

    def test_csv_import_empty_rejected(self):
        """Test CSVImport rejects empty CSV data"""
        with pytest.raises(PydanticValidationError) as exc_info:
            CSVImport(csv_data="")

        errors = exc_info.value.errors()
        assert any("cannot be empty" in str(e.get("msg", "")).lower() for e in errors)

    def test_csv_import_whitespace_rejected(self):
        """Test CSVImport rejects whitespace-only CSV data"""
        with pytest.raises(PydanticValidationError) as exc_info:
            CSVImport(csv_data="   \n   ")

        errors = exc_info.value.errors()
        assert any("cannot be empty" in str(e.get("msg", "")).lower() for e in errors)

    def test_csv_import_multiline(self):
        """Test CSVImport with multiline CSV data"""
        csv_data = CSVImport(csv_data="id,name\n1,Game1\n2,Game2\n3,Game3")
        assert "Game1" in csv_data.csv_data
        assert "Game2" in csv_data.csv_data


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
        valid_tables = ["boardgames", "buy_list_games", "price_snapshots", "price_offers", "sleeves"]

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
        assert create.bgo_link is None
        assert create.lpg_rrp is None
        assert create.lpg_status is None

    def test_buy_list_create_all_fields(self):
        """Test BuyListGameCreate with all fields"""
        create = BuyListGameCreate(
            bgg_id=174430,
            rank=1,
            bgo_link="https://boardgameoracle.com/game/174430",
            lpg_rrp=150.00,
            lpg_status="Available"
        )

        assert create.bgg_id == 174430
        assert create.rank == 1
        assert create.bgo_link == "https://boardgameoracle.com/game/174430"
        assert create.lpg_rrp == 150.00
        assert create.lpg_status == "Available"

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
        assert update.bgo_link is None
        assert update.lpg_rrp is None
        assert update.lpg_status is None
        assert update.on_buy_list is None

    def test_buy_list_update_partial(self):
        """Test BuyListGameUpdate with partial fields"""
        update = BuyListGameUpdate(rank=5, on_buy_list=False)
        assert update.rank == 5
        assert update.on_buy_list is False
        assert update.bgo_link is None

    def test_buy_list_update_all_fields(self):
        """Test BuyListGameUpdate with all fields"""
        update = BuyListGameUpdate(
            rank=2,
            bgo_link="https://example.com",
            lpg_rrp=99.99,
            lpg_status="In Stock",
            on_buy_list=True
        )

        assert update.rank == 2
        assert update.bgo_link == "https://example.com"
        assert update.lpg_rrp == 99.99
        assert update.lpg_status == "In Stock"
        assert update.on_buy_list is True


class TestPriceSnapshotOutSchema:
    """Test PriceSnapshotOut schema"""

    def test_price_snapshot_minimal(self):
        """Test PriceSnapshotOut with minimal required fields"""
        snapshot = PriceSnapshotOut(
            id=1,
            game_id=100,
            checked_at="2025-12-27T10:00:00"
        )

        assert snapshot.id == 1
        assert snapshot.game_id == 100
        assert snapshot.checked_at == "2025-12-27T10:00:00"
        assert snapshot.low_price is None

    def test_price_snapshot_all_fields(self):
        """Test PriceSnapshotOut with all fields"""
        snapshot = PriceSnapshotOut(
            id=1,
            game_id=100,
            checked_at="2025-12-27T10:00:00",
            low_price=89.99,
            mean_price=95.00,
            best_price=85.00,
            best_store="Game Store",
            discount_pct=15.5,
            delta=-5.00
        )

        assert snapshot.id == 1
        assert snapshot.game_id == 100
        assert snapshot.low_price == 89.99
        assert snapshot.mean_price == 95.00
        assert snapshot.best_price == 85.00
        assert snapshot.best_store == "Game Store"
        assert snapshot.discount_pct == 15.5
        assert snapshot.delta == -5.00


class TestBuyListGameOutSchema:
    """Test BuyListGameOut schema"""

    def test_buy_list_game_out_minimal(self):
        """Test BuyListGameOut with minimal required fields"""
        game_out = BuyListGameOut(
            id=1,
            game_id=100,
            on_buy_list=True,
            created_at="2025-12-27T10:00:00",
            updated_at="2025-12-27T10:00:00",
            title="Test Game"
        )

        assert game_out.id == 1
        assert game_out.game_id == 100
        assert game_out.on_buy_list is True
        assert game_out.title == "Test Game"
        assert game_out.rank is None
        assert game_out.latest_price is None

    def test_buy_list_game_out_with_price(self):
        """Test BuyListGameOut with latest price snapshot"""
        price_snapshot = PriceSnapshotOut(
            id=1,
            game_id=100,
            checked_at="2025-12-27T10:00:00",
            best_price=85.00,
            best_store="Game Store"
        )

        game_out = BuyListGameOut(
            id=1,
            game_id=100,
            rank=1,
            bgo_link="https://example.com",
            lpg_rrp=100.00,
            lpg_status="Available",
            on_buy_list=True,
            created_at="2025-12-27T10:00:00",
            updated_at="2025-12-27T10:00:00",
            title="Gloomhaven",
            thumbnail_url="https://example.com/thumb.jpg",
            bgg_id=174430,
            latest_price=price_snapshot
        )

        assert game_out.title == "Gloomhaven"
        assert game_out.bgg_id == 174430
        assert game_out.latest_price is not None
        assert game_out.latest_price.best_price == 85.00
        assert game_out.latest_price.best_store == "Game Store"


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
            "bgo_link": "https://example.com"
        }

        create = BuyListGameCreate(**data)
        assert create.bgg_id == 174430
        assert create.rank == 1
        assert create.bgo_link == "https://example.com"
