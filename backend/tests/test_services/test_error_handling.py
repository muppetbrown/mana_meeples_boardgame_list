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
    async def test_circuit_breaker_basic_functionality(self):
        """Circuit breaker should be initialized and available"""
        from bgg_service import bgg_circuit_breaker, _is_bgg_available

        # Circuit breaker should exist
        assert bgg_circuit_breaker is not None

        # Should have proper configuration
        assert bgg_circuit_breaker.fail_max == 5
        assert bgg_circuit_breaker.reset_timeout == 60

    @pytest.mark.asyncio
    async def test_circuit_breaker_availability_check(self):
        """Test circuit breaker availability helper function"""
        from bgg_service import _is_bgg_available

        # Function should return boolean
        result = _is_bgg_available()
        assert isinstance(result, bool)


class TestRetryLogic:
    """Test retry logic with tenacity"""

    @pytest.mark.asyncio
    async def test_image_service_has_retry_decorator(self):
        """Download thumbnail method should have retry decorator"""
        from services.image_service import ImageService
        import inspect

        # Check that download_thumbnail has the retry decorator
        # The presence of tenacity retry attributes indicates the decorator is applied
        assert hasattr(ImageService.download_thumbnail, "__wrapped__") or \
               hasattr(ImageService.download_thumbnail, "retry") or \
               "retry" in str(ImageService.download_thumbnail)


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
    async def test_background_task_failure_model(self):
        """BackgroundTaskFailure model should have correct structure"""
        from models import BackgroundTaskFailure

        # Test model can be instantiated
        failure = BackgroundTaskFailure(
            task_type="test_task",
            game_id=123,
            error_message="Test error",
            error_type="TestError",
            stack_trace="Test stack trace",
            retry_count=3,
            url="https://example.com",
            resolved=False,
        )

        assert failure.task_type == "test_task"
        assert failure.game_id == 123
        assert failure.error_message == "Test error"
        assert failure.resolved is False


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
        """Background failures endpoint should require authentication or be rate limited"""
        response = client.get("/api/admin/monitoring/background-failures")

        # Should either require auth (401) or be rate limited (429)
        assert response.status_code in [401, 429]

    def test_circuit_breaker_status_requires_auth(self, client):
        """Circuit breaker status endpoint should require authentication or be rate limited"""
        response = client.get("/api/admin/monitoring/circuit-breaker-status")

        # Should either require auth (401) or be rate limited (429)
        assert response.status_code in [401, 429]


class TestSentryConfiguration:
    """Test Sentry configuration enhancements"""

    def test_sentry_before_send_filters_development(self):
        """Sentry before_send should filter development errors"""
        from main import before_send_sentry
        import os

        # Mock development environment
        os.environ["ENVIRONMENT"] = "development"

        event = {"level": "error", "message": "Test error"}
        hint = {}

        result = before_send_sentry(event, hint)

        # Should filter out development errors
        assert result is None

        # Clean up
        os.environ.pop("ENVIRONMENT", None)

    def test_sentry_before_send_enriches_events(self):
        """Sentry before_send should enrich events with tags"""
        from main import before_send_sentry
        import os

        # Mock production environment
        os.environ["ENVIRONMENT"] = "production"

        event = {"level": "error", "message": "Test error"}
        hint = {}

        result = before_send_sentry(event, hint)

        # Should enrich with tags
        assert result is not None
        assert "tags" in result
        assert "python_version" in result["tags"]

        # Clean up
        os.environ.pop("ENVIRONMENT", None)


# Fixtures
@pytest.fixture
def client():
    """Create test client"""
    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)
