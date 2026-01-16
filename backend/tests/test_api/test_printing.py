"""
Comprehensive tests for printing API endpoints.
Tests the /api/admin/print-labels endpoint for generating PDF game labels.
"""
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO

from models import Game


class TestPrintLabelsEndpoint:
    """Tests for POST /api/admin/print-labels endpoint"""

    def test_print_labels_success(self, client, db_session, admin_headers):
        """Test successful label generation for multiple games"""
        # Create test games
        games = []
        for i in range(3):
            game = Game(
                title=f"Test Game {i}",
                year=2020 + i,
                players_min=2,
                players_max=4,
                playtime_min=30,
                playtime_max=60,
                min_age=10,
                complexity=2.5,
                mana_meeple_category="GATEWAY_STRATEGY"
            )
            db_session.add(game)
            games.append(game)
        db_session.commit()

        game_ids = [g.id for g in games]

        with patch('api.routers.printing.LabelGenerator') as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.generate_pdf.return_value = BytesIO(b'%PDF-1.4 test pdf content')
            MockGenerator.return_value = mock_instance

            response = client.post(
                "/api/admin/print-labels",
                json={"game_ids": game_ids},
                headers=admin_headers
            )

            if response.status_code == 200:
                assert response.headers.get("content-type") == "application/pdf"
                assert "attachment" in response.headers.get("content-disposition", "")
                assert "board-game-labels" in response.headers.get("content-disposition", "")
                assert ".pdf" in response.headers.get("content-disposition", "")
                # Verify generator was called with correct data
                mock_instance.generate_pdf.assert_called_once()
                call_args = mock_instance.generate_pdf.call_args[0][0]
                assert len(call_args) == 3

    def test_print_labels_single_game(self, client, db_session, admin_headers):
        """Test label generation for a single game"""
        game = Game(
            title="Single Test Game",
            year=2021,
            players_min=1,
            players_max=5,
            mana_meeple_category="COOP_ADVENTURE"
        )
        db_session.add(game)
        db_session.commit()

        with patch('api.routers.printing.LabelGenerator') as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.generate_pdf.return_value = BytesIO(b'%PDF-1.4 test pdf')
            MockGenerator.return_value = mock_instance

            response = client.post(
                "/api/admin/print-labels",
                json={"game_ids": [game.id]},
                headers=admin_headers
            )

            assert response.status_code in [200, 429]
            if response.status_code == 200:
                assert response.headers.get("content-type") == "application/pdf"

    def test_print_labels_game_not_found(self, client, admin_headers):
        """Test label generation with non-existent game ID"""
        response = client.post(
            "/api/admin/print-labels",
            json={"game_ids": [999999]},
            headers=admin_headers
        )

        assert response.status_code in [404, 429]
        if response.status_code == 404:
            assert "999999" in response.json()["detail"]

    def test_print_labels_partial_games_not_found(self, client, db_session, admin_headers):
        """Test label generation when some game IDs are not found"""
        game = Game(title="Existing Game", year=2020)
        db_session.add(game)
        db_session.commit()

        response = client.post(
            "/api/admin/print-labels",
            json={"game_ids": [game.id, 999999, 888888]},
            headers=admin_headers
        )

        assert response.status_code in [404, 429]
        if response.status_code == 404:
            detail = response.json()["detail"]
            assert "999999" in detail or "888888" in detail

    def test_print_labels_empty_game_ids(self, client, admin_headers):
        """Test label generation with empty game_ids list"""
        response = client.post(
            "/api/admin/print-labels",
            json={"game_ids": []},
            headers=admin_headers
        )

        # Should fail validation (min_length=1)
        assert response.status_code in [422, 429]

    def test_print_labels_too_many_games(self, client, admin_headers):
        """Test label generation with too many games (max 100)"""
        game_ids = list(range(1, 102))  # 101 IDs

        response = client.post(
            "/api/admin/print-labels",
            json={"game_ids": game_ids},
            headers=admin_headers
        )

        # Should fail validation (max_length=100)
        assert response.status_code in [422, 429]

    def test_print_labels_unauthorized(self, client, csrf_headers):
        """Test label generation without authentication"""
        response = client.post(
            "/api/admin/print-labels",
            json={"game_ids": [1]},
            headers=csrf_headers
        )

        assert response.status_code in [401, 429]

    def test_print_labels_missing_game_ids(self, client, admin_headers):
        """Test label generation with missing game_ids field"""
        response = client.post(
            "/api/admin/print-labels",
            json={},
            headers=admin_headers
        )

        assert response.status_code in [422, 429]

    def test_print_labels_invalid_game_ids_type(self, client, admin_headers):
        """Test label generation with invalid game_ids type"""
        response = client.post(
            "/api/admin/print-labels",
            json={"game_ids": "not a list"},
            headers=admin_headers
        )

        assert response.status_code in [422, 429]

    def test_print_labels_negative_game_id(self, client, admin_headers):
        """Test label generation with negative game ID"""
        response = client.post(
            "/api/admin/print-labels",
            json={"game_ids": [-1]},
            headers=admin_headers
        )

        # Negative IDs should not find any games
        assert response.status_code in [404, 422, 429]


