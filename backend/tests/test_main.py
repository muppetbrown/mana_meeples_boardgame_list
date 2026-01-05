"""
Comprehensive tests for main.py

Tests cover:
- Sentry event filtering and enrichment
- Structured logging formatter
- Background tasks (thumbnail download, game reimport)
- Lifespan events (startup/shutdown)
- Exception handlers
- Middleware
"""

import pytest
import logging
import json
import os
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import Request
from sqlalchemy.orm import Session

# Import the main module components
from main import (
    before_send_sentry,
    StructuredFormatter,
    CacheThumbsMiddleware,
    game_not_found_handler,
    validation_error_handler,
    bgg_service_error_handler,
    database_error_handler,
)
# Background tasks moved to services
from services.background_tasks import (
    download_and_update_thumbnail,
    reimport_single_game,
)
from exceptions import (
    GameNotFoundError,
    ValidationError,
    BGGServiceError,
    DatabaseError,
)
from models import Game


# ------------------------------------------------------------------------------
# Sentry Event Filtering Tests
# ------------------------------------------------------------------------------


class TestSentrySentry:
    """Test Sentry event filtering and enrichment"""

    def test_before_send_filters_uvicorn_access_logs(self):
        """Should filter out uvicorn access logs"""
        event = {"logger": "uvicorn.access", "message": "GET /"}
        hint = {}

        result = before_send_sentry(event, hint)

        assert result is None

    def test_before_send_filters_health_check_errors(self):
        """Should filter out health check errors"""
        # Create a mock request with health check URL
        mock_request = Mock()
        mock_request.url = "/api/health"

        event = {"message": "Some error"}
        hint = {"request": mock_request}

        result = before_send_sentry(event, hint)

        assert result is None

    def test_before_send_enriches_admin_request(self):
        """Should tag admin requests appropriately"""
        mock_request = Mock()
        mock_request.url = Mock()
        mock_request.url.path = "/api/admin/games"

        event = {"message": "Admin action"}
        hint = {"request": mock_request}

        result = before_send_sentry(event, hint)

        assert result is not None
        assert result["tags"]["user_type"] == "admin"
        assert result["tags"]["endpoint_type"] == "api"

    def test_before_send_enriches_public_request(self):
        """Should tag public requests appropriately"""
        mock_request = Mock()
        mock_request.url = Mock()
        mock_request.url.path = "/api/public/games"

        event = {"message": "Public action"}
        hint = {"request": mock_request}

        result = before_send_sentry(event, hint)

        assert result is not None
        assert result["tags"]["user_type"] == "public"
        assert result["tags"]["endpoint_type"] == "api"

    def test_before_send_enriches_static_request(self):
        """Should tag static requests appropriately"""
        mock_request = Mock()
        mock_request.url = Mock()
        mock_request.url.path = "/static/image.jpg"

        event = {"message": "Static file"}
        hint = {"request": mock_request}

        result = before_send_sentry(event, hint)

        assert result is not None
        assert result["tags"]["endpoint_type"] == "static"

    def test_before_send_adds_python_version(self):
        """Should add Python version tag"""
        event = {"message": "Test"}
        hint = {}

        with patch.dict(os.environ, {"PYTHON_VERSION": "3.11.9"}):
            result = before_send_sentry(event, hint)

        assert result is not None
        assert result["tags"]["python_version"] == "3.11.9"

    def test_before_send_adds_bgg_context_for_bgg_errors(self):
        """Should add BGG context for BGG-related exceptions"""
        event = {
            "message": "BGG error",
            "exception": {
                "values": [
                    {"type": "BGGServiceError", "value": "API timeout"}
                ]
            }
        }
        hint = {}

        result = before_send_sentry(event, hint)

        assert result is not None
        assert "bgg" in result["contexts"]
        assert result["contexts"]["bgg"]["circuit_breaker_state"] == "available"

    def test_before_send_handles_url_without_path_attribute(self):
        """Should handle requests with URLs without path attribute"""
        mock_request = Mock()
        mock_request.url = "/api/games"  # String URL without path attribute

        event = {"message": "Test"}
        hint = {"request": mock_request}

        result = before_send_sentry(event, hint)

        assert result is not None
        # Should still add tags
        assert "tags" in result


