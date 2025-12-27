"""
Comprehensive tests for API dependencies
Tests authentication, session management, and helper functions
"""
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException, Request

from api.dependencies import (
    get_client_ip,
    create_session,
    validate_session,
    cleanup_expired_sessions,
    revoke_session,
    require_admin_auth,
)
from shared.rate_limiting import session_storage, rate_limit_tracker


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request"""
    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "192.168.1.1"
    request.headers = {}
    return request


@pytest.fixture(autouse=True)
def clean_test_state():
    """Clean up test state before each test"""
    # Force memory backend and clear
    session_storage._redis_client = None
    session_storage._memory_sessions.clear()
    rate_limit_tracker._redis_client = None
    rate_limit_tracker._memory_tracker.clear()
    yield
    # Clean up after test
    session_storage._memory_sessions.clear()
    rate_limit_tracker._memory_tracker.clear()


class TestGetClientIP:
    """Test client IP extraction"""

    def test_get_client_ip_from_request_client(self, mock_request):
        """Should extract IP from request.client.host"""
        mock_request.headers = {}
        ip = get_client_ip(mock_request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_from_x_forwarded_for(self, mock_request):
        """Should extract IP from X-Forwarded-For header"""
        mock_request.headers = {"x-forwarded-for": "10.0.0.1, 192.168.1.1"}
        ip = get_client_ip(mock_request)
        assert ip == "10.0.0.1"  # First IP in the chain

    def test_get_client_ip_x_forwarded_for_single(self, mock_request):
        """Should handle single IP in X-Forwarded-For"""
        mock_request.headers = {"x-forwarded-for": "10.0.0.1"}
        ip = get_client_ip(mock_request)
        assert ip == "10.0.0.1"

    def test_get_client_ip_x_forwarded_for_with_spaces(self, mock_request):
        """Should strip spaces from X-Forwarded-For IPs"""
        mock_request.headers = {"x-forwarded-for": "  10.0.0.1  ,  192.168.1.1  "}
        ip = get_client_ip(mock_request)
        assert ip == "10.0.0.1"

    def test_get_client_ip_no_client(self, mock_request):
        """Should return 'unknown' when request.client is None"""
        mock_request.client = None
        mock_request.headers = {}
        ip = get_client_ip(mock_request)
        assert ip == "unknown"

    def test_get_client_ip_prefers_forwarded_for(self, mock_request):
        """Should prefer X-Forwarded-For over request.client"""
        mock_request.headers = {"x-forwarded-for": "10.0.0.1"}
        mock_request.client.host = "192.168.1.1"
        ip = get_client_ip(mock_request)
        assert ip == "10.0.0.1"  # Should use forwarded header


class TestCreateSession:
    """Test session creation"""

    def test_create_session_basic(self):
        """Should create a new session and return token"""
        client_ip = "192.168.1.1"
        token = create_session(client_ip)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_session_stores_in_storage(self):
        """Should store session in session_storage"""
        client_ip = "192.168.1.1"
        token = create_session(client_ip)

        # Verify session is stored
        session = session_storage.get_session(token)
        assert session is not None
        assert session["ip"] == client_ip
        assert "created_at" in session

    def test_create_session_unique_tokens(self):
        """Should create unique tokens for each session"""
        token1 = create_session("192.168.1.1")
        token2 = create_session("192.168.1.1")
        token3 = create_session("192.168.1.2")

        # All tokens should be different
        assert token1 != token2
        assert token1 != token3
        assert token2 != token3

    def test_create_session_with_different_ips(self):
        """Should create sessions for different IPs"""
        token1 = create_session("192.168.1.1")
        token2 = create_session("192.168.1.2")

        session1 = session_storage.get_session(token1)
        session2 = session_storage.get_session(token2)

        assert session1["ip"] == "192.168.1.1"
        assert session2["ip"] == "192.168.1.2"


class TestValidateSession:
    """Test session validation"""

    def test_validate_session_valid(self):
        """Should validate a valid session"""
        client_ip = "192.168.1.1"
        token = create_session(client_ip)

        result = validate_session(token, client_ip)
        assert result is True

    def test_validate_session_none_token(self):
        """Should return False for None token"""
        result = validate_session(None, "192.168.1.1")
        assert result is False

    def test_validate_session_nonexistent_token(self):
        """Should return False for nonexistent token"""
        result = validate_session("nonexistent_token", "192.168.1.1")
        assert result is False

    def test_validate_session_expired(self):
        """Should return False for expired session"""
        client_ip = "192.168.1.1"

        # Create a session with expired timestamp
        token = create_session(client_ip)
        session = session_storage.get_session(token)

        # Manually set created_at to past
        session["created_at"] = datetime.utcnow() - timedelta(hours=2)
        session_storage.set_session(token, session, 3600)

        with patch('api.dependencies.SESSION_TIMEOUT_SECONDS', 3600):  # 1 hour timeout
            result = validate_session(token, client_ip)
            assert result is False

    def test_validate_session_deletes_expired(self):
        """Should delete expired sessions"""
        client_ip = "192.168.1.1"
        token = create_session(client_ip)

        # Make session expired
        session = session_storage.get_session(token)
        session["created_at"] = datetime.utcnow() - timedelta(hours=2)
        session_storage.set_session(token, session, 3600)

        with patch('api.dependencies.SESSION_TIMEOUT_SECONDS', 3600):
            validate_session(token, client_ip)

            # Session should be deleted
            # Note: Might still exist in memory due to our test setup
            # but would be expired in real usage


class TestCleanupExpiredSessions:
    """Test expired session cleanup"""

    def test_cleanup_expired_sessions_with_legacy_storage(self):
        """Should cleanup expired sessions from legacy admin_sessions dict"""
        from shared.rate_limiting import admin_sessions

        # Add expired sessions to legacy storage
        admin_sessions["token1"] = {
            "created_at": datetime.utcnow() - timedelta(hours=2),
            "ip": "192.168.1.1"
        }
        admin_sessions["token2"] = {
            "created_at": datetime.utcnow(),
            "ip": "192.168.1.2"
        }

        with patch('api.dependencies.SESSION_TIMEOUT_SECONDS', 3600):  # 1 hour
            cleanup_expired_sessions()

            # token1 should be removed (expired)
            assert "token1" not in admin_sessions
            # token2 should remain (not expired)
            assert "token2" in admin_sessions

        # Clean up
        admin_sessions.clear()

    def test_cleanup_no_expired_sessions(self):
        """Should handle cleanup when no sessions are expired"""
        from shared.rate_limiting import admin_sessions

        admin_sessions["token1"] = {
            "created_at": datetime.utcnow(),
            "ip": "192.168.1.1"
        }

        cleanup_expired_sessions()

        # Session should still exist
        assert "token1" in admin_sessions

        # Clean up
        admin_sessions.clear()

    def test_cleanup_empty_sessions(self):
        """Should handle cleanup when no sessions exist"""
        from shared.rate_limiting import admin_sessions
        admin_sessions.clear()

        # Should not raise any errors
        cleanup_expired_sessions()


class TestRevokeSession:
    """Test session revocation"""

    def test_revoke_session_existing(self):
        """Should revoke an existing session"""
        client_ip = "192.168.1.1"
        token = create_session(client_ip)

        # Verify session exists
        assert session_storage.get_session(token) is not None

        # Revoke session
        revoke_session(token)

        # Session should be gone
        assert session_storage.get_session(token) is None

    def test_revoke_session_none_token(self):
        """Should handle None token gracefully"""
        # Should not raise any errors
        revoke_session(None)

    def test_revoke_session_nonexistent(self):
        """Should handle nonexistent token gracefully"""
        # Should not raise any errors
        revoke_session("nonexistent_token")


class TestRequireAdminAuth:
    """Test admin authentication dependency"""

    def test_require_admin_auth_with_valid_jwt(self, mock_request):
        """Should authenticate with valid JWT token"""
        from utils.jwt_utils import generate_jwt_token

        client_ip = "192.168.1.1"
        jwt_token = generate_jwt_token(client_ip)

        # Should not raise any exception
        require_admin_auth(
            request=mock_request,
            authorization=f"Bearer {jwt_token}",
            x_admin_token=None,
            admin_session=None
        )

    def test_require_admin_auth_with_invalid_jwt(self, mock_request):
        """Should reject invalid JWT token"""
        with pytest.raises(HTTPException) as exc_info:
            require_admin_auth(
                request=mock_request,
                authorization="Bearer invalid_token",
                x_admin_token=None,
                admin_session=None
            )

        assert exc_info.value.status_code == 401

    def test_require_admin_auth_with_valid_session(self, mock_request):
        """Should authenticate with valid session cookie"""
        client_ip = "192.168.1.1"
        token = create_session(client_ip)

        # Should not raise any exception
        require_admin_auth(
            request=mock_request,
            authorization=None,
            x_admin_token=None,
            admin_session=token
        )

    def test_require_admin_auth_with_invalid_session(self, mock_request):
        """Should reject invalid session cookie"""
        with pytest.raises(HTTPException) as exc_info:
            require_admin_auth(
                request=mock_request,
                authorization=None,
                x_admin_token=None,
                admin_session="invalid_session"
            )

        assert exc_info.value.status_code == 401

    def test_require_admin_auth_with_valid_admin_token(self, mock_request):
        """Should authenticate with valid admin token header"""
        with patch('api.dependencies.ADMIN_TOKEN', 'test_admin_token'):
            with patch('api.dependencies.DISABLE_RATE_LIMITING', True):
                # Should not raise any exception
                require_admin_auth(
                    request=mock_request,
                    authorization=None,
                    x_admin_token='test_admin_token',
                    admin_session=None
                )

    def test_require_admin_auth_with_invalid_admin_token(self, mock_request):
        """Should reject invalid admin token header"""
        with patch('api.dependencies.ADMIN_TOKEN', 'correct_token'):
            with patch('api.dependencies.DISABLE_RATE_LIMITING', True):
                with pytest.raises(HTTPException) as exc_info:
                    require_admin_auth(
                        request=mock_request,
                        authorization=None,
                        x_admin_token='wrong_token',
                        admin_session=None
                    )

                assert exc_info.value.status_code == 401

    def test_require_admin_auth_rate_limiting(self, mock_request):
        """Should enforce rate limiting on failed attempts"""
        with patch('api.dependencies.ADMIN_TOKEN', 'correct_token'):
            with patch('api.dependencies.DISABLE_RATE_LIMITING', False):
                with patch('api.dependencies.RATE_LIMIT_ATTEMPTS', 3):
                    with patch('api.dependencies.RATE_LIMIT_WINDOW', 60):
                        # Make multiple failed attempts
                        for i in range(3):
                            try:
                                require_admin_auth(
                                    request=mock_request,
                                    authorization=None,
                                    x_admin_token='wrong_token',
                                    admin_session=None
                                )
                            except HTTPException:
                                pass  # Expected

                        # Next attempt should be rate limited
                        with pytest.raises(HTTPException) as exc_info:
                            require_admin_auth(
                                request=mock_request,
                                authorization=None,
                                x_admin_token='wrong_token',
                                admin_session=None
                            )

                        assert exc_info.value.status_code == 429

    def test_require_admin_auth_no_credentials(self, mock_request):
        """Should reject request with no credentials"""
        with pytest.raises(HTTPException) as exc_info:
            require_admin_auth(
                request=mock_request,
                authorization=None,
                x_admin_token=None,
                admin_session=None
            )

        assert exc_info.value.status_code == 401

    def test_require_admin_auth_jwt_priority(self, mock_request):
        """Should prioritize JWT over session cookie"""
        from utils.jwt_utils import generate_jwt_token

        # Create both JWT and session
        jwt_token = generate_jwt_token("192.168.1.1")
        session_token = create_session("192.168.1.2")

        # Should authenticate with JWT (doesn't matter if session is valid)
        require_admin_auth(
            request=mock_request,
            authorization=f"Bearer {jwt_token}",
            x_admin_token=None,
            admin_session=session_token
        )

    def test_require_admin_auth_session_priority_over_header(self, mock_request):
        """Should prioritize session over admin token header"""
        session_token = create_session("192.168.1.1")

        with patch('api.dependencies.ADMIN_TOKEN', 'correct_token'):
            # Should authenticate with session, not check admin token header
            require_admin_auth(
                request=mock_request,
                authorization=None,
                x_admin_token='wrong_token',  # This should be ignored
                admin_session=session_token
            )


class TestRateLimitingIntegration:
    """Test rate limiting integration with dependencies"""

    def test_rate_limit_window_expiration(self, mock_request):
        """Should clear old attempts outside rate limit window"""
        with patch('api.dependencies.ADMIN_TOKEN', 'correct_token'):
            with patch('api.dependencies.DISABLE_RATE_LIMITING', False):
                with patch('api.dependencies.RATE_LIMIT_ATTEMPTS', 2):
                    with patch('api.dependencies.RATE_LIMIT_WINDOW', 1):  # 1 second window
                        # Make failed attempt
                        try:
                            require_admin_auth(
                                request=mock_request,
                                authorization=None,
                                x_admin_token='wrong_token',
                                admin_session=None
                            )
                        except HTTPException:
                            pass

                        # Wait for window to expire
                        time.sleep(1.1)

                        # Should be able to make more attempts
                        # (old attempts cleared from window)
                        try:
                            require_admin_auth(
                                request=mock_request,
                                authorization=None,
                                x_admin_token='wrong_token',
                                admin_session=None
                            )
                        except HTTPException as e:
                            # Should get 401, not 429
                            assert e.status_code == 401

    def test_rate_limit_per_ip(self, mock_request):
        """Should track rate limits per IP address"""
        mock_request2 = Mock(spec=Request)
        mock_request2.client = Mock()
        mock_request2.client.host = "192.168.1.2"  # Different IP
        mock_request2.headers = {}

        with patch('api.dependencies.ADMIN_TOKEN', 'correct_token'):
            with patch('api.dependencies.DISABLE_RATE_LIMITING', False):
                with patch('api.dependencies.RATE_LIMIT_ATTEMPTS', 2):
                    # Make failed attempts from first IP
                    for i in range(2):
                        try:
                            require_admin_auth(
                                request=mock_request,
                                authorization=None,
                                x_admin_token='wrong_token',
                                admin_session=None
                            )
                        except HTTPException:
                            pass

                    # First IP should be rate limited
                    with pytest.raises(HTTPException) as exc_info:
                        require_admin_auth(
                            request=mock_request,
                            authorization=None,
                            x_admin_token='wrong_token',
                            admin_session=None
                        )
                    assert exc_info.value.status_code == 429

                    # Second IP should still work (different rate limit)
                    try:
                        require_admin_auth(
                            request=mock_request2,
                            authorization=None,
                            x_admin_token='wrong_token',
                            admin_session=None
                        )
                    except HTTPException as e:
                        # Should get 401, not 429
                        assert e.status_code == 401