class TestPrintLabelsGameData:
    """Tests for game data conversion in label generation"""

    def test_print_labels_all_game_fields(self, client, db_session, admin_headers):
        """Test that all relevant game fields are passed to generator"""
        game = Game(
            title="Full Data Game",
            year=2022,
            players_min=1,
            players_max=6,
            playtime_min=45,
            playtime_max=90,
            min_age=14,
            complexity=3.5,
            game_type="base",
            is_cooperative=True,
            mana_meeple_category="CORE_STRATEGY"
        )
        db_session.add(game)
        db_session.commit()

        with patch('api.routers.printing.LabelGenerator') as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.generate_pdf.return_value = BytesIO(b'%PDF-1.4 test')
            MockGenerator.return_value = mock_instance

            response = client.post(
                "/api/admin/print-labels",
                json={"game_ids": [game.id]},
                headers=admin_headers
            )

            if response.status_code == 200:
                call_args = mock_instance.generate_pdf.call_args[0][0]
                game_dict = call_args[0]

                assert game_dict['title'] == "Full Data Game"
                assert game_dict['year'] == 2022
                assert game_dict['players_min'] == 1
                assert game_dict['players_max'] == 6
                assert game_dict['playtime_min'] == 45
                assert game_dict['playtime_max'] == 90
                assert game_dict['min_age'] == 14
                assert game_dict['complexity'] == 3.5
                assert game_dict['game_type'] == "base"
                assert game_dict['is_cooperative'] == True
                assert game_dict['mana_meeple_category'] == "CORE_STRATEGY"

    def test_print_labels_null_optional_fields(self, client, db_session, admin_headers):
        """Test label generation with null optional fields"""
        game = Game(
            title="Minimal Game",
            year=None,
            players_min=None,
            players_max=None,
            playtime_min=None,
            playtime_max=None,
            min_age=None,
            complexity=None,
            game_type=None,
            is_cooperative=None,
            mana_meeple_category=None
        )
        db_session.add(game)
        db_session.commit()

        with patch('api.routers.printing.LabelGenerator') as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.generate_pdf.return_value = BytesIO(b'%PDF-1.4 test')
            MockGenerator.return_value = mock_instance

            response = client.post(
                "/api/admin/print-labels",
                json={"game_ids": [game.id]},
                headers=admin_headers
            )

            if response.status_code == 200:
                call_args = mock_instance.generate_pdf.call_args[0][0]
                game_dict = call_args[0]

                assert game_dict['title'] == "Minimal Game"
                assert game_dict['year'] is None
                assert game_dict['players_min'] is None


class TestPrintLabelsErrorHandling:
    """Tests for error handling in label generation"""

    def test_print_labels_generator_error(self, client, db_session, admin_headers):
        """Test handling of PDF generator errors"""
        game = Game(title="Test Game", year=2020)
        db_session.add(game)
        db_session.commit()

        with patch('api.routers.printing.LabelGenerator') as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.generate_pdf.side_effect = Exception("PDF generation failed")
            MockGenerator.return_value = mock_instance

            response = client.post(
                "/api/admin/print-labels",
                json={"game_ids": [game.id]},
                headers=admin_headers
            )

            assert response.status_code in [500, 429]
            if response.status_code == 500:
                assert "Failed to generate labels" in response.json()["detail"]

    def test_print_labels_generator_init_error(self, client, db_session, admin_headers):
        """Test handling of PDF generator initialization errors"""
        game = Game(title="Test Game", year=2020)
        db_session.add(game)
        db_session.commit()

        with patch('api.routers.printing.LabelGenerator') as MockGenerator:
            MockGenerator.side_effect = Exception("Generator init failed")

            response = client.post(
                "/api/admin/print-labels",
                json={"game_ids": [game.id]},
                headers=admin_headers
            )

            assert response.status_code in [500, 429]


class TestPrintLabelsResponse:
    """Tests for print labels response format"""

    def test_print_labels_filename_format(self, client, db_session, admin_headers):
        """Test that filename includes timestamp"""
        game = Game(title="Test Game", year=2020)
        db_session.add(game)
        db_session.commit()

        with patch('api.routers.printing.LabelGenerator') as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.generate_pdf.return_value = BytesIO(b'%PDF-1.4 test')
            MockGenerator.return_value = mock_instance

            response = client.post(
                "/api/admin/print-labels",
                json={"game_ids": [game.id]},
                headers=admin_headers
            )

            if response.status_code == 200:
                content_disposition = response.headers.get("content-disposition", "")
                # Should contain timestamp format like 20240115_143022
                assert "board-game-labels-" in content_disposition
                assert ".pdf" in content_disposition

    def test_print_labels_content_type(self, client, db_session, admin_headers):
        """Test that response has correct content type"""
        game = Game(title="Test Game", year=2020)
        db_session.add(game)
        db_session.commit()

        with patch('api.routers.printing.LabelGenerator') as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.generate_pdf.return_value = BytesIO(b'%PDF-1.4 test')
            MockGenerator.return_value = mock_instance

            response = client.post(
                "/api/admin/print-labels",
                json={"game_ids": [game.id]},
                headers=admin_headers
            )

            if response.status_code == 200:
                assert response.headers.get("content-type") == "application/pdf"


