"""
Tests for backfill_cloudinary_urls script
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from models import Game


class TestBackfillCloudinaryUrlsScript:
    """Tests for the backfill_cloudinary_urls.py script"""

    @pytest.fixture
    def mock_db(self, db_session):
        """Mock database session for script"""
        with patch('scripts.backfill_cloudinary_urls.get_db') as mock_get_db:
            mock_get_db.return_value = iter([db_session])
            yield db_session

    @pytest.fixture
    def mock_cloudinary(self):
        """Mock cloudinary service"""
        with patch('scripts.backfill_cloudinary_urls.cloudinary_service') as mock_service:
            mock_service.enabled = True
            mock_service.generate_optimized_url.return_value = (
                "https://res.cloudinary.com/test/image/upload/optimized.jpg"
            )
            yield mock_service

    def test_backfill_with_dry_run(self, mock_db, mock_cloudinary):
        """Test backfill in dry-run mode doesn't commit changes"""
        from scripts.backfill_cloudinary_urls import backfill_cloudinary_urls
        from unittest.mock import MagicMock

        # Create test game
        game = Game(
            title="Test Game",
            bgg_id=1001,
            image="https://cf.geekdo-images.com/original/img/test.jpg",
            cloudinary_url=None
        )
        mock_db.add(game)
        mock_db.commit()

        # Mock the rollback method
        mock_db.rollback = MagicMock()

        stats = backfill_cloudinary_urls(dry_run=True)

        assert stats['total_games'] == 1
        assert stats['updated'] == 1
        # In dry run, game object is updated but not committed
        mock_db.rollback.assert_called()

    def test_backfill_with_limit(self, mock_db, mock_cloudinary):
        """Test backfill respects limit parameter"""
        from scripts.backfill_cloudinary_urls import backfill_cloudinary_urls

        # Create 5 test games
        for i in range(5):
            game = Game(
                title=f"Game {i}",
                bgg_id=1000 + i,
                image=f"https://cf.geekdo-images.com/original/img/test{i}.jpg",
                cloudinary_url=None
            )
            mock_db.add(game)
        mock_db.commit()

        stats = backfill_cloudinary_urls(dry_run=False, limit=3)

        assert stats['total_games'] == 3
        assert stats['processed'] == 3

    def test_backfill_uses_image_field(self, mock_db, mock_cloudinary):
        """Test backfill uses image field"""
        from scripts.backfill_cloudinary_urls import backfill_cloudinary_urls

        game = Game(
            title="Test Game",
            bgg_id=1001,
            image="https://cf.geekdo-images.com/original/img/full.jpg",
            cloudinary_url=None
        )
        mock_db.add(game)
        mock_db.commit()

        backfill_cloudinary_urls(dry_run=False)

        # Verify it called with the full image URL
        mock_cloudinary.generate_optimized_url.assert_called()
        call_args = mock_cloudinary.generate_optimized_url.call_args[0]
        assert "full.jpg" in call_args[0]

    def test_backfill_skips_games_without_images(self, mock_db, mock_cloudinary):
        """Test backfill skips games that have no image URLs"""
        from scripts.backfill_cloudinary_urls import backfill_cloudinary_urls

        game = Game(
            title="Game Without Images",
            bgg_id=1001,
            image=None
        )
        mock_db.add(game)
        mock_db.commit()

        stats = backfill_cloudinary_urls(dry_run=False)

        # Games without images are filtered out at the query level,
        # so they won't be in total_games or processed
        assert stats['total_games'] == 0
        assert stats['processed'] == 0
        assert stats['updated'] == 0

    def test_backfill_with_force_regenerates_existing_urls(self, mock_db, mock_cloudinary):
        """Test backfill with force=True regenerates URLs even if they exist"""
        from scripts.backfill_cloudinary_urls import backfill_cloudinary_urls

        game = Game(
            title="Test Game",
            bgg_id=1001,
            image="https://cf.geekdo-images.com/original/img/test.jpg",
            cloudinary_url="https://res.cloudinary.com/test/old-url.jpg"
        )
        mock_db.add(game)
        mock_db.commit()

        stats = backfill_cloudinary_urls(dry_run=False, force=True)

        assert stats['total_games'] == 1
        assert stats['updated'] == 1

    def test_backfill_handles_cloudinary_error(self, mock_db, mock_cloudinary):
        """Test backfill handles errors from Cloudinary service gracefully"""
        from scripts.backfill_cloudinary_urls import backfill_cloudinary_urls

        game = Game(
            title="Test Game",
            bgg_id=1001,
            image="https://cf.geekdo-images.com/original/img/test.jpg",
            cloudinary_url=None
        )
        mock_db.add(game)
        mock_db.commit()

        # Make cloudinary service raise an error
        mock_cloudinary.generate_optimized_url.side_effect = Exception("Cloudinary error")

        stats = backfill_cloudinary_urls(dry_run=False)

        assert stats['failed'] == 1
        assert len(stats['errors']) == 1
        assert "Cloudinary error" in stats['errors'][0]

    def test_backfill_with_cloudinary_disabled(self, mock_db):
        """Test backfill when Cloudinary is disabled (warning logged)"""
        from scripts.backfill_cloudinary_urls import backfill_cloudinary_urls

        with patch('scripts.backfill_cloudinary_urls.cloudinary_service') as mock_service:
            mock_service.enabled = False
            mock_service.generate_optimized_url.return_value = "fallback-url"

            game = Game(
                title="Test Game",
                bgg_id=1001,
                image="https://cf.geekdo-images.com/original/img/test.jpg",
                cloudinary_url=None
            )
            mock_db.add(game)
            mock_db.commit()

            stats = backfill_cloudinary_urls(dry_run=False)

            # Should still update, but with warning
            assert stats['updated'] == 1

    def test_backfill_updates_game_correctly(self, mock_db, mock_cloudinary):
        """Test backfill updates game.cloudinary_url field correctly"""
        from scripts.backfill_cloudinary_urls import backfill_cloudinary_urls

        expected_url = "https://res.cloudinary.com/test/image/upload/w_800,h_800/test.jpg"
        mock_cloudinary.generate_optimized_url.return_value = expected_url

        game = Game(
            title="Test Game",
            bgg_id=1001,
            image="https://cf.geekdo-images.com/original/img/test.jpg",
            cloudinary_url=None
        )
        mock_db.add(game)
        mock_db.commit()
        game_id = game.id

        backfill_cloudinary_urls(dry_run=False)

        # Query the game again from the database to verify the update
        updated_game = mock_db.query(Game).filter_by(id=game_id).first()
        assert updated_game.cloudinary_url == expected_url

    def test_print_summary(self):
        """Test print_summary function outputs correct statistics"""
        from scripts.backfill_cloudinary_urls import print_summary

        stats = {
            'total_games': 100,
            'processed': 100,
            'updated': 90,
            'skipped': 5,
            'failed': 5,
            'errors': ['Error 1', 'Error 2']
        }

        # Should not raise any exceptions
        with patch('scripts.backfill_cloudinary_urls.logger') as mock_logger:
            print_summary(stats, dry_run=False)
            # Verify logger.info was called multiple times
            assert mock_logger.info.call_count > 0

    def test_main_function_with_dry_run_flag(self):
        """Test main function respects --dry-run flag"""
        from scripts.backfill_cloudinary_urls import main

        test_args = ['script_name', '--dry-run']
        with patch('sys.argv', test_args), \
             patch('scripts.backfill_cloudinary_urls.backfill_cloudinary_urls') as mock_backfill, \
             patch('scripts.backfill_cloudinary_urls.print_summary'):

            mock_backfill.return_value = {
                'total_games': 0,
                'processed': 0,
                'updated': 0,
                'skipped': 0,
                'failed': 0,
                'errors': []
            }

            main()

            # Verify backfill was called with dry_run=True
            mock_backfill.assert_called_once()
            call_kwargs = mock_backfill.call_args[1]
            assert call_kwargs['dry_run'] == True

    def test_main_function_with_limit_flag(self):
        """Test main function respects --limit flag"""
        from scripts.backfill_cloudinary_urls import main

        test_args = ['script_name', '--dry-run', '--limit', '10']
        with patch('sys.argv', test_args), \
             patch('scripts.backfill_cloudinary_urls.backfill_cloudinary_urls') as mock_backfill, \
             patch('scripts.backfill_cloudinary_urls.print_summary'):

            mock_backfill.return_value = {
                'total_games': 0,
                'processed': 0,
                'updated': 0,
                'skipped': 0,
                'failed': 0,
                'errors': []
            }

            main()

            # Verify backfill was called with limit=10
            call_kwargs = mock_backfill.call_args[1]
            assert call_kwargs['limit'] == 10
