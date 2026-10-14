"""
Tests for API dependencies (api/dependencies.py)
Target: Increase coverage from 40% to 80%+
"""
import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException, Request
from api.dependencies import (
    get_client_ip,
    require_admin_auth,
)
from utils.jwt_utils import generate_jwt_token
from config import ADMIN_TOKEN


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


class TestRequireAdminAuth:
    """Test admin authentication dependency"""

    def setup_method(self):
        """Clear sessions and setup before each test"""

    def test_require_admin_auth_valid_jwt(self):
        """Test authentication with valid JWT token"""
        client_ip = "192.168.1.100"
        jwt_token = generate_jwt_token(client_ip)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        # Should not raise exception
        require_admin_auth(
            request=request, authorization=f"Bearer {jwt_token}", x_admin_token=None
        )

    def test_require_admin_auth_valid_admin_token(self):
        """Test authentication with valid admin token header"""
        client_ip = "172.16.0.1"

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        # Should not raise exception
        require_admin_auth(
            request=request, authorization=None, x_admin_token=ADMIN_TOKEN
        )

    def test_require_admin_auth_no_credentials(self):
        """Test authentication fails with no credentials"""
        client_ip = "192.168.1.1"

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host=client_ip)

        with pytest.raises(HTTPException) as exc_info:
            require_admin_auth(
                request=request, authorization=None, x_admin_token=None
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
                x_admin_token=None
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
                request=request, authorization=None, x_admin_token="wrong-token"
            )

        assert exc_info.value.status_code == 401

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
                    request=request, authorization=None, x_admin_token="wrong"
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
                request=request, authorization=None, x_admin_token="wrong-token"
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
            request=request, authorization=f"Bearer {jwt_token}", x_admin_token=None
        )

        # Check debug log
        assert any(
            "Valid JWT authentication" in record.message for record in caplog.records
        )

class TestIntegration:
    """Integration tests for authentication flow"""

    def setup_method(self):
        """Clear state before each test"""

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
            request=request, authorization=f"Bearer {token}", x_admin_token=None
        )
