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
    async def test_proxy_image_http_error(self, db_session):
        """Test proxy_image raises HTTPError on failure"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPStatusError(
            "Not Found",
            request=Mock(),
            response=Mock(status_code=404)
        ))

        service = ImageService(db_session, http_client=mock_client)

        with pytest.raises(httpx.HTTPStatusError):
            await service.proxy_image("https://example.com/missing.jpg")

    @pytest.mark.asyncio
    async def test_download_thumbnail_with_query_params(self, db_session):
        """Test thumbnail download with URL query parameters"""
        mock_response = Mock()
        mock_response.content = b"image data"
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)

        with patch("builtins.open", mock_open()):
            result = await service.download_thumbnail(
                "https://example.com/image.jpg?size=large&v=2",
                "test_game"
            )

        assert result is not None
        assert result.endswith(".jpg")

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


class TestBackgroundTaskFailure:
    """Tests for _record_background_task_failure method"""

    @pytest.mark.asyncio
    async def test_record_background_task_failure_success(self, db_session):
        """Test successful recording of background task failure"""
        from models import BackgroundTaskFailure

        service = ImageService(db_session)
        test_error = ValueError("Test error message")

        await service._record_background_task_failure(
            task_type="thumbnail_download",
            game_id=123,
            error=test_error,
            url="https://example.com/image.jpg",
            retry_count=3
        )

        # Verify the failure was recorded in the database
        failures = db_session.query(BackgroundTaskFailure).all()
        assert len(failures) == 1
        assert failures[0].task_type == "thumbnail_download"
        assert failures[0].game_id == 123
        assert "Test error message" in failures[0].error_message
        assert failures[0].error_type == "ValueError"
        assert failures[0].retry_count == 3
        assert failures[0].url == "https://example.com/image.jpg"
        assert failures[0].resolved is False

    @pytest.mark.asyncio
    async def test_record_background_task_failure_without_url(self, db_session):
        """Test recording failure without URL"""
        from models import BackgroundTaskFailure

        service = ImageService(db_session)
        test_error = RuntimeError("No URL error")

        await service._record_background_task_failure(
            task_type="image_processing",
            game_id=456,
            error=test_error,
            retry_count=1
        )

        failures = db_session.query(BackgroundTaskFailure).all()
        assert len(failures) == 1
        assert failures[0].url is None


class TestCleanupOldThumbnailsDetailed:
    """Detailed tests for cleanup_old_thumbnails method"""

    def test_cleanup_skips_recent_files(self, db_session):
        """Test that recent files are not deleted"""
        import time

        service = ImageService(db_session)

        with patch("pathlib.Path.glob") as mock_glob:
            # Create a file that's only 1 day old
            mock_file = Mock()
            mock_file.is_file.return_value = True
            mock_file.stat.return_value.st_mtime = time.time() - (1 * 24 * 60 * 60)
            mock_file.unlink = Mock()

            mock_glob.return_value = [mock_file]

            # Cleanup files older than 30 days
            count = service.cleanup_old_thumbnails(days=30)

            assert count == 0
            mock_file.unlink.assert_not_called()

    def test_cleanup_skips_directories(self, db_session):
        """Test that directories are skipped during cleanup"""
        service = ImageService(db_session)

        with patch("pathlib.Path.glob") as mock_glob:
            mock_dir = Mock()
            mock_dir.is_file.return_value = False  # It's a directory

            mock_glob.return_value = [mock_dir]

            count = service.cleanup_old_thumbnails(days=30)

            assert count == 0

    def test_cleanup_multiple_files(self, db_session):
        """Test cleanup of multiple files with mixed ages"""
        import time

        service = ImageService(db_session)

        with patch("pathlib.Path.glob") as mock_glob:
            # Old file (should be deleted)
            old_file = Mock()
            old_file.is_file.return_value = True
            old_file.stat.return_value.st_mtime = 0
            old_file.unlink = Mock()

            # Recent file (should be kept)
            recent_file = Mock()
            recent_file.is_file.return_value = True
            recent_file.stat.return_value.st_mtime = time.time()
            recent_file.unlink = Mock()

            mock_glob.return_value = [old_file, recent_file]

            count = service.cleanup_old_thumbnails(days=30)

            assert count == 1
            old_file.unlink.assert_called_once()
            recent_file.unlink.assert_not_called()


class TestProxyImageHeaders:
    """Tests for proxy_image HTTP headers"""

    @pytest.mark.asyncio
    async def test_proxy_image_sends_browser_headers(self, db_session):
        """Test that proxy_image sends proper browser headers for BGG"""
        mock_response = Mock()
        mock_response.content = b"image data"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)
        await service.proxy_image("https://cf.geekdo-images.com/test.jpg")

        # Verify headers were passed
        call_args = mock_client.get.call_args
        headers = call_args.kwargs.get('headers', {})

        assert "User-Agent" in headers
        assert "Mozilla" in headers["User-Agent"]
        assert "Referer" in headers
        assert "boardgamegeek.com" in headers["Referer"]
        assert "Accept" in headers
        assert "image" in headers["Accept"]

    @pytest.mark.asyncio
    async def test_proxy_image_avif_format(self, db_session):
        """Test proxying AVIF images"""
        mock_response = Mock()
        mock_response.content = b"AVIF data"
        mock_response.headers = {"content-type": "image/avif"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)
        content, content_type, _ = await service.proxy_image("https://example.com/img.avif")

        assert content_type == "image/avif"


class TestDownloadThumbnailExtensions:
    """Tests for download_thumbnail file extension handling"""

    @pytest.mark.asyncio
    async def test_download_thumbnail_png_extension(self, db_session):
        """Test PNG file extension is preserved"""
        mock_response = Mock()
        mock_response.content = b"PNG data"
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)

        with patch("builtins.open", mock_open()):
            result = await service.download_thumbnail(
                "https://example.com/image.png",
                "test_game"
            )

        assert result.endswith(".png")

    @pytest.mark.asyncio
    async def test_download_thumbnail_webp_extension(self, db_session):
        """Test WebP file extension is preserved"""
        mock_response = Mock()
        mock_response.content = b"WebP data"
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)

        with patch("builtins.open", mock_open()):
            result = await service.download_thumbnail(
                "https://example.com/image.webp",
                "test_game"
            )

        assert result.endswith(".webp")

    @pytest.mark.asyncio
    async def test_download_thumbnail_jpeg_extension(self, db_session):
        """Test JPEG file extension is preserved"""
        mock_response = Mock()
        mock_response.content = b"JPEG data"
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        service = ImageService(db_session, http_client=mock_client)

        with patch("builtins.open", mock_open()):
            result = await service.download_thumbnail(
                "https://example.com/image.jpeg",
                "test_game"
            )

        assert result.endswith(".jpeg")


class TestReimportGameThumbnailDetailed:
    """Detailed tests for reimport_game_thumbnail method"""

    @pytest.mark.asyncio
    async def test_reimport_updates_game_fields(self, db_session):
        """Test that reimport properly updates game fields via GameService"""
        game = Game(title="Original Title", bgg_id=12345)
        db_session.add(game)
        db_session.commit()
        game_id = game.id

        mock_bgg_data = {
            "title": "Updated Title",
            "description": "New description",
            "year": 2024,
            "thumbnail": "https://example.com/new-thumb.jpg",
            "image": "https://example.com/new-image.jpg",
        }

        service = ImageService(db_session)

        with patch("bgg_service.fetch_bgg_thing", new_callable=AsyncMock) as mock_fetch, \
             patch("services.game_service.GameService") as MockGameService:

            mock_fetch.return_value = mock_bgg_data

            mock_game_service = MockGameService.return_value
            mock_game_service.update_game_from_bgg_data = Mock()

            result = await service.reimport_game_thumbnail(game_id, 12345)

            assert result is True

            # Verify GameService was instantiated with correct db session
            MockGameService.assert_called_once_with(db_session)

            # Verify update_game_from_bgg_data was called
            mock_game_service.update_game_from_bgg_data.assert_called_once()
            call_args = mock_game_service.update_game_from_bgg_data.call_args
            assert call_args.kwargs.get('commit') is True


class TestProxyImageNetworkErrors:
    """Tests for proxy_image network error handling"""

    @pytest.mark.asyncio
    async def test_proxy_image_connection_error(self, db_session):
        """Test proxy_image handles connection errors"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        service = ImageService(db_session, http_client=mock_client)

        with pytest.raises(httpx.ConnectError):
            await service.proxy_image("https://unreachable.example.com/image.jpg")

    @pytest.mark.asyncio
    async def test_proxy_image_timeout(self, db_session):
        """Test proxy_image handles timeout"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))

        service = ImageService(db_session, http_client=mock_client)

        with pytest.raises(httpx.TimeoutException):
            await service.proxy_image("https://slow.example.com/image.jpg")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
