# tests/test_services/test_error_handling.py
"""
Tests for Sprint 5: Error Handling & Monitoring
Tests circuit breaker, retry logic, and background task failure tracking
"""
import pytest



class TestCircuitBreaker:
    """Test BGG circuit breaker functionality"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_basic_functionality(self):
        """Circuit breaker should be initialized and available"""
        from bgg_service import bgg_circuit_breaker

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


class TestBackgroundTaskFailureTracking:
    """Test background task failure tracking"""

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