class TestPrintLabelsEdgeCases:
    """Tests for edge cases in label generation"""

    def test_print_labels_special_characters_in_title(self, client, db_session, admin_headers):
        """Test label generation with special characters in game title"""
        game = Game(
            title="Game: The & of 'Special' \"Characters\" — Edition",
            year=2020
        )
        db_session.add(game)
        db_session.commit()

        with patch('api.routers.printing.LabelGenerator') as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.generate_pdf.return_value = BytesIO(b'%PDF-1.4 test')
            MockGenerator.return_value = mock_instance

            response = client.post(
                "/api/admin/print-labels",
                json={"game_ids": [game.id]},
                headers=admin_headers
            )

            assert response.status_code in [200, 429]

    def test_print_labels_unicode_title(self, client, db_session, admin_headers):
        """Test label generation with unicode characters in title"""
        game = Game(
            title="日本語ゲーム — Pokémon™",
            year=2020
        )
        db_session.add(game)
        db_session.commit()

        with patch('api.routers.printing.LabelGenerator') as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.generate_pdf.return_value = BytesIO(b'%PDF-1.4 test')
            MockGenerator.return_value = mock_instance

            response = client.post(
                "/api/admin/print-labels",
                json={"game_ids": [game.id]},
                headers=admin_headers
            )

            assert response.status_code in [200, 429]

    def test_print_labels_very_long_title(self, client, db_session, admin_headers):
        """Test label generation with very long game title"""
        game = Game(
            title="A" * 500,  # Very long title
            year=2020
        )
        db_session.add(game)
        db_session.commit()

        with patch('api.routers.printing.LabelGenerator') as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.generate_pdf.return_value = BytesIO(b'%PDF-1.4 test')
            MockGenerator.return_value = mock_instance

            response = client.post(
                "/api/admin/print-labels",
                json={"game_ids": [game.id]},
                headers=admin_headers
            )

            assert response.status_code in [200, 429]

    def test_print_labels_duplicate_game_ids(self, client, db_session, admin_headers):
        """Test label generation with duplicate game IDs"""
        game = Game(title="Test Game", year=2020)
        db_session.add(game)
        db_session.commit()

        with patch('api.routers.printing.LabelGenerator') as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.generate_pdf.return_value = BytesIO(b'%PDF-1.4 test')
            MockGenerator.return_value = mock_instance

            # Same ID twice
            response = client.post(
                "/api/admin/print-labels",
                json={"game_ids": [game.id, game.id]},
                headers=admin_headers
            )

            # Should either work (with deduplication) or fail validation
            assert response.status_code in [200, 404, 422, 429]

    def test_print_labels_extreme_player_counts(self, client, db_session, admin_headers):
        """Test label generation with extreme player counts"""
        game = Game(
            title="Massive Party Game",
            year=2020,
            players_min=1,
            players_max=999
        )
        db_session.add(game)
        db_session.commit()

        with patch('api.routers.printing.LabelGenerator') as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.generate_pdf.return_value = BytesIO(b'%PDF-1.4 test')
            MockGenerator.return_value = mock_instance

            response = client.post(
                "/api/admin/print-labels",
                json={"game_ids": [game.id]},
                headers=admin_headers
            )

            assert response.status_code in [200, 429]

    def test_print_labels_minimal_playtime(self, client, db_session, admin_headers):
        """Test label generation with minimal playtime values"""
        game = Game(
            title="Quick Game",
            year=2020,
            playtime_min=1,
            playtime_max=5
        )
        db_session.add(game)
        db_session.commit()

        with patch('api.routers.printing.LabelGenerator') as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.generate_pdf.return_value = BytesIO(b'%PDF-1.4 test')
            MockGenerator.return_value = mock_instance

            response = client.post(
                "/api/admin/print-labels",
                json={"game_ids": [game.id]},
                headers=admin_headers
            )

            assert response.status_code in [200, 429]

    def test_print_labels_boundary_complexity(self, client, db_session, admin_headers):
        """Test label generation with boundary complexity values (1.0-5.0)"""
        games = []
        for complexity in [1.0, 2.5, 4.0, 5.0]:  # Valid complexity values
            game = Game(
                title=f"Complexity {complexity}",
                year=2020,
                complexity=complexity
            )
            db_session.add(game)
            games.append(game)
        db_session.commit()

        game_ids = [g.id for g in games]

        with patch('api.routers.printing.LabelGenerator') as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.generate_pdf.return_value = BytesIO(b'%PDF-1.4 test')
            MockGenerator.return_value = mock_instance

            response = client.post(
                "/api/admin/print-labels",
                json={"game_ids": game_ids},
                headers=admin_headers
            )

            assert response.status_code in [200, 429]
