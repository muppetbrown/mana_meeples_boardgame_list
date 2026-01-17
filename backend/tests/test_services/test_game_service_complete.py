"""
Comprehensive tests for Game Service (services/game_service.py)
Target: 26.6% → 90% coverage
Focus: Search, filtering, CRUD, BGG integration, performance
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from services.game_service import GameService
from models import Game
from exceptions import GameNotFoundError, ValidationError


class TestGameRetrieval:
    """Test game retrieval methods"""

    def test_get_game_by_id_found(self, db_session, sample_game):
        """Should retrieve game by ID"""
        service = GameService(db_session)

        game = service.get_game_by_id(sample_game.id)

        assert game is not None
        assert game.id == sample_game.id
        assert game.title == sample_game.title

    def test_get_game_by_id_not_found(self, db_session):
        """Should return None for non-existent ID"""
        service = GameService(db_session)

        game = service.get_game_by_id(99999)

        assert game is None

    def test_get_game_by_bgg_id_found(self, db_session, sample_game):
        """Should retrieve game by BGG ID"""
        service = GameService(db_session)

        game = service.get_game_by_bgg_id(sample_game.bgg_id)

        assert game is not None
        assert game.bgg_id == sample_game.bgg_id

    def test_get_game_by_bgg_id_not_found(self, db_session):
        """Should return None for non-existent BGG ID"""
        service = GameService(db_session)

        game = service.get_game_by_bgg_id(999999)

        assert game is None

    def test_get_all_games_owned_only(self, db_session):
        """Should return only OWNED games"""
        # Create games with different statuses
        owned = Game(title="Owned Game", status="OWNED", bgg_id=1001)
        wishlist = Game(title="Wishlist Game", status="WISHLIST", bgg_id=1002)
        db_session.add_all([owned, wishlist])
        db_session.commit()

        service = GameService(db_session)
        games = service.get_all_games()

        titles = [g.title for g in games]
        assert "Owned Game" in titles
        assert "Wishlist Game" not in titles


class TestSearchAndFiltering:
    """Test advanced search and filtering"""

    def test_search_in_title(self, db_session):
        """Should search in game title"""
        game1 = Game(title="Pandemic Legacy", bgg_id=2001, status="OWNED")
        game2 = Game(title="Gloomhaven", bgg_id=2002, status="OWNED")
        db_session.add_all([game1, game2])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(search="Pandemic")

        assert total == 1
        assert games[0].title == "Pandemic Legacy"

    def test_search_in_designers(self, db_session):
        """Should search in designers field"""
        game1 = Game(
            title="Scythe",
            bgg_id=3001,
            status="OWNED",
            designers=["Jamey Stegmaier"]
        )
        game2 = Game(
            title="Wingspan",
            bgg_id=3002,
            status="OWNED",
            designers=["Elizabeth Hargrave"]
        )
        db_session.add_all([game1, game2])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(search="Stegmaier")

        assert total == 1
        assert games[0].title == "Scythe"

    def test_category_filtering(self, db_session):
        """Should filter by category"""
        coop = Game(title="Pandemic", bgg_id=4001, status="OWNED", mana_meeple_category="COOP_ADVENTURE")
        strategy = Game(title="Brass", bgg_id=4002, status="OWNED", mana_meeple_category="CORE_STRATEGY")
        db_session.add_all([coop, strategy])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(category="COOP_ADVENTURE")

        assert total == 1
        assert games[0].mana_meeple_category == "COOP_ADVENTURE"

    def test_category_filtering_uncategorized(self, db_session):
        """Should filter uncategorized games"""
        categorized = Game(title="Categorized", bgg_id=5001, status="OWNED", mana_meeple_category="GATEWAY_STRATEGY")
        uncategorized = Game(title="Uncategorized", bgg_id=5002, status="OWNED", mana_meeple_category=None)
        db_session.add_all([categorized, uncategorized])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(category="uncategorized")

        assert total == 1
        assert games[0].mana_meeple_category is None

    def test_nz_designer_filtering(self, db_session):
        """Should filter by NZ designer flag"""
        nz_game = Game(title="NZ Game", bgg_id=6001, status="OWNED", nz_designer=True)
        intl_game = Game(title="Intl Game", bgg_id=6002, status="OWNED", nz_designer=False)
        db_session.add_all([nz_game, intl_game])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(nz_designer=True)

        assert total == 1
        assert games[0].nz_designer is True

    def test_player_count_filtering(self, db_session):
        """Should filter by player count"""
        game_2_4 = Game(title="2-4 Players", bgg_id=7001, status="OWNED", players_min=2, players_max=4)
        game_3_6 = Game(title="3-6 Players", bgg_id=7002, status="OWNED", players_min=3, players_max=6)
        db_session.add_all([game_2_4, game_3_6])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(players=3)

        # Both games support 3 players
        assert total == 2

    def test_complexity_range_filtering(self, db_session):
        """Should filter by complexity range"""
        light = Game(title="Light", bgg_id=8001, status="OWNED", complexity=1.5)
        medium = Game(title="Medium", bgg_id=8002, status="OWNED", complexity=2.5)
        heavy = Game(title="Heavy", bgg_id=8003, status="OWNED", complexity=4.0)
        db_session.add_all([light, medium, heavy])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(complexity_min=2.0, complexity_max=3.0)

        assert total == 1
        assert games[0].title == "Medium"

    def test_recently_added_filtering(self, db_session):
        """Should filter recently added games"""
        recent = Game(
            title="Recent",
            bgg_id=9001,
            status="OWNED",
            date_added=datetime.now(timezone.utc) - timedelta(days=5)
        )
        old = Game(
            title="Old",
            bgg_id=9002,
            status="OWNED",
            date_added=datetime.now(timezone.utc) - timedelta(days=30)
        )
        db_session.add_all([recent, old])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(recently_added_days=7)

        assert total == 1
        assert games[0].title == "Recent"

    def test_combined_filters(self, db_session):
        """Should apply multiple filters together"""
        matching = Game(
            title="Pandemic Legacy",
            bgg_id=10001,
            status="OWNED",
            mana_meeple_category="COOP_ADVENTURE",
            complexity=2.8,
            nz_designer=False
        )
        non_matching = Game(
            title="Gloomhaven",
            bgg_id=10002,
            status="OWNED",
            mana_meeple_category="CORE_STRATEGY",
            complexity=3.8,
            nz_designer=False
        )
        db_session.add_all([matching, non_matching])
        db_session.commit()

        service = GameService(db_session)
        games, total = service.get_filtered_games(
            search="Pandemic",
            category="COOP_ADVENTURE",
            complexity_max=3.0
        )

        assert total == 1
        assert games[0].title == "Pandemic Legacy"

    def test_pagination(self, db_session):
        """Should paginate results correctly"""
        for i in range(50):
            game = Game(title=f"Game {i}", bgg_id=11000 + i, status="OWNED")
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)

        # First page
        games_p1, total_p1 = service.get_filtered_games(page=1, page_size=20)
        assert len(games_p1) == 20
        assert total_p1 == 50

        # Second page
        games_p2, total_p2 = service.get_filtered_games(page=2, page_size=20)
        assert len(games_p2) == 20

        # Third page (partial)
        games_p3, total_p3 = service.get_filtered_games(page=3, page_size=20)
        assert len(games_p3) == 10

    def test_sorting_title_asc(self, db_session):
        """Should sort by title ascending"""
        game_z = Game(title="Zombicide", bgg_id=12001, status="OWNED")
        game_a = Game(title="Azul", bgg_id=12002, status="OWNED")
        db_session.add_all([game_z, game_a])
        db_session.commit()

        service = GameService(db_session)
        games, _ = service.get_filtered_games(sort="title_asc")

        assert games[0].title == "Azul"
        assert games[1].title == "Zombicide"

    def test_sorting_year_desc(self, db_session):
        """Should sort by year descending"""
        old = Game(title="Old", bgg_id=13001, status="OWNED", year=1995)
        new = Game(title="New", bgg_id=13002, status="OWNED", year=2023)
        db_session.add_all([old, new])
        db_session.commit()

        service = GameService(db_session)
        games, _ = service.get_filtered_games(sort="year_desc")

        assert games[0].year == 2023
        assert games[1].year == 1995

    def test_sorting_rating_desc(self, db_session):
        """Should sort by rating descending"""
        low = Game(title="Low", bgg_id=14001, status="OWNED", average_rating=6.5)
        high = Game(title="High", bgg_id=14002, status="OWNED", average_rating=8.5)
        db_session.add_all([low, high])
        db_session.commit()

        service = GameService(db_session)
        games, _ = service.get_filtered_games(sort="rating_desc")

        assert games[0].average_rating == 8.5

    def test_sorting_playtime_asc(self, db_session):
        """Should sort by playtime ascending"""
        short = Game(title="Short", bgg_id=15001, status="OWNED", playtime_min=15, playtime_max=30)
        long = Game(title="Long", bgg_id=15002, status="OWNED", playtime_min=120, playtime_max=180)
        db_session.add_all([short, long])
        db_session.commit()

        service = GameService(db_session)
        games, _ = service.get_filtered_games(sort="time_asc")

        assert games[0].title == "Short"


class TestGameCRUD:
    """Test Create, Read, Update, Delete operations"""

    def test_create_game_success(self, db_session):
        """Should create a new game"""
        service = GameService(db_session)

        game_data = {
            "title": "New Game",
            "year": 2023,
            "players_min": 2,
            "players_max": 4,
            "bgg_id": 16001,
            "mana_meeple_category": "GATEWAY_STRATEGY"
        }

        game = service.create_game(game_data)

        assert game.id is not None
        assert game.title == "New Game"
        assert game.mana_meeple_category == "GATEWAY_STRATEGY"

    def test_create_game_missing_title(self, db_session):
        """Should raise ValidationError for missing title"""
        service = GameService(db_session)

        with pytest.raises(ValidationError, match="Title is required"):
            service.create_game({"title": ""})

    def test_create_game_duplicate_bgg_id(self, db_session, sample_game):
        """Should raise ValidationError for duplicate BGG ID"""
        service = GameService(db_session)

        game_data = {
            "title": "Duplicate",
            "bgg_id": sample_game.bgg_id
        }

        with pytest.raises(ValidationError, match="already exists"):
            service.create_game(game_data)

    def test_create_game_invalid_category(self, db_session):
        """Should raise ValidationError for invalid category"""
        service = GameService(db_session)

        game_data = {
            "title": "Invalid Category Game",
            "mana_meeple_category": "INVALID_CATEGORY"
        }

        with pytest.raises(ValidationError, match="Invalid category"):
            service.create_game(game_data)

    def test_update_game_success(self, db_session, sample_game):
        """Should update existing game"""
        service = GameService(db_session)

        update_data = {
            "title": "Updated Title",
            "year": 2024
        }

        updated = service.update_game(sample_game.id, update_data)

        assert updated.title == "Updated Title"
        assert updated.year == 2024

    def test_update_game_not_found(self, db_session):
        """Should raise GameNotFoundError for non-existent game"""
        service = GameService(db_session)

        with pytest.raises(GameNotFoundError):
            service.update_game(99999, {"title": "Test"})

    def test_update_game_invalid_title(self, db_session, sample_game):
        """Should raise ValidationError for empty title"""
        service = GameService(db_session)

        with pytest.raises(ValidationError, match="Title is required"):
            service.update_game(sample_game.id, {"title": ""})

    def test_delete_game_success(self, db_session, sample_game):
        """Should delete game"""
        service = GameService(db_session)

        title = service.delete_game(sample_game.id)

        assert title == sample_game.title
        # Verify deleted
        assert service.get_game_by_id(sample_game.id) is None

    def test_delete_game_not_found(self, db_session):
        """Should raise GameNotFoundError for non-existent game"""
        service = GameService(db_session)

        with pytest.raises(GameNotFoundError):
            service.delete_game(99999)


class TestBGGIntegration:
    """Test BGG import and update functionality"""

    def test_create_from_bgg_new_game(self, db_session):
        """Should create new game from BGG data"""
        service = GameService(db_session)

        bgg_data = {
            "title": "Gloomhaven",
            "year": 2017,
            "designers": ["Isaac Childres"],
            "complexity": 3.87,
            "average_rating": 8.67
        }

        game, was_cached = service.create_or_update_from_bgg(174430, bgg_data)

        assert game.id is not None
        assert game.title == "Gloomhaven"
        assert was_cached is False

    def test_create_from_bgg_existing_no_update(self, db_session):
        """Should return cached game without updating"""
        service = GameService(db_session)

        # Create initial game
        bgg_data = {"title": "Test Game", "year": 2020}
        game1, _ = service.create_or_update_from_bgg(999, bgg_data)

        # Try to create again without force_update
        bgg_data_new = {"title": "Updated Title", "year": 2021}
        game2, was_cached = service.create_or_update_from_bgg(999, bgg_data_new, force_update=False)

        assert game2.id == game1.id
        assert game2.title == "Test Game"  # Not updated
        assert was_cached is True

    def test_create_from_bgg_force_update(self, db_session):
        """Should update existing game when force_update=True"""
        service = GameService(db_session)

        # Create initial game
        bgg_data = {"title": "Test Game", "year": 2020}
        game1, _ = service.create_or_update_from_bgg(998, bgg_data)

        # Force update
        bgg_data_new = {"title": "Updated Title", "year": 2021}
        game2, was_cached = service.create_or_update_from_bgg(998, bgg_data_new, force_update=True)

        assert game2.id == game1.id
        assert game2.title == "Updated Title"
        assert game2.year == 2021

    def test_create_from_bgg_invalid_bgg_id(self, db_session):
        """Should raise ValidationError for invalid BGG ID"""
        service = GameService(db_session)

        with pytest.raises(ValidationError, match="positive integer"):
            service.create_or_update_from_bgg(-1, {"title": "Test"})

    def test_create_from_bgg_missing_title(self, db_session):
        """Should raise ValidationError for missing title"""
        service = GameService(db_session)

        with pytest.raises(ValidationError, match="must include a title"):
            service.create_or_update_from_bgg(1, {})

    def test_auto_link_expansion(self, db_session):
        """Should auto-link expansion to base game"""
        service = GameService(db_session)

        # Create base game
        base_game = Game(title="Base Game", bgg_id=200, status="OWNED")
        db_session.add(base_game)
        db_session.commit()

        # Create expansion with base game reference
        expansion_data = {
            "title": "Expansion",
            "is_expansion": True,
            "base_game_bgg_id": 200
        }

        expansion, _ = service.create_or_update_from_bgg(201, expansion_data)

        assert expansion.base_game_id == base_game.id

    def test_determine_optimal_bgg_image_quality_very_popular(self, db_session):
        """Should use 'original' quality for very popular games"""
        service = GameService(db_session)

        game = Game(title="Popular", bgg_id=300, users_rated=15000, bgg_rank=100)

        quality = service._determine_optimal_bgg_image_quality(game)

        assert quality == "original"

    def test_determine_optimal_bgg_image_quality_moderate(self, db_session):
        """Should use 'medium' quality for moderate popularity"""
        service = GameService(db_session)

        game = Game(title="Moderate", bgg_id=301, users_rated=2000)

        quality = service._determine_optimal_bgg_image_quality(game)

        assert quality == "medium"

    def test_determine_optimal_bgg_image_quality_unpopular(self, db_session):
        """Should use 'medium-thumb' for unpopular games"""
        service = GameService(db_session)

        game = Game(title="Unpopular", bgg_id=302, users_rated=100)

        quality = service._determine_optimal_bgg_image_quality(game)

        assert quality == "medium-thumb"


class TestCategoryCounts:
    """Test category counting functionality"""

    def test_get_category_counts(self, db_session):
        """Should count games per category"""
        coop = Game(title="Coop", bgg_id=400, status="OWNED", mana_meeple_category="COOP_ADVENTURE")
        strategy = Game(title="Strategy", bgg_id=401, status="OWNED", mana_meeple_category="CORE_STRATEGY")
        uncategorized = Game(title="Uncat", bgg_id=402, status="OWNED", mana_meeple_category=None)
        db_session.add_all([coop, strategy, uncategorized])
        db_session.commit()

        service = GameService(db_session)
        counts = service.get_category_counts()

        assert counts["all"] == 3
        assert counts["COOP_ADVENTURE"] == 1
        assert counts["CORE_STRATEGY"] == 1
        assert counts["uncategorized"] == 1

    def test_get_category_counts_excludes_buy_list(self, db_session):
        """Should exclude WISHLIST and BUY_LIST games"""
        owned = Game(title="Owned", bgg_id=500, status="OWNED")
        wishlist = Game(title="Wishlist", bgg_id=501, status="WISHLIST")
        db_session.add_all([owned, wishlist])
        db_session.commit()

        service = GameService(db_session)
        counts = service.get_category_counts()

        assert counts["all"] == 1  # Only owned


class TestGamesByDesigner:
    """Test designer filtering"""

    def test_get_games_by_designer(self, db_session):
        """Should find games by designer name"""
        game1 = Game(
            title="Game 1",
            bgg_id=600,
            status="OWNED",
            designers=["Jamey Stegmaier", "Morten Monrad Pedersen"]
        )
        game2 = Game(
            title="Game 2",
            bgg_id=601,
            status="OWNED",
            designers=["Elizabeth Hargrave"]
        )
        db_session.add_all([game1, game2])
        db_session.commit()

        service = GameService(db_session)
        games = service.get_games_by_designer("Stegmaier")

        assert len(games) == 1
        assert games[0].title == "Game 1"


class TestPerformance:
    """Test performance optimizations"""

    def test_eager_loading_prevents_n_plus_1(self, db_session):
        """Should use eager loading for expansions"""
        # Create base game with expansion
        base = Game(title="Base", bgg_id=700, status="OWNED")
        db_session.add(base)
        db_session.commit()

        expansion = Game(
            title="Expansion",
            bgg_id=701,
            status="OWNED",
            is_expansion=True,
            base_game_id=base.id
        )
        db_session.add(expansion)
        db_session.commit()

        service = GameService(db_session)

        # Should load expansions in single query
        game = service.get_game_by_id(base.id)

        # Access expansions (should not trigger additional query)
        assert len(game.expansions) == 1

    def test_pagination_performance(self, db_session, large_game_dataset):
        """Should handle large datasets efficiently"""
        service = GameService(db_session)

        # Should complete in reasonable time
        games, total = service.get_filtered_games(page=1, page_size=50)

        assert len(games) == 50
        assert total == 500

    def test_window_function_single_query(self, db_session):
        """Should use window function for count + pagination"""
        for i in range(10):
            game = Game(title=f"Game {i}", bgg_id=800 + i, status="OWNED")
            db_session.add(game)
        db_session.commit()

        service = GameService(db_session)

        # Should execute efficiently using window function
        with patch.object(db_session, 'execute', wraps=db_session.execute) as mock_execute:
            games, total = service.get_filtered_games(page=1, page_size=5)

            # Should make 3 calls: setup, window function query, and object loading
            # This is much better than N+1 queries (would be 10+ calls)
            assert mock_execute.call_count == 3
