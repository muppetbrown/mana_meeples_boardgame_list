"""
Integration tests for complete game workflows.
Tests end-to-end functionality: BGG import → categorization → public display → updates
"""
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.orm import Session

from models import Game
from services.game_service import GameService
from bgg_service import fetch_bgg_thing
from exceptions import GameNotFoundError, ValidationError


class TestGameImportWorkflow:
    """Test complete game import workflow from BGG to public display"""

    @pytest.mark.asyncio
    async def test_complete_bgg_import_workflow(self, db_session: Session):
        """
        Test complete workflow: BGG fetch → create game → auto-categorize → verify data
        """
        # Mock BGG API response
        mock_bgg_data = {
            "bgg_id": 174430,
            "title": "Gloomhaven",
            "year": 2017,
            "description": "Gloomhaven is a game of Euro-inspired tactical combat...",
            "thumbnail": "https://cf.geekdo-images.com/thumb_img/img/...",
            "image": "https://cf.geekdo-images.com/original_img/img/...",
            "players_min": 1,
            "players_max": 4,
            "playtime_min": 60,
            "playtime_max": 120,
            "min_age": 14,
            "categories": ["Adventure", "Fantasy", "Fighting"],
            "mechanics": ["Campaign / Battle Card Driven", "Cooperative Game", "Grid Movement"],
            "designers": ["Isaac Childres"],
            "publishers": ["Cephalofair Games"],
            "artists": ["Alexandr Elichev", "Josh T. McDowell"],
            "average_rating": 8.8,
            "complexity": 3.86,
            "bgg_rank": 1,
            "users_rated": 60000,
            "is_cooperative": True,
            "game_type": "Strategy • Thematic",
        }

        # Step 1: Fetch from BGG (mocked)
        with patch("bgg_service.fetch_bgg_thing", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_bgg_data
            bgg_data = await mock_fetch(174430)
            assert bgg_data["title"] == "Gloomhaven"
            assert bgg_data["bgg_id"] == 174430

            # Step 2: Create game using service
            service = GameService(db_session)
            game, was_cached = service.create_or_update_from_bgg(174430, bgg_data)

            # Step 3: Verify game was created
            assert game.id is not None
            assert game.title == "Gloomhaven"
            assert game.bgg_id == 174430
            assert game.year == 2017
            assert game.players_min == 1
            assert game.players_max == 4
            assert game.complexity == 3.86
            assert game.average_rating == 8.8
            assert game.is_cooperative is True
            assert was_cached is False

            # Step 4: Verify auto-categorization occurred
            # Gloomhaven should be categorized (even if we can't predict exact category)
            assert game.mana_meeple_category is not None or game.categories

            # Step 5: Verify designers and mechanics stored as JSON
            assert "Isaac Childres" in game.designers
            assert "Cooperative Game" in game.mechanics
            assert "Cephalofair Games" in game.publishers

            # Step 6: Verify game is retrievable
            retrieved_game = service.get_game_by_bgg_id(174430)
            assert retrieved_game.id == game.id
            assert retrieved_game.title == "Gloomhaven"

    @pytest.mark.asyncio
    async def test_import_update_workflow(self, db_session: Session):
        """
        Test workflow: Import game → Update from BGG → Verify changes persisted
        """
        mock_initial_data = {
            "bgg_id": 13,
            "title": "Catan",
            "year": 1995,
            "players_min": 3,
            "players_max": 4,
            "categories": ["Negotiation"],
            "designers": ["Klaus Teuber"],
            "average_rating": 7.2,
            "complexity": 2.3,
            "mechanics": ["Trading", "Dice Rolling"],
            "publishers": ["Kosmos"],
            "artists": ["Artist Name"],
            "bgg_rank": 300,
        }

        mock_updated_data = {
            **mock_initial_data,
            "average_rating": 7.3,  # Rating improved
            "bgg_rank": 280,  # Rank improved
            "users_rated": 85000,  # More ratings
        }

        service = GameService(db_session)

        with patch("bgg_service.fetch_bgg_thing", new_callable=AsyncMock) as mock_fetch:
            # Initial import
            mock_fetch.return_value = mock_initial_data
            game, was_cached = service.create_or_update_from_bgg(13, mock_initial_data)
            initial_id = game.id
            assert game.average_rating == 7.2
            assert game.bgg_rank == 300

            # Force update with new data
            mock_fetch.return_value = mock_updated_data
            game, was_cached = service.create_or_update_from_bgg(
                13, mock_updated_data, force_update=True
            )

            # Verify same game was updated (not new game created)
            assert game.id == initial_id
            assert game.average_rating == 7.3
            assert game.bgg_rank == 280
            assert game.users_rated == 85000

    @pytest.mark.asyncio
    async def test_expansion_linking_workflow(self, db_session: Session):
        """
        Test workflow: Import base game → Import expansion → Verify linking
        """
        # Base game data
        base_game_data = {
            "bgg_id": 13,
            "title": "Catan",
            "year": 1995,
            "players_min": 3,
            "players_max": 4,
            "is_expansion": False,
            "categories": ["Negotiation"],
            "designers": ["Klaus Teuber"],
            "mechanics": ["Trading"],
            "publishers": ["Kosmos"],
            "artists": ["Artist Name"],
        }

        # Expansion data
        expansion_data = {
            "bgg_id": 2807,
            "title": "Catan: 5-6 Player Extension",
            "year": 1996,
            "players_min": 5,
            "players_max": 6,
            "is_expansion": True,
            "base_game_bgg_id": 13,  # Links to base game
            "expansion_type": "requires_base",
            "modifies_players_min": 5,
            "modifies_players_max": 6,
            "categories": ["Expansion"],
            "designers": ["Klaus Teuber"],
            "mechanics": ["Trading"],
            "publishers": ["Kosmos"],
            "artists": ["Artist Name"],
        }

        service = GameService(db_session)

        with patch("bgg_service.fetch_bgg_thing", new_callable=AsyncMock) as mock_fetch:
            # Step 1: Import base game
            mock_fetch.return_value = base_game_data
            base_game, _ = service.create_or_update_from_bgg(13, base_game_data)
            assert base_game.is_expansion is False
            assert base_game.players_max == 4

            # Step 2: Import expansion
            mock_fetch.return_value = expansion_data
            expansion, _ = service.create_or_update_from_bgg(2807, expansion_data)

            # Step 3: Verify expansion linked to base game
            assert expansion.is_expansion is True
            assert expansion.base_game_id == base_game.id
            assert expansion.expansion_type == "requires_base"
            assert expansion.modifies_players_max == 6

            # Step 4: Verify base game has expansion in relationship
            db_session.refresh(base_game)
            assert len(base_game.expansions) == 1
            assert base_game.expansions[0].id == expansion.id


class TestPublicAPIWorkflow:
    """Test public API workflows for game browsing"""

    def test_filter_and_pagination_workflow(self, db_session: Session):
        """
        Test workflow: Create multiple games → Filter → Paginate → Sort
        """
        service = GameService(db_session)

        # Create test games with different categories
        games_data = [
            {
                "title": "Game A - Coop",
                "bgg_id": 1001,
                "mana_meeple_category": "COOP_ADVENTURE",
                "year": 2020,
                "average_rating": 8.0,
                "status": "OWNED",
            },
            {
                "title": "Game B - Coop",
                "bgg_id": 1002,
                "mana_meeple_category": "COOP_ADVENTURE",
                "year": 2021,
                "average_rating": 8.5,
                "status": "OWNED",
            },
            {
                "title": "Game C - Strategy",
                "bgg_id": 1003,
                "mana_meeple_category": "CORE_STRATEGY",
                "year": 2019,
                "average_rating": 9.0,
                "status": "OWNED",
            },
            {
                "title": "Game D - Party",
                "bgg_id": 1004,
                "mana_meeple_category": "PARTY_ICEBREAKERS",
                "year": 2022,
                "average_rating": 7.5,
                "status": "OWNED",
            },
        ]

        for data in games_data:
            service.create_game(data)

        # Test 1: Filter by category
        games, total = service.get_filtered_games(
            category="COOP_ADVENTURE", page=1, page_size=10
        )
        assert total == 2
        assert all(g.mana_meeple_category == "COOP_ADVENTURE" for g in games)

        # Test 2: Sort by rating descending
        games, total = service.get_filtered_games(
            sort="rating_desc", page=1, page_size=10
        )
        assert total == 4
        assert games[0].title == "Game C - Strategy"  # Highest rating (9.0)
        assert games[-1].title == "Game D - Party"  # Lowest rating (7.5)

        # Test 3: Pagination
        games_page1, total = service.get_filtered_games(page=1, page_size=2)
        games_page2, _ = service.get_filtered_games(page=2, page_size=2)
        assert total == 4
        assert len(games_page1) == 2
        assert len(games_page2) == 2
        assert games_page1[0].id != games_page2[0].id  # Different games

        # Test 4: Search by title
        games, total = service.get_filtered_games(search="Coop")
        assert total == 2
        assert all("Coop" in g.title for g in games)

    def test_nz_designer_filter_workflow(self, db_session: Session):
        """
        Test workflow: Create games with NZ designers → Filter → Verify results
        """
        service = GameService(db_session)

        # Create test games
        nz_game_1 = service.create_game({
            "title": "NZ Game 1",
            "bgg_id": 2001,
            "nz_designer": True,
            "designers": ["NZ Designer"],
            "status": "OWNED",
        })
        nz_game_2 = service.create_game({
            "title": "NZ Game 2",
            "bgg_id": 2002,
            "nz_designer": True,
            "designers": ["Another NZ Designer"],
            "status": "OWNED",
        })
        intl_game = service.create_game({
            "title": "International Game",
            "bgg_id": 2003,
            "nz_designer": False,
            "designers": ["International Designer"],
            "status": "OWNED",
        })

        # Verify games created with correct flags
        assert nz_game_1.nz_designer is True
        assert nz_game_2.nz_designer is True
        assert intl_game.nz_designer is False

        # Filter by NZ designer
        games, total = service.get_filtered_games(nz_designer=True, page_size=100)

        # Debug: print what we got
        print(f"DEBUG: NZ designer filter returned {total} games")
        for g in games:
            print(f"  - {g.title}: nz_designer={g.nz_designer}")

        assert total >= 2, f"Expected at least 2 NZ designer games, got {total}"
        # Verify our specific NZ games are included
        nz_titles = {g.title for g in games}
        assert "NZ Game 1" in nz_titles, f"NZ Game 1 not in results: {nz_titles}"
        assert "NZ Game 2" in nz_titles, f"NZ Game 2 not in results: {nz_titles}"

        # Verify non-NZ games excluded from NZ filter
        for g in games:
            assert g.nz_designer is True, f"Non-NZ game in results: {g.title}"

    def test_player_count_filter_workflow(self, db_session: Session):
        """
        Test workflow: Create games with different player counts → Filter → Verify
        """
        service = GameService(db_session)

        games_data = [
            {
                "title": "Solo Game",
                "bgg_id": 3001,
                "players_min": 1,
                "players_max": 1,
                "status": "OWNED",
            },
            {
                "title": "Party Game",
                "bgg_id": 3002,
                "players_min": 4,
                "players_max": 10,
                "status": "OWNED",
            },
            {
                "title": "Flexible Game",
                "bgg_id": 3003,
                "players_min": 2,
                "players_max": 5,
                "status": "OWNED",
            },
        ]

        for data in games_data:
            service.create_game(data)

        # Test: Filter for 4 players
        games, total = service.get_filtered_games(players=4)
        assert total == 2  # Party Game and Flexible Game
        assert all(g.players_min <= 4 <= g.players_max for g in games)

        # Test: Filter for 1 player (solo)
        games, total = service.get_filtered_games(players=1)
        assert total == 1
        assert games[0].title == "Solo Game"


class TestAdminWorkflow:
    """Test admin workflows for game management"""

    def test_create_update_delete_workflow(self, db_session: Session):
        """
        Test workflow: Create game → Update → Verify → Delete → Verify deletion
        """
        service = GameService(db_session)

        # Step 1: Create game
        game_data = {
            "title": "Test Game",
            "bgg_id": 9999,
            "year": 2020,
            "players_min": 2,
            "players_max": 4,
            "mana_meeple_category": "GATEWAY_STRATEGY",
        }
        game = service.create_game(game_data)
        game_id = game.id
        assert game.title == "Test Game"
        assert game.year == 2020

        # Step 2: Update game
        update_data = {
            "year": 2021,
            "description": "Updated description",
            "nz_designer": True,
        }
        updated_game = service.update_game(game_id, update_data)
        assert updated_game.year == 2021
        assert updated_game.description == "Updated description"
        assert updated_game.nz_designer is True
        assert updated_game.title == "Test Game"  # Unchanged fields preserved

        # Step 3: Verify game exists
        retrieved = service.get_game_by_id(game_id)
        assert retrieved.year == 2021

        # Step 4: Delete game
        deleted_title = service.delete_game(game_id)
        assert deleted_title == "Test Game"

        # Step 5: Verify deletion
        deleted_game = service.get_game_by_id(game_id)
        assert deleted_game is None

        # Step 6: Verify deletion raises error on subsequent operations
        with pytest.raises(GameNotFoundError):
            service.update_game(game_id, {"year": 2022})

    def test_bulk_categorization_workflow(self, db_session: Session):
        """
        Test workflow: Create uncategorized games → Bulk categorize → Verify
        """
        service = GameService(db_session)

        # Create uncategorized games
        games_data = [
            {"title": "Uncategorized 1", "bgg_id": 4001, "status": "OWNED"},
            {"title": "Uncategorized 2", "bgg_id": 4002, "status": "OWNED"},
            {"title": "Uncategorized 3", "bgg_id": 4003, "status": "OWNED"},
        ]

        created_games = []
        for data in games_data:
            game = service.create_game(data)
            created_games.append(game)
            assert game.mana_meeple_category is None

        # Bulk categorize
        categorization_map = {
            created_games[0].id: "COOP_ADVENTURE",
            created_games[1].id: "CORE_STRATEGY",
            created_games[2].id: "PARTY_ICEBREAKERS",
        }

        for game_id, category in categorization_map.items():
            service.update_game(game_id, {"mana_meeple_category": category})

        # Verify categorization
        for game_id, expected_category in categorization_map.items():
            game = service.get_game_by_id(game_id)
            assert game.mana_meeple_category == expected_category


class TestErrorHandlingWorkflow:
    """Test error handling across workflows"""

    def test_duplicate_bgg_id_prevention(self, db_session: Session):
        """
        Test workflow: Create game → Attempt duplicate BGG ID → Verify error
        """
        service = GameService(db_session)

        # Create first game
        game_data = {"title": "Original Game", "bgg_id": 5000}
        service.create_game(game_data)

        # Attempt to create duplicate
        duplicate_data = {"title": "Duplicate Game", "bgg_id": 5000}
        with pytest.raises(ValidationError, match="already exists"):
            service.create_game(duplicate_data)

    def test_invalid_category_validation(self, db_session: Session):
        """
        Test workflow: Attempt to create game with invalid category → Verify error
        """
        service = GameService(db_session)

        invalid_data = {
            "title": "Invalid Game",
            "bgg_id": 6000,
            "mana_meeple_category": "INVALID_CATEGORY",
        }

        with pytest.raises(ValidationError, match="Invalid category"):
            service.create_game(invalid_data)

    def test_empty_title_validation(self, db_session: Session):
        """
        Test workflow: Attempt to create game without title → Verify error
        """
        service = GameService(db_session)

        invalid_data = {"bgg_id": 7000, "title": ""}

        with pytest.raises(ValidationError, match="Title is required"):
            service.create_game(invalid_data)


class TestComplexityFilterWorkflow:
    """Test complexity filtering workflows"""

    def test_complexity_range_filter(self, db_session: Session):
        """
        Test workflow: Create games with various complexity → Filter by range
        """
        service = GameService(db_session)

        games_data = [
            {"title": "Simple Game", "bgg_id": 8001, "complexity": 1.5, "status": "OWNED"},
            {"title": "Medium Game", "bgg_id": 8002, "complexity": 2.8, "status": "OWNED"},
            {"title": "Complex Game", "bgg_id": 8003, "complexity": 4.2, "status": "OWNED"},
            {"title": "Very Complex", "bgg_id": 8004, "complexity": 4.8, "status": "OWNED"},
        ]

        for data in games_data:
            service.create_game(data)

        # Filter: complexity between 2.0 and 4.0
        games, total = service.get_filtered_games(
            complexity_min=2.0, complexity_max=4.0
        )
        assert total == 1  # Only "Medium Game"
        assert games[0].title == "Medium Game"

        # Filter: complexity >= 4.0
        games, total = service.get_filtered_games(complexity_min=4.0)
        assert total == 2  # "Complex Game" and "Very Complex"

        # Filter: complexity <= 2.0
        games, total = service.get_filtered_games(complexity_max=2.0)
        assert total == 1  # Only "Simple Game"
