"""Tests for ImageService business logic layer."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
import httpx

from services.image_service import ImageService
from models import Game


class TestImageService:
    """Test suite for ImageService"""

    @pytest.mark.asyncio
    async def test_download_thumbnail_success(self, db_session):
        """Test successful thumbnail download"""
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)

        with patch("builtins.open", mock_open()) as mock_file:
            result = await service.download_thumbnail(
                "https://example.com/image.jpg",
                "test_game"
            )

        assert result is not None
        assert "test_game" in result
        assert result.endswith(".jpg")
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_thumbnail_failure(self, db_session):
        """Test thumbnail download failure"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Network error"))

        service = ImageService(db_session, http_client=mock_client)

        result = await service.download_thumbnail(
            "https://example.com/image.jpg",
            "test_game"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_download_and_update_game_thumbnail_success(self, db_session):
        """Test downloading and updating game thumbnail"""
        # Create test game
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.commit()

        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)

        with patch("builtins.open", mock_open()):
            result = await service.download_and_update_game_thumbnail(
                game.id,
                "https://example.com/image.jpg"
            )

        assert result is True
        # Refresh game from DB
        db_session.refresh(game)
        # Check that thumbnail fields were updated if they exist
        if hasattr(game, 'thumbnail_file'):
            assert game.thumbnail_file is not None

    @pytest.mark.asyncio
    async def test_download_and_update_game_thumbnail_not_found(self, db_session):
        """Test thumbnail update for non-existent game"""
        mock_client = AsyncMock()
        service = ImageService(db_session, http_client=mock_client)

        result = await service.download_and_update_game_thumbnail(
            999,  # Non-existent game ID
            "https://example.com/image.jpg"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_download_and_update_with_retry(self, db_session):
        """Test thumbnail download retry logic"""
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.commit()

        # Mock failures then success
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[
            httpx.HTTPError("Fail 1"),
            httpx.HTTPError("Fail 2"),
            mock_response  # Success on 3rd attempt
        ])

        service = ImageService(db_session, http_client=mock_client)

        with patch("builtins.open", mock_open()):
            result = await service.download_and_update_game_thumbnail(
                game.id,
                "https://example.com/image.jpg",
                max_retries=3
            )

        # Should succeed after retries
        assert result is True
        assert mock_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_download_exceeds_max_retries(self, db_session):
        """Test thumbnail download exceeding max retries"""
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.commit()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Always fails"))

        service = ImageService(db_session, http_client=mock_client)

        result = await service.download_and_update_game_thumbnail(
            game.id,
            "https://example.com/image.jpg",
            max_retries=2
        )

        assert result is False
        # Should try max_retries times
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_proxy_image_success(self, db_session):
        """Test image proxying with caching"""
        mock_response = Mock()
        mock_response.content = b"proxied image data"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)

        content, content_type, cache_control = await service.proxy_image(
            "https://example.com/image.jpg",
            cache_max_age=600
        )

        assert content == b"proxied image data"
        assert content_type == "image/jpeg"
        assert "max-age=600" in cache_control
        assert "public" in cache_control

    @pytest.mark.asyncio
    async def test_proxy_image_default_content_type(self, db_session):
        """Test proxy image with default content type"""
        mock_response = Mock()
        mock_response.content = b"data"
        mock_response.headers = {}  # No content-type header
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)

        content, content_type, cache_control = await service.proxy_image(
            "https://example.com/image.jpg"
        )

        assert content_type == "application/octet-stream"

    def test_cleanup_old_thumbnails(self, db_session):
        """Test cleanup of old thumbnail files"""
        service = ImageService(db_session)

        with patch("pathlib.Path.glob") as mock_glob:
            mock_file = Mock()
            mock_file.is_file.return_value = True
            mock_file.stat.return_value.st_mtime = 0  # Very old file
            mock_file.unlink = Mock()

            mock_glob.return_value = [mock_file]

            count = service.cleanup_old_thumbnails(days=30)

            assert count == 1
            mock_file.unlink.assert_called_once()

    def test_cleanup_handles_errors(self, db_session):
        """Test cleanup handles errors gracefully"""
        service = ImageService(db_session)

        with patch("pathlib.Path.glob", side_effect=Exception("Access denied")):
            count = service.cleanup_old_thumbnails()

            # Should not raise, should return 0
            assert count == 0


class TestImageServiceInit:
    """Test ImageService initialization"""

    def test_init_with_custom_client(self, db_session):
        """Test initialization with custom HTTP client"""
        custom_client = AsyncMock()
        service = ImageService(db_session, http_client=custom_client)

        assert service.http_client == custom_client

    def test_init_creates_default_client(self, db_session):
        """Test initialization creates default client if none provided"""
        service = ImageService(db_session)

        assert service.http_client is not None
        assert isinstance(service.http_client, httpx.AsyncClient)

    def test_ensures_thumbs_dir_exists(self, db_session):
        """Test that thumbnail directory is created on init"""
        with patch("os.makedirs") as mock_makedirs:
            service = ImageService(db_session)

            # Should have called makedirs with exist_ok=True
            mock_makedirs.assert_called_once()
            assert mock_makedirs.call_args[1]["exist_ok"] is True
