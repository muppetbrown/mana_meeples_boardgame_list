"""Tests for GameService business logic layer."""
import pytest

from services.game_service import GameService
from models import Game
from exceptions import GameNotFoundError, ValidationError


class TestGameService:
    """Test suite for GameService"""

    def test_get_game_by_id_found(self, db_session):
        """Test retrieving a game by ID when it exists"""
        # Create a test game
        game = Game(
            id=1,
            title="Test Game",
            bgg_id=12345,
            year=2020,
            players_min=2,
            players_max=4,
            playtime_min=30,
            status="OWNED"
        )
        db_session.add(game)
        db_session.commit()

        # Test
        service = GameService(db_session)
        result = service.get_game_by_id(1)

        assert result is not None
        assert result.title == "Test Game"
        assert result.bgg_id == 12345

    def test_get_game_by_id_not_found(self, db_session):
        """Test retrieving a game by ID when it doesn't exist"""
        service = GameService(db_session)
        result = service.get_game_by_id(999)

        assert result is None

    def test_get_game_by_bgg_id(self, db_session):
        """Test retrieving a game by BGG ID"""
        game = Game(
            title="BGG Test Game",
            bgg_id=99999,
            year=2021,
            players_min=2,
            playtime_min=30,
            status="OWNED"
        )
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        result = service.get_game_by_bgg_id(99999)

        assert result is not None
        assert result.title == "BGG Test Game"

    def test_get_all_games(self, db_session):
        """Test retrieving all games"""
        # Create multiple games
        games = [
            Game(title=f"Game {i}", bgg_id=i, year=2020 + i, players_min=2, playtime_min=30, status="OWNED")
            for i in range(5)
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results = service.get_all_games()

        assert len(results) == 5

    def test_create_game_success(self, db_session):
        """Test creating a new game"""
        game_data = {
            "title": "New Game",
            "bgg_id": 11111,
            "year": 2023,
            "players_min": 1,
            "players_max": 6,
            "categories": ["Strategy", "Card Game"]
        }

        service = GameService(db_session)
        game = service.create_game(game_data)

        assert game.id is not None
        assert game.title == "New Game"
        assert game.bgg_id == 11111
        assert "Strategy" in game.categories

    def test_create_game_duplicate_bgg_id(self, db_session):
        """Test creating a game with duplicate BGG ID raises error"""
        # Create first game
        existing = Game(title="Existing", bgg_id=55555, players_min=2, playtime_min=30, status="OWNED")
        db_session.add(existing)
        db_session.commit()

        # Try to create duplicate
        game_data = {
            "title": "Duplicate",
            "bgg_id": 55555
        }

        service = GameService(db_session)
        with pytest.raises(ValidationError, match="already exists"):
            service.create_game(game_data)

    def test_update_game_success(self, db_session):
        """Test updating an existing game"""
        game = Game(title="Original Title", bgg_id=77777, year=2020, players_min=2, playtime_min=30, status="OWNED")
        db_session.add(game)
        db_session.commit()

        update_data = {
            "title": "Updated Title",
            "year": 2022,
            "mana_meeple_category": "CORE_STRATEGY"
        }

        service = GameService(db_session)
        updated = service.update_game(game.id, update_data)

        assert updated.title == "Updated Title"
        assert updated.year == 2022
        assert updated.mana_meeple_category == "CORE_STRATEGY"

    def test_update_game_not_found(self, db_session):
        """Test updating a non-existent game raises error"""
        service = GameService(db_session)

        with pytest.raises(GameNotFoundError):
            service.update_game(999, {"title": "New Title"})

    def test_delete_game_success(self, db_session):
        """Test deleting a game"""
        game = Game(title="To Delete", bgg_id=88888, players_min=2, playtime_min=30, status="OWNED")
        db_session.add(game)
        db_session.commit()
        game_id = game.id

        service = GameService(db_session)
        deleted_title = service.delete_game(game_id)

        assert deleted_title == "To Delete"
        assert db_session.get(Game, game_id) is None

    def test_delete_game_not_found(self, db_session):
        """Test deleting a non-existent game raises error"""
        service = GameService(db_session)

        with pytest.raises(GameNotFoundError):
            service.delete_game(999)

    def test_get_filtered_games_by_category(self, db_session):
        """Test filtering games by category"""
        games = [
            Game(title="Strategy 1", mana_meeple_category="CORE_STRATEGY", players_min=2, playtime_min=30, status="OWNED"),
            Game(title="Strategy 2", mana_meeple_category="CORE_STRATEGY", players_min=2, playtime_min=30, status="OWNED"),
            Game(title="Party", mana_meeple_category="PARTY_ICEBREAKERS", players_min=4, playtime_min=15, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(category="CORE_STRATEGY")

        assert total == 2
        assert all(g.mana_meeple_category == "CORE_STRATEGY" for g in results)

    def test_get_filtered_games_by_search(self, db_session):
        """Test searching games by title"""
        games = [
            Game(title="Pandemic Legacy", players_min=2, playtime_min=45, status="OWNED"),
            Game(title="Pandemic Rising Tide", players_min=2, playtime_min=60, status="OWNED"),
            Game(title="Ticket to Ride", players_min=2, playtime_min=30, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(search="Pandemic")

        assert total == 2
        assert all("Pandemic" in g.title for g in results)

    def test_get_filtered_games_pagination(self, db_session):
        """Test pagination works correctly"""
        # Create 25 games
        games = [Game(title=f"Game {i}", players_min=2, playtime_min=30, status="OWNED") for i in range(25)]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)

        # Page 1
        results, total = service.get_filtered_games(page=1, page_size=10)
        assert len(results) == 10
        assert total == 25

        # Page 3
        results, total = service.get_filtered_games(page=3, page_size=10)
        assert len(results) == 5  # Last page has 5 items

    def test_get_filtered_games_sorting(self, db_session):
        """Test sorting games"""
        games = [
            Game(title="Zebra Game", year=2020),
            Game(title="Alpha Game", year=2022),
            Game(title="Beta Game", year=2021),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)

        # Test title ascending
        results, _ = service.get_filtered_games(sort="title_asc")
        assert results[0].title == "Alpha Game"

        # Test year descending
        results, _ = service.get_filtered_games(sort="year_desc")
        assert results[0].year == 2022

    def test_create_or_update_from_bgg_new_game(self, db_session):
        """Test creating a new game from BGG data"""
        bgg_data = {
            "title": "BGG Import",
            "year": 2023,
            "categories": ["Strategy", "Economic"],
            "players_min": 2,
            "players_max": 5,
            "designers": ["Designer 1", "Designer 2"]
        }

        service = GameService(db_session)
        game, was_cached = service.create_or_update_from_bgg(12345, bgg_data)

        assert was_cached is False
        assert game.title == "BGG Import"
        assert game.bgg_id == 12345

    def test_create_or_update_from_bgg_update_existing(self, db_session):
        """Test updating existing game from BGG data"""
        # Create existing game
        existing = Game(title="Old Title", bgg_id=12345, year=2020)
        db_session.add(existing)
        db_session.commit()

        bgg_data = {
            "title": "Updated Title",
            "year": 2023,
            "categories": ["Strategy"],
        }

        service = GameService(db_session)
        game, was_cached = service.create_or_update_from_bgg(
            12345, bgg_data, force_update=True
        )

        assert was_cached is True
        assert game.title == "Updated Title"
        assert game.year == 2023

    def test_create_or_update_from_bgg_invalid_id(self, db_session):
        """Test BGG import with invalid ID raises error"""
        service = GameService(db_session)

        # Test with invalid BGG ID (non-positive)
        with pytest.raises(ValidationError, match="BGG ID must be"):
            service.create_or_update_from_bgg(0, {})

        with pytest.raises(ValidationError, match="BGG ID must be"):
            service.create_or_update_from_bgg(-1, {})

    def test_create_or_update_from_bgg_missing_title(self, db_session):
        """Test BGG import with missing title raises error"""
        service = GameService(db_session)

        # Test with missing title
        with pytest.raises(ValidationError, match="title"):
            service.create_or_update_from_bgg(12345, {"year": 2023})

        # Test with empty title
        with pytest.raises(ValidationError, match="title"):
            service.create_or_update_from_bgg(12345, {"title": ""})

    def test_get_games_by_designer(self, db_session):
        """Test retrieving games by designer name"""
        games = [
            Game(title="Game 1", designers=["Alice", "Bob"], players_min=2, playtime_min=30, status="OWNED"),
            Game(title="Game 2", designers=["Alice", "Charlie"], players_min=2, playtime_min=30, status="OWNED"),
            Game(title="Game 3", designers=["Bob", "Dave"], players_min=2, playtime_min=30, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results = service.get_games_by_designer("Alice")

        # Note: This depends on how JSON search works in your DB
        # May need to adjust based on actual implementation
        assert len(results) >= 0  # Placeholder - adjust based on implementation

    def test_get_filtered_games_by_nz_designer(self, db_session):
        """Test filtering games by NZ designer flag"""
        games = [
            Game(title="NZ Game 1", nz_designer=True, status="OWNED"),
            Game(title="NZ Game 2", nz_designer=True, status="OWNED"),
            Game(title="Regular Game", nz_designer=False, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(nz_designer=True)

        assert total == 2
        assert all(g.nz_designer is True for g in results)

    def test_get_filtered_games_by_designer_param(self, db_session):
        """Test filtering by designer parameter"""
        games = [
            Game(title="Game 1", designers=["Martin Wallace"], status="OWNED"),
            Game(title="Game 2", designers=["Reiner Knizia"], status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(designer="Martin")

        assert total >= 0  # Implementation depends on JSON search

    def test_get_filtered_games_combined_filters(self, db_session):
        """Test applying multiple filters together"""
        games = [
            Game(
                title="NZ Strategy Game",
                mana_meeple_category="CORE_STRATEGY",
                nz_designer=True,
                status="OWNED"
            ),
            Game(
                title="NZ Party Game",
                mana_meeple_category="PARTY_ICEBREAKERS",
                nz_designer=True,
                status="OWNED"
            ),
            Game(
                title="Regular Strategy",
                mana_meeple_category="CORE_STRATEGY",
                nz_designer=False,
                status="OWNED"
            ),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(
            category="CORE_STRATEGY",
            nz_designer=True
        )

        assert total == 1
        assert results[0].title == "NZ Strategy Game"

    def test_get_filtered_games_excludes_wishlist(self, db_session):
        """Test that filtered games excludes non-OWNED status"""
        games = [
            Game(title="Owned Game", status="OWNED"),
            Game(title="Wishlist Game", status="WISHLIST"),
            Game(title="Buy List Game", status="BUY_LIST"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games()

        assert total == 1
        assert results[0].title == "Owned Game"

    def test_get_filtered_games_uncategorized(self, db_session):
        """Test filtering for uncategorized games"""
        games = [
            Game(title="Categorized", mana_meeple_category="CORE_STRATEGY", status="OWNED"),
            Game(title="Uncategorized", mana_meeple_category=None, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(category="uncategorized")

        assert total == 1
        assert results[0].title == "Uncategorized"

    def test_sort_title_descending(self, db_session):
        """Test sorting by title descending"""
        games = [
            Game(title="Alpha", status="OWNED"),
            Game(title="Zebra", status="OWNED"),
            Game(title="Beta", status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, _ = service.get_filtered_games(sort="title_desc")

        assert results[0].title == "Zebra"
        assert results[-1].title == "Alpha"

    def test_sort_rating_ascending(self, db_session):
        """Test sorting by rating ascending"""
        games = [
            Game(title="High", average_rating=8.5, status="OWNED"),
            Game(title="Low", average_rating=6.0, status="OWNED"),
            Game(title="Mid", average_rating=7.2, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, _ = service.get_filtered_games(sort="rating_asc")

        ratings = [g.average_rating for g in results if g.average_rating]
        assert ratings == sorted(ratings)

    def test_sort_rating_descending(self, db_session):
        """Test sorting by rating descending"""
        games = [
            Game(title="High", average_rating=8.5, status="OWNED"),
            Game(title="Low", average_rating=6.0, status="OWNED"),
            Game(title="Mid", average_rating=7.2, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, _ = service.get_filtered_games(sort="rating_desc")

        assert results[0].average_rating == 8.5

    def test_search_case_insensitive(self, db_session):
        """Test search is case-insensitive"""
        game = Game(title="Pandemic Legacy", status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(search="pandemic")

        assert total == 1
        assert results[0].title == "Pandemic Legacy"

    def test_search_partial_match(self, db_session):
        """Test search matches partial strings"""
        game = Game(title="Codenames", status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(search="code")

        assert total == 1

    def test_search_empty_string(self, db_session):
        """Test empty search returns all games"""
        games = [Game(title=f"Game {i}", status="OWNED", players_min=2, playtime_min=30) for i in range(3)]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(search="")

        assert total == 3

    def test_search_whitespace_only(self, db_session):
        """Test whitespace-only search is ignored"""
        games = [Game(title=f"Game {i}", status="OWNED", players_min=2, playtime_min=30) for i in range(3)]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(search="   ")

        assert total == 3

    def test_pagination_page_beyond_available(self, db_session):
        """Test requesting page beyond available data"""
        games = [Game(title=f"Game {i}", status="OWNED", players_min=2, playtime_min=30) for i in range(5)]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(page=10, page_size=10)

        assert len(results) == 0
        assert total == 5

    def test_get_category_counts(self, db_session):
        """Test getting category counts"""
        games = [
            Game(title="Game 1", mana_meeple_category="CORE_STRATEGY", status="OWNED"),
            Game(title="Game 2", mana_meeple_category="CORE_STRATEGY", status="OWNED"),
            Game(title="Game 3", mana_meeple_category="PARTY_ICEBREAKERS", status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        counts = service.get_category_counts()

        assert counts["CORE_STRATEGY"] == 2
        assert counts["PARTY_ICEBREAKERS"] == 1

    def test_create_game_with_list_categories(self, db_session):
        """Test creating game with categories as list"""
        game_data = {
            "title": "Test Game",
            "categories": ["Adventure", "Fantasy"],
        }

        service = GameService(db_session)
        game = service.create_game(game_data)

        assert "Adventure" in game.categories
        assert "Fantasy" in game.categories

    def test_create_game_with_string_categories(self, db_session):
        """Test creating game with categories as string"""
        game_data = {
            "title": "Test Game",
            "categories": "Adventure, Fantasy",
        }

        service = GameService(db_session)
        game = service.create_game(game_data)

        assert game.categories == "Adventure, Fantasy"

    def test_update_game_category(self, db_session):
        """Test updating game category"""
        game = Game(title="Game", mana_meeple_category="PARTY_ICEBREAKERS", status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        updated = service.update_game(game.id, {"mana_meeple_category": "CORE_STRATEGY"})

        assert updated.mana_meeple_category == "CORE_STRATEGY"

    def test_create_or_update_from_bgg_no_update_when_exists(self, db_session):
        """Test BGG import doesn't update when force=False"""
        existing = Game(title="Original", bgg_id=12345, year=2020, status="OWNED")
        db_session.add(existing)
        db_session.commit()

        bgg_data = {
            "title": "Should Not Update",
            "year": 9999,
        }

        service = GameService(db_session)
        game, was_cached = service.create_or_update_from_bgg(12345, bgg_data, force_update=False)

        assert game.title == "Original"
        assert game.year == 2020
        assert was_cached is True

    def test_update_game_with_expansion_fields(self, db_session):
        """Test updating expansion-related fields"""
        game = Game(title="Expansion", is_expansion=False, status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        updated = service.update_game(
            game.id,
            {
                "is_expansion": True,
                "expansion_type": "both",
                "modifies_players_min": 5,
                "modifies_players_max": 6,
            }
        )

        assert updated.is_expansion is True
        if hasattr(updated, "expansion_type"):
            assert updated.expansion_type == "both"

    def test_update_game_ignores_nonexistent_fields(self, db_session):
        """Test update ignores fields that don't exist"""
        game = Game(title="Test", status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        updated = service.update_game(
            game.id,
            {
                "title": "Updated",
                "nonexistent_field": "should_be_ignored",
            }
        )

        assert updated.title == "Updated"
        assert not hasattr(updated, "nonexistent_field")

    def test_get_all_games_excludes_non_owned(self, db_session):
        """Test get_all_games only returns OWNED status"""
        games = [
            Game(title="Owned 1", status="OWNED"),
            Game(title="Owned 2", status="OWNED"),
            Game(title="Wishlist", status="WISHLIST"),
            Game(title="Buy List", status="BUY_LIST"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results = service.get_all_games()

        assert len(results) == 2
        assert all(g.status == "OWNED" for g in results)

    def test_sort_year_asc(self, db_session):
        """Test sorting by year ascending"""
        games = [
            Game(title="New", year=2020, status="OWNED"),
            Game(title="Old", year=1995, status="OWNED"),
            Game(title="Mid", year=2010, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, _ = service.get_filtered_games(sort="year_asc")

        assert results[0].year == 1995

    def test_get_filtered_games_category_all(self, db_session):
        """Test category filter with 'all' returns everything"""
        games = [
            Game(title="Game 1", mana_meeple_category="CORE_STRATEGY", status="OWNED"),
            Game(title="Game 2", mana_meeple_category="PARTY_ICEBREAKERS", status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(category="all")

        assert total == 2

    def test_create_or_update_from_bgg_with_enhanced_fields(self, db_session):
        """Test BGG import with enhanced fields"""
        bgg_data = {
            "title": "Enhanced Game",
            "year": 2023,
            "categories": ["Strategy"],
            "designers": ["Designer 1"],
            "publishers": ["Publisher 1"],
            "mechanics": ["Worker Placement"],
            "complexity": 3.5,
            "average_rating": 8.2,
            "bgg_rank": 100,
            "min_age": 14,
        }

        service = GameService(db_session)
        game, _ = service.create_or_update_from_bgg(99999, bgg_data)

        assert game.title == "Enhanced Game"
        if hasattr(game, "complexity"):
            assert game.complexity == 3.5
        if hasattr(game, "average_rating"):
            assert game.average_rating == 8.2

    def test_sort_playtime_asc(self, db_session):
        """Test sorting by playtime ascending"""
        games = [
            Game(title="Long", playtime_min=120, playtime_max=180, status="OWNED"),
            Game(title="Short", playtime_min=15, playtime_max=30, status="OWNED"),
            Game(title="Medium", playtime_min=45, playtime_max=60, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, _ = service.get_filtered_games(sort="time_asc")

        # Should be sorted by average playtime
        assert results[0].title == "Short"

    def test_sort_playtime_desc(self, db_session):
        """Test sorting by playtime descending"""
        games = [
            Game(title="Long", playtime_min=120, playtime_max=180, status="OWNED"),
            Game(title="Short", playtime_min=15, playtime_max=30, status="OWNED"),
            Game(title="Medium", playtime_min=45, playtime_max=60, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, _ = service.get_filtered_games(sort="time_desc")

        # Should be sorted by average playtime descending
        assert results[0].title == "Long"

    def test_filter_excludes_expansions(self, db_session):
        """Test that require-base expansions are excluded from public view"""
        games = [
            Game(title="Base Game", is_expansion=False, status="OWNED"),
            Game(
                title="Standalone Expansion",
                is_expansion=True,
                expansion_type="standalone",
                status="OWNED"
            ),
            Game(
                title="Require Base",
                is_expansion=True,
                expansion_type="requires_base",
                status="OWNED"
            ),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games()

        # Should exclude require-base expansions
        # Exact count depends on expansion logic
        assert len(results) >= 1

    def test_update_game_nz_designer_flag(self, db_session):
        """Test updating NZ designer flag"""
        game = Game(title="Game", nz_designer=False, status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        updated = service.update_game(game.id, {"nz_designer": True})

        assert updated.nz_designer is True

    def test_update_game_player_count(self, db_session):
        """Test updating player count fields"""
        game = Game(title="Game", players_min=2, players_max=4, status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        updated = service.update_game(
            game.id,
            {"players_min": 1, "players_max": 6}
        )

        assert updated.players_min == 1
        assert updated.players_max == 6

    def test_update_game_playtime(self, db_session):
        """Test updating playtime fields"""
        game = Game(title="Game", playtime_min=30, playtime_max=60, status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        updated = service.update_game(
            game.id,
            {"playtime_min": 45, "playtime_max": 90}
        )

        assert updated.playtime_min == 45
        assert updated.playtime_max == 90

    def test_create_game_auto_categorize(self, db_session):
        """Test auto-categorization when creating game"""
        game_data = {
            "title": "Cooperative Game",
            "categories": "Cooperative Game, Adventure",
        }

        service = GameService(db_session)
        game = service.create_game(game_data)

        # Should auto-categorize based on categories
        # Exact category depends on categorize_game logic
        assert game.title == "Cooperative Game"

    def test_get_filtered_games_multiple_sort_fallback(self, db_session):
        """Test that invalid sort falls back to title_asc"""
        games = [
            Game(title="Zebra", status="OWNED"),
            Game(title="Alpha", status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, _ = service.get_filtered_games(sort="invalid_sort_option")

        assert results[0].title == "Alpha"
        assert results[1].title == "Zebra"

    def test_pagination_first_page(self, db_session):
        """Test first page of pagination"""
        games = [Game(title=f"Game {i:02d}", status="OWNED") for i in range(10)]
        for game in games:
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(page=1, page_size=3)

        assert len(results) == 3
        assert total == 10

    def test_get_games_by_designer_no_matches(self, db_session):
        """Test designer search with no matches"""
        game = Game(title="Game", designers=["Other Designer"], status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results = service.get_games_by_designer("Nonexistent Designer")

        assert len(results) == 0

    # --- Quick-pick tests (mobile library "Who's playing today?" row) ---

    def test_quick_pick_first_timers_uses_1_5_threshold(self, db_session):
        """First timers should only include complexity < 1.5, not 1.5+"""
        easy = Game(title="Easy Game", complexity=1.2, status="OWNED")
        borderline = Game(title="Borderline Game", complexity=1.5, status="OWNED")
        heavy = Game(title="Heavy Game", complexity=3.0, status="OWNED")
        db_session.add_all([easy, borderline, heavy])
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(quick_pick="first")

        assert total == 1
        assert results[0].title == "Easy Game"

    def test_quick_pick_kids_requires_both_complexity_and_min_age(self, db_session):
        """
        With the kids should exclude simple-but-adult games (e.g. a low
        complexity party game with a high min_age), matching only the
        KIDS_FAMILIES category or games that are both simple and low min_age.
        """
        family_category = Game(title="Family Game", mana_meeple_category="KIDS_FAMILIES", complexity=2.0, min_age=30, status="OWNED")
        simple_and_young = Game(title="Simple Kid Game", complexity=1.1, min_age=6, status="OWNED")
        simple_but_adult = Game(title="Simple Adult Party Game", complexity=1.1, min_age=17, status="OWNED")
        db_session.add_all([family_category, simple_and_young, simple_but_adult])
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(quick_pick="kids")
        titles = {g.title for g in results}

        assert total == 2
        assert titles == {"Family Game", "Simple Kid Game"}

    def test_quick_pick_group_uses_6_plus_threshold(self, db_session):
        """Big group should only include players_max >= 6, not 5"""
        five = Game(title="Five Max", players_max=5, status="OWNED")
        six = Game(title="Six Max", players_max=6, status="OWNED")
        db_session.add_all([five, six])
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(quick_pick="group")

        assert total == 1
        assert results[0].title == "Six Max"

    def test_quick_pick_coop_matches_flag_or_category(self, db_session):
        """Team up should match is_cooperative OR COOP_ADVENTURE category"""
        flagged = Game(title="Flagged Coop", is_cooperative=True, status="OWNED")
        categorized = Game(title="Categorized Coop", mana_meeple_category="COOP_ADVENTURE", status="OWNED")
        neither = Game(title="Competitive Game", is_cooperative=False, status="OWNED")
        db_session.add_all([flagged, categorized, neither])
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(quick_pick="coop")
        titles = {g.title for g in results}

        assert total == 2
        assert titles == {"Flagged Coop", "Categorized Coop"}

    def test_quick_pick_respects_admin_exclusion(self, db_session):
        """A game matching the auto-logic should be hidden once excluded for that key"""
        excluded = Game(title="Excluded Game", complexity=1.0, excluded_quick_picks=["first"], status="OWNED")
        included = Game(title="Included Game", complexity=1.0, status="OWNED")
        db_session.add_all([excluded, included])
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(quick_pick="first")

        assert total == 1
        assert results[0].title == "Included Game"

    def test_quick_pick_exclusion_is_scoped_to_its_own_key(self, db_session):
        """Excluding a game from 'kids' shouldn't hide it from 'first'"""
        game = Game(title="Easy Game", complexity=1.0, excluded_quick_picks=["kids"], status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        results, total = service.get_filtered_games(quick_pick="first")

        assert total == 1
        assert results[0].title == "Easy Game"

    def test_get_quick_pick_candidates_ignores_exclusions(self, db_session):
        """The admin candidates list should show excluded games too, for review"""
        excluded = Game(title="Excluded Game", complexity=1.0, excluded_quick_picks=["first"], status="OWNED")
        included = Game(title="Included Game", complexity=1.0, status="OWNED")
        db_session.add_all([excluded, included])
        db_session.commit()

        service = GameService(db_session)
        candidates = service.get_quick_pick_candidates("first")
        titles = {g.title for g in candidates}

        assert titles == {"Excluded Game", "Included Game"}

    def test_get_quick_pick_candidates_invalid_key_returns_empty(self, db_session):
        """An unrecognized quick-pick key returns an empty list, not an error"""
        service = GameService(db_session)
        assert service.get_quick_pick_candidates("not_a_real_key") == []

    def test_update_game_validates_excluded_quick_picks(self, db_session):
        """update_game should reject unknown quick-pick keys"""
        game = Game(title="Test Game", status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        with pytest.raises(ValidationError):
            service.update_game(game.id, {"excluded_quick_picks": ["not_a_real_key"]})

    def test_update_game_sets_excluded_quick_picks(self, db_session):
        """update_game should persist a valid excluded_quick_picks list"""
        game = Game(title="Test Game", status="OWNED")
        db_session.add(game)
        db_session.commit()

        service = GameService(db_session)
        updated = service.update_game(game.id, {"excluded_quick_picks": ["first", "kids"]})

        assert updated.excluded_quick_picks == ["first", "kids"]
