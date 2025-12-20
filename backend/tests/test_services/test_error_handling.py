# tests/test_services/test_error_handling.py
"""
Tests for Sprint 5: Error Handling & Monitoring
Tests circuit breaker, retry logic, and background task failure tracking
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import httpx
from pybreaker import CircuitBreakerError


class TestCircuitBreaker:
    """Test BGG circuit breaker functionality"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Circuit breaker should open after consecutive failures"""
        from bgg_service import bgg_circuit_breaker, fetch_bgg_thing

        # Reset circuit breaker state
        bgg_circuit_breaker._state = bgg_circuit_breaker.STATE_CLOSED
        bgg_circuit_breaker.fail_counter = 0

        with patch("httpx.AsyncClient.get") as mock_get:
            # Simulate network failures
            mock_get.side_effect = httpx.NetworkError("Connection failed")

            # Attempt multiple failures to open circuit
            for i in range(6):  # fail_max is 5
                try:
                    await fetch_bgg_thing(123)
                except (CircuitBreakerError, Exception):
                    pass

            # Circuit should be open now
            assert bgg_circuit_breaker.current_state == "open"

    @pytest.mark.asyncio
    async def test_circuit_breaker_allows_after_reset(self):
        """Circuit breaker should allow requests after reset timeout"""
        from bgg_service import bgg_circuit_breaker, _is_bgg_available

        # Manually set circuit to closed state
        bgg_circuit_breaker._state = bgg_circuit_breaker.STATE_CLOSED
        bgg_circuit_breaker.fail_counter = 0

        assert _is_bgg_available() is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_excludes_validation_errors(self):
        """Circuit breaker should not count BGGServiceError as failures"""
        from bgg_service import bgg_circuit_breaker, fetch_bgg_thing, BGGServiceError

        # Reset circuit breaker
        bgg_circuit_breaker._state = bgg_circuit_breaker.STATE_CLOSED
        bgg_circuit_breaker.fail_counter = 0

        with patch("httpx.AsyncClient.get") as mock_get:
            # Simulate validation error (invalid game ID)
            mock_response = AsyncMock()
            mock_response.status_code = 400
            mock_get.return_value = mock_response

            try:
                await fetch_bgg_thing(999999999)
            except BGGServiceError:
                pass

            # Circuit should still be closed (validation errors don't count)
            assert bgg_circuit_breaker.current_state == "closed"
            assert bgg_circuit_breaker.fail_counter == 0


class TestRetryLogic:
    """Test retry logic with tenacity"""

    @pytest.mark.asyncio
    async def test_download_thumbnail_retries_on_network_error(self):
        """Download thumbnail should retry on network errors"""
        from services.image_service import ImageService
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        image_service = ImageService(mock_db)

        with patch("httpx.AsyncClient.get") as mock_get:
            # First two attempts fail, third succeeds
            mock_get.side_effect = [
                httpx.NetworkError("Network error"),
                httpx.NetworkError("Network error"),
                AsyncMock(
                    status_code=200,
                    content=b"fake image data",
                    raise_for_status=lambda: None,
                ),
            ]

            # Should succeed after retries
            with patch("builtins.open", create=True):
                result = await image_service.download_thumbnail(
                    "https://example.com/image.jpg", "test_game"
                )

            # Should have retried 3 times
            assert mock_get.call_count == 3
            assert result is not None

    @pytest.mark.asyncio
    async def test_download_thumbnail_gives_up_after_max_retries(self):
        """Download thumbnail should give up after max retries"""
        from services.image_service import ImageService
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        image_service = ImageService(mock_db)

        with patch("httpx.AsyncClient.get") as mock_get:
            # All attempts fail
            mock_get.side_effect = httpx.NetworkError("Network error")

            # Should return None after all retries exhausted
            result = await image_service.download_thumbnail(
                "https://example.com/image.jpg", "test_game"
            )

            # Should have attempted 3 times (max retries)
            assert mock_get.call_count == 3
            assert result is None


class TestBackgroundTaskFailureTracking:
    """Test background task failure tracking"""

    @pytest.mark.asyncio
    async def test_record_background_task_failure(self):
        """Should record background task failure in database"""
        from services.image_service import ImageService
        from models import BackgroundTaskFailure
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        image_service = ImageService(mock_db)

        test_error = ValueError("Test error message")

        await image_service._record_background_task_failure(
            task_type="thumbnail_download",
            game_id=123,
            error=test_error,
            url="https://example.com/image.jpg",
            retry_count=3,
        )

        # Verify database add and commit were called
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        # Verify the failure object was created with correct data
        added_failure = mock_db.add.call_args[0][0]
        assert isinstance(added_failure, BackgroundTaskFailure)
        assert added_failure.task_type == "thumbnail_download"
        assert added_failure.game_id == 123
        assert added_failure.error_message == "Test error message"
        assert added_failure.error_type == "ValueError"
        assert added_failure.retry_count == 3
        assert added_failure.url == "https://example.com/image.jpg"
        assert added_failure.resolved is False

    @pytest.mark.asyncio
    async def test_download_failure_records_in_database(self):
        """Failed download should be recorded in database"""
        from services.image_service import ImageService
        from models import Game
        from unittest.mock import MagicMock, AsyncMock

        mock_db = MagicMock()
        mock_game = MagicMock(spec=Game)
        mock_game.id = 123
        mock_game.title = "Test Game"

        mock_db.get.return_value = mock_game

        image_service = ImageService(mock_db)

        with patch("httpx.AsyncClient.get") as mock_get:
            # All download attempts fail
            mock_get.side_effect = httpx.NetworkError("Network error")

            with patch.object(
                image_service, "_record_background_task_failure"
            ) as mock_record:
                result = await image_service.download_and_update_game_thumbnail(
                    game_id=123, thumbnail_url="https://example.com/image.jpg"
                )

                # Verify failure was recorded
                assert result is False
                mock_record.assert_called_once()

                # Verify correct parameters
                call_args = mock_record.call_args
                assert call_args[1]["task_type"] == "thumbnail_download"
                assert call_args[1]["game_id"] == 123
                assert call_args[1]["url"] == "https://example.com/image.jpg"
                assert call_args[1]["retry_count"] == 3


class TestSentryIntegration:
    """Test Sentry error reporting"""

    @pytest.mark.asyncio
    async def test_sentry_captures_download_failures(self):
        """Sentry should capture download failures with context"""
        from services.image_service import ImageService
        from models import Game
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        mock_game = MagicMock(spec=Game)
        mock_game.id = 123
        mock_game.title = "Test Game"

        mock_db.get.return_value = mock_game

        image_service = ImageService(mock_db)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.NetworkError("Network error")

            with patch("sentry_sdk.capture_exception") as mock_sentry:
                with patch.object(
                    image_service, "_record_background_task_failure"
                ):
                    await image_service.download_and_update_game_thumbnail(
                        game_id=123, thumbnail_url="https://example.com/image.jpg"
                    )

                # Verify Sentry was called
                mock_sentry.assert_called()


class TestMonitoringEndpoints:
    """Test error monitoring API endpoints"""

    def test_get_background_failures_requires_auth(self, client):
        """Background failures endpoint should require authentication"""
        response = client.get("/api/admin/monitoring/background-failures")

        assert response.status_code == 401

    def test_circuit_breaker_status_requires_auth(self, client):
        """Circuit breaker status endpoint should require authentication"""
        response = client.get("/api/admin/monitoring/circuit-breaker-status")

        assert response.status_code == 401


# Fixtures
@pytest.fixture
def client():
    """Create test client"""
    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)
