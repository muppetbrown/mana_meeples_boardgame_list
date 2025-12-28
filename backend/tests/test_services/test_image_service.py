"""Tests for ImageService business logic layer."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch, mock_open
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


class TestImageFormats:
    """Test handling of different image formats"""

    @pytest.mark.asyncio
    async def test_proxy_image_png_format(self, db_session):
        """Test proxying PNG images"""
        mock_response = Mock()
        mock_response.content = b"PNG data"
        mock_response.headers = {"content-type": "image/png"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)
        content, content_type, _ = await service.proxy_image("https://example.com/img.png")

        assert content_type == "image/png"

    @pytest.mark.asyncio
    async def test_proxy_image_gif_format(self, db_session):
        """Test proxying GIF images"""
        mock_response = Mock()
        mock_response.content = b"GIF data"
        mock_response.headers = {"content-type": "image/gif"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)
        content, content_type, _ = await service.proxy_image("https://example.com/img.gif")

        assert content_type == "image/gif"

    @pytest.mark.asyncio
    async def test_proxy_image_webp_format(self, db_session):
        """Test proxying WebP images"""
        mock_response = Mock()
        mock_response.content = b"WebP data"
        mock_response.headers = {"content-type": "image/webp"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)
        content, content_type, _ = await service.proxy_image("https://example.com/img.webp")

        assert content_type == "image/webp"


class TestImageEdgeCases:
    """Test edge cases and error scenarios"""

    @pytest.mark.asyncio
    async def test_download_thumbnail_with_invalid_url(self, db_session):
        """Test thumbnail download with malformed URL"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.InvalidURL("Malformed URL"))

        service = ImageService(db_session, http_client=mock_client)
        result = await service.download_thumbnail("not-a-url", "game")

        assert result is None

    @pytest.mark.asyncio
    async def test_download_thumbnail_timeout(self, db_session):
        """Test thumbnail download timeout"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))

        service = ImageService(db_session, http_client=mock_client)
        result = await service.download_thumbnail("https://slow-server.com/img.jpg", "game")

        assert result is None

    @pytest.mark.asyncio
    async def test_proxy_image_empty_response(self, db_session):
        """Test proxying image with empty response"""
        mock_response = Mock()
        mock_response.content = b""
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)
        content, content_type, _ = await service.proxy_image("https://example.com/empty.jpg")

        assert content == b""
        assert content_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_proxy_image_custom_cache_max_age(self, db_session):
        """Test proxy with custom cache max age"""
        mock_response = Mock()
        mock_response.content = b"data"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)
        _, _, cache_control = await service.proxy_image(
            "https://example.com/img.jpg",
            cache_max_age=86400
        )

        assert "max-age=86400" in cache_control

    @pytest.mark.asyncio
    async def test_record_background_task_failure_error_handling(self, db_session):
        """Test error handling when recording background task failure itself fails"""
        service = ImageService(db_session)
        
        # Create a mock error
        test_error = Exception("Test error")
        
        # Mock db.add to raise an exception
        with patch.object(db_session, "add", side_effect=Exception("Database error")), \
             patch("services.image_service.sentry_sdk.capture_exception") as mock_sentry:
            # Should not raise - errors are swallowed
            await service._record_background_task_failure(
                task_type="test_task",
                game_id=1,
                error=test_error,
                url="https://example.com/test.jpg",
                retry_count=3
            )
            
            # Sentry should still be called with the original error
            mock_sentry.assert_called_once_with(test_error)

    @pytest.mark.asyncio

    @pytest.mark.asyncio
    async def test_download_thumbnail_with_invalid_extension(self, db_session):
        """Test download_thumbnail defaults to jpg for unknown extensions"""
        mock_response = Mock()
        mock_response.content = b"image_data"
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.path.join", return_value="/tmp/thumbs/test.jpg"):
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            result = await service.download_thumbnail(
                "https://example.com/image.unknown",
                "test"
            )

            assert result == "test.jpg"

    @pytest.mark.asyncio
    async def test_reimport_game_thumbnail_success(self, db_session):
        """Test successful game thumbnail reimport"""
        game = Game(id=1, title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.commit()

        mock_bgg_data = {
            "title": "Updated Game",
            "description": "Updated description",
            "year": 2023,
        }

        service = ImageService(db_session)

        with patch("bgg_service.fetch_bgg_thing", new_callable=AsyncMock) as mock_fetch, \
             patch("services.game_service.GameService") as MockGameService:
            
            mock_fetch.return_value = mock_bgg_data
            
            mock_game_service = MockGameService.return_value
            mock_game_service.update_game_from_bgg_data = Mock()

            result = await service.reimport_game_thumbnail(1, 12345)

            assert result is True
            mock_fetch.assert_called_once_with(12345)
            mock_game_service.update_game_from_bgg_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_reimport_game_thumbnail_game_not_found(self, db_session):
        """Test reimport when game doesn't exist"""
        service = ImageService(db_session)

        result = await service.reimport_game_thumbnail(999, 12345)

        assert result is False

    @pytest.mark.asyncio
    async def test_reimport_game_thumbnail_bgg_error(self, db_session):
        """Test reimport handles BGG fetch errors"""
        game = Game(id=1, title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.commit()

        service = ImageService(db_session)

        with patch("bgg_service.fetch_bgg_thing", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("BGG API error")

            result = await service.reimport_game_thumbnail(1, 12345)

            assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
