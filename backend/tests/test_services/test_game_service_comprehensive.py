"""
Comprehensive tests for GameService.
Tests all filtering, sorting, CRUD operations, and edge cases.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from models import Game
from services.game_service import GameService
from exceptions import GameNotFoundError, ValidationError


class TestGameServiceBasicQueries:
    """Tests for basic game queries"""

    def test_get_game_by_id_found(self, db_session):
        """Should return game when found by ID"""
        game = Game(title="Test Game", bgg_id=12345, status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        result = service.get_game_by_id(game.id)

        assert result is not None
        assert result.title == "Test Game"

    def test_get_game_by_id_not_found(self, db_session):
        """Should return None when game not found"""
        service = GameService(db_session)
        result = service.get_game_by_id(99999)

        assert result is None

    def test_get_game_by_bgg_id_found(self, db_session):
        """Should return game when found by BGG ID"""
        game = Game(title="BGG Game", bgg_id=54321, status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        result = service.get_game_by_bgg_id(54321)

        assert result is not None
        assert result.title == "BGG Game"

    def test_get_game_by_bgg_id_not_found(self, db_session):
        """Should return None when BGG ID not found"""
        service = GameService(db_session)
        result = service.get_game_by_bgg_id(99999)

        assert result is None

    def test_get_all_games_only_owned(self, db_session):
        """Should only return OWNED games"""
        owned = Game(title="Owned Game", bgg_id=1001, status="OWNED")
        wishlist = Game(title="Wishlist Game", bgg_id=1002, status="WISHLIST")
        buy_list = Game(title="Buy List Game", bgg_id=1003, status="BUY_LIST")
        null_status = Game(title="Null Status Game", bgg_id=1004, status=None)

        db_session.add_all([owned, wishlist, buy_list, null_status])
        db_session.commit()

        service = GameService(db_session)
        games = service.get_all_games()

        titles = [g.title for g in games]
        assert "Owned Game" in titles
        assert "Null Status Game" in titles  # None defaults to OWNED
        assert "Wishlist Game" not in titles
        assert "Buy List Game" not in titles


class TestGameServiceFiltering:
    """Tests for get_filtered_games with various filter combinations"""

    def test_filter_by_search_title(self, db_session):
        """Should filter by title search"""
        game1 = Game(title="Pandemic", bgg_id=2001, status="OWNED")
        game2 = Game(title="Catan", bgg_id=2002, status="OWNED")
        game3 = Game(title="Pandemic Legacy", bgg_id=2003, status="OWNED")

        db_session.add_all([game1, game2, game3])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(search="Pandemic")

        assert total == 2
        titles = [g.title for g in games]
        assert "Pandemic" in titles
        assert "Pandemic Legacy" in titles
        assert "Catan" not in titles

    def test_filter_by_search_designers(self, db_session):
        """Should filter by designer search"""
        game1 = Game(title="Pandemic", bgg_id=2101, designers=["Matt Leacock"], status="OWNED")
        game2 = Game(title="Ticket to Ride", bgg_id=2102, designers=["Alan Moon"], status="OWNED")

        db_session.add_all([game1, game2])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(search="Matt Leacock")

        assert total == 1
        assert games[0].title == "Pandemic"

    def test_filter_by_category(self, db_session):
        """Should filter by category"""
        coop = Game(title="Coop Game", bgg_id=2201, mana_meeple_category="COOP_ADVENTURE", status="OWNED")
        strategy = Game(title="Strategy Game", bgg_id=2202, mana_meeple_category="CORE_STRATEGY", status="OWNED")

        db_session.add_all([coop, strategy])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(category="COOP_ADVENTURE")

        assert total == 1
        assert games[0].title == "Coop Game"

    def test_filter_by_category_uncategorized(self, db_session):
        """Should filter uncategorized games"""
        categorized = Game(title="Categorized", bgg_id=2301, mana_meeple_category="GATEWAY_STRATEGY", status="OWNED")
        uncategorized = Game(title="Uncategorized", bgg_id=2302, mana_meeple_category=None, status="OWNED")

        db_session.add_all([categorized, uncategorized])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(category="uncategorized")

        assert total == 1
        assert games[0].title == "Uncategorized"

    def test_filter_by_nz_designer_true(self, db_session):
        """Should filter NZ designer games"""
        nz = Game(title="NZ Game", bgg_id=2401, nz_designer=True, status="OWNED")
        other = Game(title="Other Game", bgg_id=2402, nz_designer=False, status="OWNED")

        db_session.add_all([nz, other])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(nz_designer=True)

        assert total == 1
        assert games[0].title == "NZ Game"

    def test_filter_by_nz_designer_false(self, db_session):
        """Should filter non-NZ designer games"""
        nz = Game(title="NZ Game", bgg_id=2501, nz_designer=True, status="OWNED")
        other = Game(title="Other Game", bgg_id=2502, nz_designer=False, status="OWNED")

        db_session.add_all([nz, other])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(nz_designer=False)

        assert total == 1
        assert games[0].title == "Other Game"

    def test_filter_by_player_count(self, db_session):
        """Should filter by player count"""
        two_player = Game(title="Two Player", bgg_id=2601, players_min=2, players_max=2, status="OWNED")
        four_player = Game(title="Four Player", bgg_id=2602, players_min=3, players_max=5, status="OWNED")

        db_session.add_all([two_player, four_player])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(players=4)

        assert total == 1
        assert games[0].title == "Four Player"

    def test_filter_by_complexity_min(self, db_session):
        """Should filter by minimum complexity"""
        light = Game(title="Light Game", bgg_id=2701, complexity=1.5, status="OWNED")
        heavy = Game(title="Heavy Game", bgg_id=2702, complexity=4.2, status="OWNED")

        db_session.add_all([light, heavy])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(complexity_min=3.0)

        assert total == 1
        assert games[0].title == "Heavy Game"

    def test_filter_by_complexity_max(self, db_session):
        """Should filter by maximum complexity"""
        light = Game(title="Light Game", bgg_id=2801, complexity=1.5, status="OWNED")
        heavy = Game(title="Heavy Game", bgg_id=2802, complexity=4.2, status="OWNED")

        db_session.add_all([light, heavy])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(complexity_max=2.0)

        assert total == 1
        assert games[0].title == "Light Game"

    def test_filter_by_complexity_range(self, db_session):
        """Should filter by complexity range"""
        light = Game(title="Light", bgg_id=2901, complexity=1.5, status="OWNED")
        medium = Game(title="Medium", bgg_id=2902, complexity=2.5, status="OWNED")
        heavy = Game(title="Heavy", bgg_id=2903, complexity=4.2, status="OWNED")

        db_session.add_all([light, medium, heavy])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(complexity_min=2.0, complexity_max=3.0)

        assert total == 1
        assert games[0].title == "Medium"

    def test_filter_combined(self, db_session):
        """Should handle multiple filters combined"""
        game1 = Game(
            title="Target Game",
            bgg_id=3001,
            mana_meeple_category="COOP_ADVENTURE",
            nz_designer=True,
            complexity=2.5,
            status="OWNED"
        )
        game2 = Game(
            title="Other Coop",
            bgg_id=3002,
            mana_meeple_category="COOP_ADVENTURE",
            nz_designer=False,
            complexity=2.5,
            status="OWNED"
        )
        game3 = Game(
            title="Strategy",
            bgg_id=3003,
            mana_meeple_category="CORE_STRATEGY",
            nz_designer=True,
            complexity=2.5,
            status="OWNED"
        )

        db_session.add_all([game1, game2, game3])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(
            category="COOP_ADVENTURE",
            nz_designer=True
        )

        assert total == 1
        assert games[0].title == "Target Game"

    def test_filter_excludes_requires_base_expansions(self, db_session):
        """Should exclude expansions with requires_base type"""
        base = Game(title="Base Game", bgg_id=3101, status="OWNED")
        standalone = Game(
            title="Standalone Expansion",
            bgg_id=3102,
            is_expansion=True,
            expansion_type="standalone",
            status="OWNED"
        )
        requires_base = Game(
            title="Requires Base",
            bgg_id=3103,
            is_expansion=True,
            expansion_type="requires_base",
            status="OWNED"
        )

        db_session.add_all([base, standalone, requires_base])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games()

        titles = [g.title for g in games]
        assert "Base Game" in titles
        assert "Standalone Expansion" in titles
        assert "Requires Base" not in titles


class TestGameServiceSorting:
    """Tests for sorting functionality"""

    def test_sort_title_asc(self, db_session):
        """Should sort by title ascending"""
        c = Game(title="Catan", bgg_id=4001, status="OWNED")
        a = Game(title="Azul", bgg_id=4002, status="OWNED")
        b = Game(title="Brass", bgg_id=4003, status="OWNED")

        db_session.add_all([c, a, b])
        db_session.commit()

        service = GameService(db_session)
        games, _ = service.get_filtered_games(sort="title_asc")

        assert [g.title for g in games] == ["Azul", "Brass", "Catan"]

    def test_sort_title_desc(self, db_session):
        """Should sort by title descending"""
        c = Game(title="Catan", bgg_id=4101, status="OWNED")
        a = Game(title="Azul", bgg_id=4102, status="OWNED")
        b = Game(title="Brass", bgg_id=4103, status="OWNED")

        db_session.add_all([c, a, b])
        db_session.commit()

        service = GameService(db_session)
        games, _ = service.get_filtered_games(sort="title_desc")

        assert [g.title for g in games] == ["Catan", "Brass", "Azul"]

    def test_sort_year_desc(self, db_session):
        """Should sort by year descending"""
        old = Game(title="Old", bgg_id=4201, year=1995, status="OWNED")
        mid = Game(title="Mid", bgg_id=4202, year=2010, status="OWNED")
        new = Game(title="New", bgg_id=4203, year=2023, status="OWNED")

        db_session.add_all([old, mid, new])
        db_session.commit()

        service = GameService(db_session)
        games, _ = service.get_filtered_games(sort="year_desc")

        assert games[0].title == "New"
        assert games[-1].title == "Old"

    def test_sort_year_asc(self, db_session):
        """Should sort by year ascending"""
        old = Game(title="Old", bgg_id=4301, year=1995, status="OWNED")
        new = Game(title="New", bgg_id=4302, year=2023, status="OWNED")

        db_session.add_all([old, new])
        db_session.commit()

        service = GameService(db_session)
        games, _ = service.get_filtered_games(sort="year_asc")

        assert games[0].title == "Old"
        assert games[-1].title == "New"

    def test_sort_rating_desc(self, db_session):
        """Should sort by rating descending"""
        low = Game(title="Low", bgg_id=4401, average_rating=5.5, status="OWNED")
        high = Game(title="High", bgg_id=4402, average_rating=8.9, status="OWNED")

        db_session.add_all([low, high])
        db_session.commit()

        service = GameService(db_session)
        games, _ = service.get_filtered_games(sort="rating_desc")

        assert games[0].title == "High"

    def test_sort_rating_asc(self, db_session):
        """Should sort by rating ascending"""
        low = Game(title="Low", bgg_id=4501, average_rating=5.5, status="OWNED")
        high = Game(title="High", bgg_id=4502, average_rating=8.9, status="OWNED")

        db_session.add_all([low, high])
        db_session.commit()

        service = GameService(db_session)
        games, _ = service.get_filtered_games(sort="rating_asc")

        assert games[0].title == "Low"

    def test_sort_time_asc(self, db_session):
        """Should sort by playtime ascending"""
        long = Game(title="Long", bgg_id=4601, playtime_min=120, playtime_max=180, status="OWNED")
        short = Game(title="Short", bgg_id=4602, playtime_min=15, playtime_max=30, status="OWNED")

        db_session.add_all([long, short])
        db_session.commit()

        service = GameService(db_session)
        games, _ = service.get_filtered_games(sort="time_asc")

        assert games[0].title == "Short"

    def test_sort_time_desc(self, db_session):
        """Should sort by playtime descending"""
        long = Game(title="Long", bgg_id=4701, playtime_min=120, playtime_max=180, status="OWNED")
        short = Game(title="Short", bgg_id=4702, playtime_min=15, playtime_max=30, status="OWNED")

        db_session.add_all([long, short])
        db_session.commit()

        service = GameService(db_session)
        games, _ = service.get_filtered_games(sort="time_desc")

        assert games[0].title == "Long"

    def test_sort_default(self, db_session):
        """Invalid sort should default to title_asc"""
        c = Game(title="Catan", bgg_id=4801, status="OWNED")
        a = Game(title="Azul", bgg_id=4802, status="OWNED")

        db_session.add_all([c, a])
        db_session.commit()

        service = GameService(db_session)
        games, _ = service.get_filtered_games(sort="invalid_sort")

        assert games[0].title == "Azul"


class TestGameServicePagination:
    """Tests for pagination functionality"""

    def test_pagination_first_page(self, db_session):
        """Should return first page correctly"""
        for i in range(10):
            db_session.add(Game(title=f"Game {i:02d}", bgg_id=5000+i, status="OWNED"))
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(page=1, page_size=3)

        assert len(games) == 3
        assert total == 10

    def test_pagination_second_page(self, db_session):
        """Should return second page correctly"""
        for i in range(10):
            db_session.add(Game(title=f"Game {i:02d}", bgg_id=5100+i, status="OWNED"))
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(page=2, page_size=3, sort="title_asc")

        assert len(games) == 3
        assert total == 10
        # Second page should have games 03, 04, 05
        assert games[0].title == "Game 03"

    def test_pagination_last_page_partial(self, db_session):
        """Should handle partial last page"""
        for i in range(5):
            db_session.add(Game(title=f"Game {i}", bgg_id=5200+i, status="OWNED"))
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(page=2, page_size=3)

        assert len(games) == 2  # Only 2 items on second page
        assert total == 5

    def test_pagination_beyond_last_page(self, db_session):
        """Should return empty list for page beyond data"""
        for i in range(3):
            db_session.add(Game(title=f"Game {i}", bgg_id=5300+i, status="OWNED"))
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(page=10, page_size=3)

        assert len(games) == 0
        assert total == 3


class TestGameServiceCRUD:
    """Tests for CRUD operations"""

    def test_create_game_minimal(self, db_session):
        """Should create game with minimal data"""
        service = GameService(db_session)
        game = service.create_game({"title": "New Game"})

        assert game.id is not None
        assert game.title == "New Game"
        assert game.status == "OWNED"  # Default

    def test_create_game_full_data(self, db_session):
        """Should create game with full data"""
        service = GameService(db_session)
        game = service.create_game({
            "title": "Full Game",
            "year": 2023,
            "players_min": 2,
            "players_max": 4,
            "playtime_min": 30,
            "playtime_max": 60,
            "bgg_id": 5500,
            "mana_meeple_category": "GATEWAY_STRATEGY",
            "nz_designer": True,
        })

        assert game.title == "Full Game"
        assert game.year == 2023
        assert game.players_min == 2
        assert game.players_max == 4
        assert game.mana_meeple_category == "GATEWAY_STRATEGY"
        assert game.nz_designer is True

    def test_create_game_empty_title_fails(self, db_session):
        """Should reject game with empty title"""
        service = GameService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.create_game({"title": ""})

        assert "Title is required" in str(exc_info.value)

    def test_create_game_whitespace_title_fails(self, db_session):
        """Should reject game with whitespace-only title"""
        service = GameService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.create_game({"title": "   "})

        assert "Title is required" in str(exc_info.value)

    def test_create_game_duplicate_bgg_id_fails(self, db_session):
        """Should reject duplicate BGG ID"""
        existing = Game(title="Existing", bgg_id=5600, status="OWNED")
        db_session.add(existing)
        db_session.commit()

        service = GameService(db_session)
        with pytest.raises(ValidationError) as exc_info:
            service.create_game({"title": "Duplicate", "bgg_id": 5600})

        assert "BGG ID already exists" in str(exc_info.value)

    def test_create_game_invalid_category_fails(self, db_session):
        """Should reject invalid category"""
        service = GameService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.create_game({
                "title": "Invalid Category",
                "mana_meeple_category": "INVALID"
            })

        assert "Invalid category" in str(exc_info.value)

    def test_update_game_success(self, db_session):
        """Should update game successfully"""
        game = Game(title="Original", bgg_id=5700, status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        updated = service.update_game(game.id, {"title": "Updated"})

        assert updated.title == "Updated"

    def test_update_game_not_found(self, db_session):
        """Should raise error for nonexistent game"""
        service = GameService(db_session)

        with pytest.raises(GameNotFoundError):
            service.update_game(99999, {"title": "Updated"})

    def test_update_game_empty_title_fails(self, db_session):
        """Should reject update with empty title"""
        game = Game(title="Original", bgg_id=5800, status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        with pytest.raises(ValidationError) as exc_info:
            service.update_game(game.id, {"title": ""})

        assert "Title is required" in str(exc_info.value)

    def test_update_game_invalid_category_fails(self, db_session):
        """Should reject update with invalid category"""
        game = Game(title="Original", bgg_id=5900, status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        with pytest.raises(ValidationError):
            service.update_game(game.id, {"mana_meeple_category": "INVALID"})

    def test_delete_game_success(self, db_session):
        """Should delete game successfully"""
        game = Game(title="To Delete", bgg_id=6000, status="OWNED")
        db_session.add(game)
        db_session.commit()
        game_id = game.id

        service = GameService(db_session)
        title = service.delete_game(game_id)

        assert title == "To Delete"
        assert service.get_game_by_id(game_id) is None

    def test_delete_game_not_found(self, db_session):
        """Should raise error for nonexistent game"""
        service = GameService(db_session)

        with pytest.raises(GameNotFoundError):
            service.delete_game(99999)


class TestGameServiceBGGImport:
    """Tests for BGG import functionality"""

    def test_create_from_bgg_new_game(self, db_session):
        """Should create new game from BGG data"""
        service = GameService(db_session)
        bgg_data = {
            "title": "Imported Game",
            "year": 2020,
            "players_min": 2,
            "players_max": 4,
            "categories": ["Strategy", "Card Game"],
        }

        game, was_cached = service.create_or_update_from_bgg(6100, bgg_data)

        assert game.title == "Imported Game"
        assert game.bgg_id == 6100
        assert was_cached is False

    def test_create_from_bgg_existing_game_cached(self, db_session):
        """Should return cached game without force update"""
        existing = Game(title="Existing", bgg_id=6200, status="OWNED")
        db_session.add(existing)
        db_session.commit()

        service = GameService(db_session)
        bgg_data = {"title": "Updated Title"}

        game, was_cached = service.create_or_update_from_bgg(6200, bgg_data)

        assert game.title == "Existing"  # Not updated
        assert was_cached is True

    def test_create_from_bgg_force_update(self, db_session):
        """Should update game with force_update=True"""
        existing = Game(title="Existing", bgg_id=6300, status="OWNED")
        db_session.add(existing)
        db_session.commit()

        service = GameService(db_session)
        bgg_data = {"title": "Updated Title"}

        game, was_cached = service.create_or_update_from_bgg(6300, bgg_data, force_update=True)

        assert game.title == "Updated Title"
        assert was_cached is True

    def test_create_from_bgg_invalid_bgg_id(self, db_session):
        """Should reject invalid BGG ID"""
        service = GameService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.create_or_update_from_bgg(0, {"title": "Test"})

        assert "positive integer" in str(exc_info.value)

    def test_create_from_bgg_missing_title(self, db_session):
        """Should reject BGG data without title"""
        service = GameService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.create_or_update_from_bgg(6400, {})

        assert "title" in str(exc_info.value)


class TestGameServiceByDesigner:
    """Tests for get_games_by_designer"""

    def test_find_games_by_designer(self, db_session):
        """Should find games by designer name"""
        game1 = Game(title="Game 1", bgg_id=6500, designers=["Designer A"], status="OWNED")
        game2 = Game(title="Game 2", bgg_id=6501, designers=["Designer B"], status="OWNED")

        db_session.add_all([game1, game2])
        db_session.commit()

        service = GameService(db_session)
        games = service.get_games_by_designer("Designer A")

        assert len(games) == 1
        assert games[0].title == "Game 1"

    def test_find_games_partial_match(self, db_session):
        """Should find games with partial designer match"""
        game = Game(title="Game", bgg_id=6600, designers=["Matt Leacock"], status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        games = service.get_games_by_designer("Leacock")

        assert len(games) == 1

    def test_find_games_case_insensitive(self, db_session):
        """Should find games case-insensitively"""
        game = Game(title="Game", bgg_id=6700, designers=["Matt Leacock"], status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        games = service.get_games_by_designer("matt leacock")

        assert len(games) == 1


class TestGameServiceCategoryCounts:
    """Tests for get_category_counts"""

    def test_category_counts(self, db_session):
        """Should return correct category counts"""
        coop1 = Game(title="Coop 1", bgg_id=6800, mana_meeple_category="COOP_ADVENTURE", status="OWNED")
        coop2 = Game(title="Coop 2", bgg_id=6801, mana_meeple_category="COOP_ADVENTURE", status="OWNED")
        strategy = Game(title="Strategy", bgg_id=6802, mana_meeple_category="CORE_STRATEGY", status="OWNED")
        uncategorized = Game(title="None", bgg_id=6803, mana_meeple_category=None, status="OWNED")

        db_session.add_all([coop1, coop2, strategy, uncategorized])
        db_session.commit()

        service = GameService(db_session)
        counts = service.get_category_counts()

        assert counts["COOP_ADVENTURE"] == 2
        assert counts["CORE_STRATEGY"] == 1
        assert counts["uncategorized"] == 1
        assert counts["all"] == 4

    def test_category_counts_excludes_non_owned(self, db_session):
        """Should exclude non-OWNED games from counts"""
        owned = Game(title="Owned", bgg_id=6900, mana_meeple_category="GATEWAY_STRATEGY", status="OWNED")
        wishlist = Game(title="Wishlist", bgg_id=6901, mana_meeple_category="GATEWAY_STRATEGY", status="WISHLIST")

        db_session.add_all([owned, wishlist])
        db_session.commit()

        service = GameService(db_session)
        counts = service.get_category_counts()

        assert counts["GATEWAY_STRATEGY"] == 1


class TestGameServiceEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_filter_with_special_chars_in_search(self, db_session):
        """Should handle special characters in search"""
        game = Game(title="7 Wonders: Duel", bgg_id=7000, status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(search="7 Wonders:")

        assert total == 1

    def test_filter_with_empty_search(self, db_session):
        """Should ignore empty/whitespace search"""
        game = Game(title="Test", bgg_id=7100, status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(search="   ")

        assert total == 1

    def test_filter_null_complexity_excluded_from_range(self, db_session):
        """Games with null complexity should be excluded from complexity filter"""
        with_complexity = Game(title="With", bgg_id=7200, complexity=2.5, status="OWNED")
        null_complexity = Game(title="Without", bgg_id=7201, complexity=None, status="OWNED")

        db_session.add_all([with_complexity, null_complexity])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(complexity_min=2.0)

        assert total == 1
        assert games[0].title == "With"
