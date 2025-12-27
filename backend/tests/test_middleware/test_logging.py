"""
Unit tests for middleware/logging.py

Tests request logging middleware including timing, request IDs, and performance monitoring.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from middleware.logging import RequestLoggingMiddleware


class TestRequestLoggingMiddleware:
    """Test request logging middleware"""

    @pytest.mark.asyncio
    @patch('middleware.logging.logger')
    @patch('middleware.logging.performance_monitor')
    async def test_logs_successful_http_request(self, mock_perf_monitor, mock_logger):
        """Test middleware logs successful HTTP requests"""
        app = AsyncMock()
        middleware = RequestLoggingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
        }
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Verify logging
        assert mock_logger.info.call_count == 2  # Started and completed
        assert "Request started" in str(mock_logger.info.call_args_list[0])
        assert "Request completed" in str(mock_logger.info.call_args_list[1])

        # Verify performance monitoring
        mock_perf_monitor.record_request.assert_called_once()

    @pytest.mark.asyncio
    @patch('middleware.logging.logger')
    @patch('middleware.logging.performance_monitor')
    async def test_adds_request_id_to_scope(self, mock_perf_monitor, mock_logger):
        """Test middleware adds request ID to scope"""
        app = AsyncMock()
        middleware = RequestLoggingMiddleware(app)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/data",
        }
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Request ID should be added to scope
        assert "request_id" in scope
        assert isinstance(scope["request_id"], str)
        assert len(scope["request_id"]) == 8  # UUID truncated to 8 chars

    @pytest.mark.asyncio
    @patch('middleware.logging.logger')
    async def test_skips_non_http_requests(self, mock_logger):
        """Test middleware skips non-HTTP requests"""
        app = AsyncMock()
        middleware = RequestLoggingMiddleware(app)

        scope = {
            "type": "websocket",
            "path": "/ws",
        }
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Should not log for websocket
        mock_logger.info.assert_not_called()

        # App should still be called
        app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    @patch('middleware.logging.logger')
    @patch('middleware.logging.performance_monitor')
    async def test_captures_status_code_from_response(self, mock_perf_monitor, mock_logger):
        """Test middleware captures status code from response"""
        async def app_with_status(scope, receive, send):
            await send({"type": "http.response.start", "status": 404})

        middleware = RequestLoggingMiddleware(app_with_status)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/notfound",
        }
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Verify status code was recorded
        call_args = mock_perf_monitor.record_request.call_args
        assert call_args[0][3] == 404  # status_code argument

    @pytest.mark.asyncio
    @patch('middleware.logging.logger')
    @patch('middleware.logging.performance_monitor')
    async def test_handles_exception_during_request(self, mock_perf_monitor, mock_logger):
        """Test middleware handles exceptions during request processing"""
        test_error = RuntimeError("Test error")

        async def failing_app(scope, receive, send):
            raise test_error

        middleware = RequestLoggingMiddleware(failing_app)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/error",
        }
        receive = AsyncMock()
        send = AsyncMock()

        # Should re-raise the exception
        with pytest.raises(RuntimeError, match="Test error"):
            await middleware(scope, receive, send)

        # Should log error
        mock_logger.error.assert_called_once()
        error_msg = str(mock_logger.error.call_args)
        assert "Request failed" in error_msg
        assert "Test error" in error_msg

        # Should record with 500 status
        call_args = mock_perf_monitor.record_request.call_args
        assert call_args[0][3] == 500  # status_code

    @pytest.mark.asyncio
    @patch('middleware.logging.logger')
    @patch('middleware.logging.performance_monitor')
    async def test_records_request_duration(self, mock_perf_monitor, mock_logger):
        """Test middleware records request duration"""
        import asyncio

        async def slow_app(scope, receive, send):
            await asyncio.sleep(0.01)  # 10ms delay

        middleware = RequestLoggingMiddleware(slow_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/slow",
        }
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Verify duration was recorded
        call_args = mock_perf_monitor.record_request.call_args
        duration = call_args[0][2]
        assert duration >= 0.01  # At least 10ms

    @pytest.mark.asyncio
    @patch('middleware.logging.logger')
    @patch('middleware.logging.performance_monitor')
    async def test_logs_with_request_id(self, mock_perf_monitor, mock_logger):
        """Test all logs include request ID"""
        app = AsyncMock()
        middleware = RequestLoggingMiddleware(app)

        scope = {
            "type": "http",
            "method": "PUT",
            "path": "/api/update",
        }
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Check both log calls have request_id in extra
        for call in mock_logger.info.call_args_list:
            assert "extra" in call.kwargs
            assert "request_id" in call.kwargs["extra"]

    @pytest.mark.asyncio
    @patch('middleware.logging.logger')
    @patch('middleware.logging.performance_monitor')
    async def test_handles_missing_path_and_method(self, mock_perf_monitor, mock_logger):
        """Test middleware handles missing path and method gracefully"""
        app = AsyncMock()
        middleware = RequestLoggingMiddleware(app)

        scope = {
            "type": "http",
            # No path or method
        }
        receive = AsyncMock()
        send = AsyncMock()

        # Should not crash
        await middleware(scope, receive, send)

        # Should still log (with empty strings)
        assert mock_logger.info.call_count >= 1

    @pytest.mark.asyncio
    @patch('middleware.logging.logger')
    @patch('middleware.logging.performance_monitor')
    async def test_default_status_code(self, mock_perf_monitor, mock_logger):
        """Test middleware uses default 200 status if not set in response"""
        async def app_no_status(scope, receive, send):
            # Don't send status code
            pass

        middleware = RequestLoggingMiddleware(app_no_status)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
        }
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Should use default 200
        call_args = mock_perf_monitor.record_request.call_args
        assert call_args[0][3] == 200  # status_code


class TestRequestLoggingIntegration:
    """Integration tests for request logging middleware"""

    @pytest.mark.asyncio
    @patch('middleware.logging.logger')
    @patch('middleware.logging.performance_monitor')
    async def test_full_request_lifecycle(self, mock_perf_monitor, mock_logger):
        """Test complete request lifecycle with all components"""
        async def complete_app(scope, receive, send):
            # Simulate complete HTTP response
            await send({"type": "http.response.start", "status": 201})
            await send({"type": "http.response.body", "body": b"Created"})

        middleware = RequestLoggingMiddleware(complete_app)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/create",
        }
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Verify complete lifecycle
        assert mock_logger.info.call_count == 2
        assert mock_perf_monitor.record_request.called
        assert "request_id" in scope

        # Verify correct status code
        call_args = mock_perf_monitor.record_request.call_args
        assert call_args[0][3] == 201

    @pytest.mark.asyncio
    @patch('middleware.logging.logger')
    @patch('middleware.logging.performance_monitor')
    async def test_exception_includes_duration(self, mock_perf_monitor, mock_logger):
        """Test exception logging includes request duration"""
        async def failing_app(scope, receive, send):
            import asyncio
            await asyncio.sleep(0.005)  # 5ms delay
            raise ValueError("Simulated error")

        middleware = RequestLoggingMiddleware(failing_app)

        scope = {
            "type": "http",
            "method": "DELETE",
            "path": "/api/delete",
        }
        receive = AsyncMock()
        send = AsyncMock()

        with pytest.raises(ValueError):
            await middleware(scope, receive, send)

        # Error log should include duration
        error_msg = str(mock_logger.error.call_args)
        assert "s)" in error_msg  # Duration in seconds

        # Performance monitor should have duration
        call_args = mock_perf_monitor.record_request.call_args
        assert call_args[0][2] >= 0.005  # At least 5ms