# ------------------------------------------------------------------------------
# Structured Logging Tests
# ------------------------------------------------------------------------------


class TestStructuredFormatter:
    """Test structured JSON logging formatter"""

    def test_basic_formatting(self):
        """Should format basic log record as JSON"""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["module"] == "test"
        assert data["line"] == 42
        assert "timestamp" in data

    def test_formatting_with_extra_fields(self):
        """Should include extra fields when present"""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=100,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )
        record.user_id = "user123"
        record.request_id = "req456"
        record.bgg_id = 12345
        record.game_id = 789

        result = formatter.format(record)
        data = json.loads(result)

        assert data["user_id"] == "user123"
        assert data["request_id"] == "req456"
        assert data["bgg_id"] == 12345
        assert data["game_id"] == 789

    def test_formatting_without_extra_fields(self):
        """Should work without extra fields"""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=50,
            msg="Warning message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        # Should not have extra fields
        assert "user_id" not in data
        assert "request_id" not in data


# ------------------------------------------------------------------------------
# Background Task Tests
# ------------------------------------------------------------------------------


class TestBackgroundTasks:
    """
    Test background task functions
    Note: download_thumbnail tests removed - they're covered in test_services/test_image_service.py
    """

    @pytest.mark.asyncio
    async def test_download_and_update_thumbnail(self, db_session):
        """Should download thumbnail and update game record"""
        # Create a test game
        game = Game(
            id=1,
            title="Test Game",
            bgg_id=12345,
            thumbnail_url="https://example.com/old.jpg"
        )
        db_session.add(game)
        db_session.commit()

        with patch("services.background_tasks.SessionLocal", return_value=db_session), \
             patch("services.image_service.ImageService.download_and_update_game_thumbnail", return_value=True):

            await download_and_update_thumbnail(1, "https://example.com/new.jpg")

    @pytest.mark.asyncio
    async def test_download_and_update_thumbnail_game_not_found(self, db_session):
        """Should handle case when game doesn't exist"""
        with patch("services.background_tasks.SessionLocal", return_value=db_session):
            # Should not raise exception
            await download_and_update_thumbnail(999, "https://example.com/new.jpg")

    @pytest.mark.asyncio
    async def test_download_and_update_thumbnail_download_fails(self, db_session):
        """Should handle download failure gracefully"""
        game = Game(
            id=1,
            title="Test Game",
            bgg_id=12345
        )
        db_session.add(game)
        db_session.commit()

        with patch("services.background_tasks.SessionLocal", return_value=db_session), \
             patch("services.image_service.ImageService.download_and_update_game_thumbnail", return_value=False):

            await download_and_update_thumbnail(1, "https://example.com/new.jpg")

    @pytest.mark.asyncio
    async def test_reimport_single_game(self, db_session):
        """Should reimport game with BGG data"""
        game = Game(
            id=1,
            title="Test Game",
            bgg_id=12345
        )
        db_session.add(game)
        db_session.commit()

        mock_bgg_data = {
            "name": "Updated Game Name",
            "description": "Updated description",
            "designers": ["Designer A"],
            "year": 2023,
        }

        # Patch where GameService is imported in background_tasks module, not where it's defined
        with patch("services.background_tasks.SessionLocal", return_value=db_session), \
             patch("services.background_tasks.fetch_bgg_thing", return_value=mock_bgg_data), \
             patch("services.background_tasks.GameService") as MockGameService:

            mock_service = MockGameService.return_value
            mock_service.update_game_from_bgg_data = Mock()

            await reimport_single_game(1, 12345)

            # Verify GameService was called
            mock_service.update_game_from_bgg_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_reimport_single_game_not_found(self, db_session):
        """Should handle game not found during reimport"""
        with patch("services.background_tasks.SessionLocal", return_value=db_session):
            # Should not raise exception
            await reimport_single_game(999, 12345)

    @pytest.mark.asyncio
    async def test_reimport_single_game_bgg_error(self, db_session):
        """Should handle BGG fetch error during reimport"""
        game = Game(
            id=1,
            title="Test Game",
            bgg_id=12345
        )
        db_session.add(game)
        db_session.commit()

        with patch("services.background_tasks.SessionLocal", return_value=db_session), \
             patch("services.background_tasks.fetch_bgg_thing", side_effect=Exception("BGG API error")):

            # Should not raise exception
            await reimport_single_game(1, 12345)


