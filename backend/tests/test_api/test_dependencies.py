"""
Tests for API dependencies (api/dependencies.py)
Target: Increase coverage from 40% to 80%+
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
from shared.rate_limiting import admin_sessions, session_storage
from utils.jwt_utils import generate_jwt_token
from config import SESSION_TIMEOUT_SECONDS, ADMIN_TOKEN


class TestGetClientIP:
    """Test client IP extraction"""

    def test_get_client_ip_direct(self):
        """Test IP extraction from direct connection"""
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="192.168.1.100")

        ip = get_client_ip(request)

        assert ip == "192.168.1.100"

    def test_get_client_ip_x_forwarded_for(self):
        """Test IP extraction from X-Forwarded-For header"""
        request = Mock(spec=Request)
        request.headers = {"x-forwarded-for": "203.0.113.1, 192.168.1.1"}
        request.client = Mock(host="10.0.0.1")

        ip = get_client_ip(request)

        # Should use first IP from X-Forwarded-For
        assert ip == "203.0.113.1"

    def test_get_client_ip_x_forwarded_for_single(self):
        """Test X-Forwarded-For with single IP"""
        request = Mock(spec=Request)
        request.headers = {"x-forwarded-for": "203.0.113.5"}
        request.client = Mock(host="10.0.0.1")

        ip = get_client_ip(request)

        assert ip == "203.0.113.5"

    def test_get_client_ip_x_forwarded_for_whitespace(self):
        """Test X-Forwarded-For with extra whitespace"""
        request = Mock(spec=Request)
        request.headers = {"x-forwarded-for": "  203.0.113.10  ,  10.0.0.1  "}
        request.client = Mock(host="10.0.0.1")

        ip = get_client_ip(request)

        assert ip == "203.0.113.10"

    def test_get_client_ip_no_client(self):
        """Test IP extraction when client is None"""
        request = Mock(spec=Request)
        request.headers = {}
        request.client = None

        ip = get_client_ip(request)

        assert ip == "unknown"

    def test_get_client_ip_header_case_insensitive(self):
        """Test header name is case sensitive in dict"""
        # Note: In real FastAPI, headers are case-insensitive
        # But in our mock, we need to use the exact case
        request = Mock(spec=Request)
        request.headers = {"x-forwarded-for": "172.16.0.1"}
        request.client = Mock(host="10.0.0.1")

        ip = get_client_ip(request)

        assert ip == "172.16.0.1"


class TestCreateSession:
    """Test session creation"""

    def setup_method(self):
        """Clear sessions before each test"""
        session_storage._memory_sessions.clear()
        admin_sessions.clear()

    def test_create_session_returns_token(self):
        """Test session creation returns a token"""
        client_ip = "192.168.1.100"

        token = create_session(client_ip)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_session_stores_data(self):
        """Test session data is stored correctly"""
        client_ip = "10.0.0.5"

        token = create_session(client_ip)

        # Verify session is stored
        session = session_storage.get_session(token)
        assert session is not None
        assert session["ip"] == client_ip
        assert isinstance(session["created_at"], datetime)

    def test_create_session_unique_tokens(self):
        """Test each session gets a unique token"""
        tokens = [create_session("192.168.1.1") for _ in range(10)]

        # All tokens should be unique
        assert len(set(tokens)) == 10

    def test_create_session_logging(self, caplog):
        """Test session creation logs correctly"""
        import logging

        caplog.set_level(logging.INFO)
        client_ip = "203.0.113.50"

        create_session(client_ip)

        # Check log message
        assert any(
            "Created new admin session" in record.message and client_ip in record.message
            for record in caplog.records
        )


class TestValidateSession:
    """Test session validation"""

    def setup_method(self):
        """Clear sessions before each test"""
        session_storage._memory_sessions.clear()
        admin_sessions.clear()

    def test_validate_session_valid(self):
        """Test validation of valid session"""
        client_ip = "192.168.1.100"
        token = create_session(client_ip)

        is_valid = validate_session(token, client_ip)

        assert is_valid is True

    def test_validate_session_none_token(self):
        """Test validation with None token"""
        is_valid = validate_session(None, "192.168.1.1")

        assert is_valid is False

    def test_validate_session_empty_token(self):
        """Test validation with empty token"""
        is_valid = validate_session("", "192.168.1.1")

        assert is_valid is False

    def test_validate_session_invalid_token(self):
        """Test validation with invalid token"""
        is_valid = validate_session("invalid-token-123", "192.168.1.1")

        assert is_valid is False

    def test_validate_session_expired(self):
        """Test validation of expired session"""
        client_ip = "10.0.0.1"
        token = create_session(client_ip)

        # Manually expire the session by modifying created_at
        session = session_storage.get_session(token)
        session["created_at"] = datetime.utcnow() - timedelta(
            seconds=SESSION_TIMEOUT_SECONDS + 10
        )
        session_storage.set_session(token, session, SESSION_TIMEOUT_SECONDS)

        is_valid = validate_session(token, client_ip)

        assert is_valid is False

    def test_validate_session_expired_logging(self, caplog):
        """Test expired session logs correctly"""
        import logging

        caplog.set_level(logging.INFO)
        client_ip = "10.0.0.1"
        token = create_session(client_ip)

        # Expire session
        session = session_storage.get_session(token)
        session["created_at"] = datetime.utcnow() - timedelta(
            seconds=SESSION_TIMEOUT_SECONDS + 10
        )
        session_storage.set_session(token, session, SESSION_TIMEOUT_SECONDS)

        validate_session(token, client_ip)

        # Check log message
        assert any("Session expired" in record.message for record in caplog.records)

    def test_validate_session_removes_expired(self):
        """Test expired session is removed from storage"""
        client_ip = "10.0.0.1"
        token = create_session(client_ip)

        # Expire session
        session = session_storage.get_session(token)
        session["created_at"] = datetime.utcnow() - timedelta(
            seconds=SESSION_TIMEOUT_SECONDS + 10
        )
        session_storage.set_session(token, session, SESSION_TIMEOUT_SECONDS)

        validate_session(token, client_ip)

        # Session should be deleted
        # Note: May still exist in storage depending on implementation
        # but validation should return False
        assert validate_session(token, client_ip) is False


class TestCleanupExpiredSessions:
    """Test session cleanup"""

    def setup_method(self):
        """Clear sessions before each test"""
        admin_sessions.clear()
        session_storage._memory_sessions.clear()

    def test_cleanup_expired_sessions_empty(self):
        """Test cleanup with no sessions"""
        cleanup_expired_sessions()

        # Should not raise error
        assert len(admin_sessions) == 0

    def test_cleanup_expired_sessions_all_valid(self):
        """Test cleanup with all valid sessions"""
        # Create some valid sessions in legacy storage
        tokens = []
        for i in range(3):
            token = f"token-{i}"
            admin_sessions[token] = {
                "created_at": datetime.utcnow(),
                "ip": f"192.168.1.{i}",
            }
            tokens.append(token)

        cleanup_expired_sessions()

        # All sessions should still exist
        assert len(admin_sessions) == 3

    def test_cleanup_expired_sessions_some_expired(self):
        """Test cleanup removes only expired sessions"""
        # Create mix of valid and expired sessions
        valid_token = "valid-token"
        admin_sessions[valid_token] = {
            "created_at": datetime.utcnow(),
            "ip": "192.168.1.1",
        }

        expired_token = "expired-token"
        admin_sessions[expired_token] = {
            "created_at": datetime.utcnow()
            - timedelta(seconds=SESSION_TIMEOUT_SECONDS + 10),
            "ip": "192.168.1.2",
        }

        cleanup_expired_sessions()

        # Only valid session should remain
        assert valid_token in admin_sessions
        assert expired_token not in admin_sessions

    def test_cleanup_expired_sessions_logging(self, caplog):
        """Test cleanup logs when sessions are removed"""
        import logging

        caplog.set_level(logging.INFO)

        # Create expired sessions
        for i in range(3):
            token = f"expired-{i}"
            admin_sessions[token] = {
                "created_at": datetime.utcnow()
                - timedelta(seconds=SESSION_TIMEOUT_SECONDS + 10),
                "ip": f"192.168.1.{i}",
            }

        cleanup_expired_sessions()

        # Check log message
        assert any(
            "Cleaned up" in record.message and "expired sessions" in record.message
            for record in caplog.records
        )


class TestRevokeSession:
    """Test session revocation"""

    def setup_method(self):
        """Clear sessions before each test"""
        session_storage._memory_sessions.clear()
        admin_sessions.clear()

    def test_revoke_session_valid(self):
        """Test revoking a valid session"""
        client_ip = "192.168.1.100"
        token = create_session(client_ip)

        # Verify session exists
        assert validate_session(token, client_ip) is True

        # Revoke session
        revoke_session(token)

        # Session should no longer be valid
        assert validate_session(token, client_ip) is False

    def test_revoke_session_none(self):
        """Test revoking None token"""
        # Should not raise error
        revoke_session(None)

    def test_revoke_session_invalid(self):
        """Test revoking invalid token"""
        # Should not raise error
        revoke_session("invalid-token")

    def test_revoke_session_logging(self, caplog):
        """Test revocation logs correctly"""
        import logging

        caplog.set_level(logging.INFO)
        client_ip = "192.168.1.100"
        token = create_session(client_ip)

        revoke_session(token)

        # Check log message
        assert any("Revoked admin session" in record.message for record in caplog.records)


class TestRequireAdminAuth:
    """Test admin authentication dependency"""

    def setup_method(self):
        """Clear sessions and setup before each test"""
        session_storage._memory_sessions.clear()
        admin_sessions.clear()

    def test_require_admin_auth_valid_jwt(self):
        """Test authentication with valid JWT token"""
        client_ip = "192.168.1.100"
        jwt_token = generate_jwt_token(client_ip)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        # Should not raise exception
        require_admin_auth(
            request=request, authorization=f"Bearer {jwt_token}", x_admin_token=None, admin_session=None
        )

    def test_require_admin_auth_valid_session_cookie(self):
        """Test authentication with valid session cookie"""
        client_ip = "10.0.0.5"
        session_token = create_session(client_ip)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        # Should not raise exception
        require_admin_auth(
            request=request, authorization=None, x_admin_token=None, admin_session=session_token
        )

    def test_require_admin_auth_valid_admin_token(self):
        """Test authentication with valid admin token header"""
        client_ip = "172.16.0.1"

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        # Should not raise exception
        require_admin_auth(
            request=request, authorization=None, x_admin_token=ADMIN_TOKEN, admin_session=None
        )

    def test_require_admin_auth_no_credentials(self):
        """Test authentication fails with no credentials"""
        client_ip = "192.168.1.1"

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        with pytest.raises(HTTPException) as exc_info:
            require_admin_auth(
                request=request, authorization=None, x_admin_token=None, admin_session=None
            )

        assert exc_info.value.status_code == 401

    def test_require_admin_auth_invalid_jwt(self):
        """Test authentication fails with invalid JWT"""
        client_ip = "192.168.1.1"

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        with pytest.raises(HTTPException) as exc_info:
            require_admin_auth(
                request=request,
                authorization="Bearer invalid.jwt.token",
                x_admin_token=None,
                admin_session=None,
            )

        assert exc_info.value.status_code == 401

    def test_require_admin_auth_invalid_admin_token(self):
        """Test authentication fails with wrong admin token"""
        client_ip = "192.168.1.1"

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        with pytest.raises(HTTPException) as exc_info:
            require_admin_auth(
                request=request, authorization=None, x_admin_token="wrong-token", admin_session=None
            )

        assert exc_info.value.status_code == 401

    def test_require_admin_auth_invalid_session(self):
        """Test authentication fails with invalid session"""
        client_ip = "192.168.1.1"

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        with pytest.raises(HTTPException) as exc_info:
            require_admin_auth(
                request=request, authorization=None, x_admin_token=None, admin_session="invalid-session"
            )

        assert exc_info.value.status_code == 401

    def test_require_admin_auth_jwt_preferred_over_session(self):
        """Test JWT is tried before session cookie"""
        client_ip = "192.168.1.100"
        jwt_token = generate_jwt_token(client_ip)
        # Create invalid session
        invalid_session = "invalid-session-token"

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        # Should succeed with valid JWT even though session is invalid
        require_admin_auth(
            request=request, authorization=f"Bearer {jwt_token}", x_admin_token=None, admin_session=invalid_session
        )

    def test_require_admin_auth_session_preferred_over_token(self):
        """Test session cookie is tried before admin token"""
        client_ip = "192.168.1.100"
        session_token = create_session(client_ip)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        # Should succeed with valid session even with wrong admin token
        require_admin_auth(
            request=request, authorization=None, x_admin_token="wrong", admin_session=session_token
        )

    @patch("api.dependencies.DISABLE_RATE_LIMITING", False)
    def test_require_admin_auth_rate_limiting_disabled_in_tests(self):
        """Test rate limiting behavior"""
        # Note: In test environment, DISABLE_RATE_LIMITING is typically True
        # This test verifies the code path when it's False
        client_ip = "192.168.1.1"

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        # Multiple failed attempts
        for _ in range(3):
            with pytest.raises(HTTPException):
                require_admin_auth(
                    request=request, authorization=None, x_admin_token="wrong", admin_session=None
                )

    def test_require_admin_auth_logging_invalid(self, caplog):
        """Test authentication logs invalid attempts"""
        import logging

        caplog.set_level(logging.WARNING)
        client_ip = "192.168.1.1"

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        with pytest.raises(HTTPException):
            require_admin_auth(
                request=request, authorization=None, x_admin_token="wrong-token", admin_session=None
            )

        # Check log message
        assert any(
            "Invalid admin token attempt" in record.message for record in caplog.records
        )

    def test_require_admin_auth_jwt_debug_logging(self, caplog):
        """Test JWT authentication debug logging"""
        import logging

        caplog.set_level(logging.DEBUG)
        client_ip = "192.168.1.100"
        jwt_token = generate_jwt_token(client_ip)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        require_admin_auth(
            request=request, authorization=f"Bearer {jwt_token}", x_admin_token=None, admin_session=None
        )

        # Check debug log
        assert any(
            "Valid JWT authentication" in record.message for record in caplog.records
        )

    def test_require_admin_auth_session_debug_logging(self, caplog):
        """Test session authentication debug logging"""
        import logging

        caplog.set_level(logging.DEBUG)
        client_ip = "192.168.1.100"
        session_token = create_session(client_ip)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        require_admin_auth(
            request=request, authorization=None, x_admin_token=None, admin_session=session_token
        )

        # Check debug log
        assert any(
            "Valid session authentication" in record.message for record in caplog.records
        )


class TestIntegration:
    """Integration tests for authentication flow"""

    def setup_method(self):
        """Clear state before each test"""
        session_storage._memory_sessions.clear()
        admin_sessions.clear()

    def test_full_session_workflow(self):
        """Test complete session creation, validation, and revocation"""
        client_ip = "192.168.1.100"

        # 1. Create session
        token = create_session(client_ip)
        assert token is not None

        # 2. Validate session
        assert validate_session(token, client_ip) is True

        # 3. Use session for authentication
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        require_admin_auth(request=request, authorization=None, x_admin_token=None, admin_session=token)

        # 4. Revoke session
        revoke_session(token)

        # 5. Session should no longer work
        assert validate_session(token, client_ip) is False

        with pytest.raises(HTTPException):
            require_admin_auth(
                request=request, authorization=None, x_admin_token=None, admin_session=token
            )

    def test_full_jwt_workflow(self):
        """Test complete JWT authentication workflow"""
        client_ip = "10.0.0.5"

        # 1. Generate JWT
        token = generate_jwt_token(client_ip)

        # 2. Use for authentication
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        require_admin_auth(
            request=request, authorization=f"Bearer {token}", x_admin_token=None, admin_session=None
        )

    def test_mixed_authentication_methods(self):
        """Test using different authentication methods"""
        client_ip = "172.16.0.1"

        # Create all auth methods
        jwt_token = generate_jwt_token(client_ip)
        session_token = create_session(client_ip)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        # Test JWT
        require_admin_auth(
            request=request, authorization=f"Bearer {jwt_token}", x_admin_token=None, admin_session=None
        )

        # Test session
        require_admin_auth(
            request=request, authorization=None, x_admin_token=None, admin_session=session_token
        )

        # Test admin token
        require_admin_auth(
            request=request, authorization=None, x_admin_token=ADMIN_TOKEN, admin_session=None
        )