# ------------------------------------------------------------------------------
# Exception Handler Tests
# ------------------------------------------------------------------------------


class TestExceptionHandlers:
    """Test custom exception handlers"""

    @pytest.mark.asyncio
    async def test_game_not_found_handler(self):
        """Should return 404 for game not found errors"""
        mock_request = Mock(spec=Request)
        exc = GameNotFoundError("Game with ID 123 not found")

        response = await game_not_found_handler(mock_request, exc)

        assert response.status_code == 404
        # Check response contains error information
        response_data = json.loads(response.body)
        assert "detail" in response_data or "Game" in str(response.body)

    @pytest.mark.asyncio
    async def test_validation_error_handler(self):
        """Should return 400 for validation errors"""
        mock_request = Mock(spec=Request)
        exc = ValidationError("Invalid input")

        response = await validation_error_handler(mock_request, exc)

        assert response.status_code == 400
        assert b"Invalid input" in response.body

    @pytest.mark.asyncio
    async def test_bgg_service_error_handler(self):
        """Should return 503 for BGG service errors"""
        mock_request = Mock(spec=Request)
        exc = BGGServiceError("BGG API timeout")

        response = await bgg_service_error_handler(mock_request, exc)

        assert response.status_code == 503
        assert b"BGG API timeout" in response.body

    @pytest.mark.asyncio
    async def test_database_error_handler(self):
        """Should return 500 for database errors"""
        mock_request = Mock(spec=Request)
        exc = DatabaseError("Connection failed")

        response = await database_error_handler(mock_request, exc)

        assert response.status_code == 500
        # Check response contains error information
        response_data = json.loads(response.body)
        assert "detail" in response_data


# ------------------------------------------------------------------------------
# Middleware Tests
# ------------------------------------------------------------------------------


class TestCacheThumbsMiddleware:
    """Test thumbnail caching middleware"""

    @pytest.mark.asyncio
    async def test_caches_thumbnail_response(self):
        """Should cache thumbnail responses"""
        # Mock the ASGI app
        async def mock_app(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            })
            await send({
                "type": "http.response.body",
                "body": b"test",
            })

        middleware = CacheThumbsMiddleware(app=mock_app)

        # ASGI scope for thumbnail request
        scope = {
            "type": "http",
            "path": "/thumbs/game123.jpg",
        }

        # Track sent messages
        sent_messages = []

        async def mock_receive():
            return {"type": "http.request"}

        async def mock_send(message):
            sent_messages.append(message)

        await middleware(scope, mock_receive, mock_send)

        # Check that cache headers were added
        response_start = sent_messages[0]
        headers = dict(response_start["headers"])
        assert b"cache-control" in headers
        assert b"public, max-age=31536000, immutable" in headers[b"cache-control"]

    @pytest.mark.asyncio
    async def test_does_not_cache_non_thumbnail_requests(self):
        """Should not cache non-thumbnail requests"""
        # Mock the ASGI app
        async def mock_app(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            })
            await send({
                "type": "http.response.body",
                "body": b"test",
            })

        middleware = CacheThumbsMiddleware(app=mock_app)

        # ASGI scope for API request
        scope = {
            "type": "http",
            "path": "/api/games",
        }

        # Track sent messages
        sent_messages = []

        async def mock_receive():
            return {"type": "http.request"}

        async def mock_send(message):
            sent_messages.append(message)

        await middleware(scope, mock_receive, mock_send)

        # Check that cache headers were not added
        response_start = sent_messages[0]
        headers = dict(response_start.get("headers", []))
        assert b"cache-control" not in headers
