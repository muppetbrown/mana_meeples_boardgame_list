"""
Tests for JWT utilities (utils/jwt_utils.py)
Target: Increase coverage from 53% to 95%+
"""
import pytest
import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from utils.jwt_utils import (
    generate_jwt_token,
    verify_jwt_token,
    extract_token_from_header,
    JWT_ALGORITHM,
)
from config import SESSION_SECRET, JWT_EXPIRATION_DAYS


class TestGenerateJwtToken:
    """Test JWT token generation"""

    def test_generate_jwt_token_basic(self):
        """Test basic JWT token generation"""
        client_ip = "192.168.1.100"
        token = generate_jwt_token(client_ip)

        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

        # Decode to verify structure
        payload = pyjwt.decode(token, SESSION_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["sub"] == "admin"
        assert payload["ip"] == client_ip
        assert "iat" in payload
        assert "exp" in payload

    def test_generate_jwt_token_expiration(self):
        """Test JWT token has correct expiration"""
        client_ip = "10.0.0.1"
        token = generate_jwt_token(client_ip)

        payload = pyjwt.decode(token, SESSION_SECRET, algorithms=[JWT_ALGORITHM])

        # Check expiration is set correctly
        iat = datetime.fromtimestamp(payload["iat"])
        exp = datetime.fromtimestamp(payload["exp"])
        expected_delta = timedelta(days=JWT_EXPIRATION_DAYS)

        # Allow 1 second tolerance for test execution time
        actual_delta = exp - iat
        assert abs((actual_delta - expected_delta).total_seconds()) < 1

    def test_generate_jwt_token_different_ips(self):
        """Test tokens for different IPs are unique"""
        token1 = generate_jwt_token("192.168.1.1")
        token2 = generate_jwt_token("192.168.1.2")

        assert token1 != token2

        payload1 = pyjwt.decode(token1, SESSION_SECRET, algorithms=[JWT_ALGORITHM])
        payload2 = pyjwt.decode(token2, SESSION_SECRET, algorithms=[JWT_ALGORITHM])

        assert payload1["ip"] == "192.168.1.1"
        assert payload2["ip"] == "192.168.1.2"

    def test_generate_jwt_token_logging(self, caplog):
        """Test JWT generation logs correctly"""
        import logging

        caplog.set_level(logging.INFO)
        client_ip = "203.0.113.1"
        generate_jwt_token(client_ip)

        # Check log message
        assert any(
            client_ip in record.message and "Generated JWT token" in record.message
            for record in caplog.records
        )


class TestVerifyJwtToken:
    """Test JWT token verification"""

    def test_verify_jwt_token_valid(self):
        """Test verification of valid JWT token"""
        client_ip = "172.16.0.1"
        token = generate_jwt_token(client_ip)

        payload = verify_jwt_token(token)

        assert payload is not None
        assert payload["sub"] == "admin"
        assert payload["ip"] == client_ip

    def test_verify_jwt_token_expired(self):
        """Test verification of expired JWT token"""
        # Create an expired token
        payload = {
            "sub": "admin",
            "ip": "10.0.0.1",
            "iat": datetime.now(timezone.utc) - timedelta(days=10),
            "exp": datetime.now(timezone.utc) - timedelta(days=1),  # Expired yesterday
        }
        expired_token = pyjwt.encode(payload, SESSION_SECRET, algorithm=JWT_ALGORITHM)

        result = verify_jwt_token(expired_token)

        assert result is None

    def test_verify_jwt_token_expired_logging(self, caplog):
        """Test verification logs expired tokens"""
        import logging

        caplog.set_level(logging.WARNING)

        # Create expired token
        payload = {
            "sub": "admin",
            "ip": "10.0.0.1",
            "iat": datetime.now(timezone.utc) - timedelta(days=10),
            "exp": datetime.now(timezone.utc) - timedelta(days=1),
        }
        expired_token = pyjwt.encode(payload, SESSION_SECRET, algorithm=JWT_ALGORITHM)

        verify_jwt_token(expired_token)

        # Check log message
        assert any("JWT token expired" in record.message for record in caplog.records)

    def test_verify_jwt_token_invalid_signature(self):
        """Test verification of token with wrong signature"""
        # Create token with different secret
        payload = {
            "sub": "admin",
            "ip": "10.0.0.1",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
        }
        invalid_token = pyjwt.encode(payload, "wrong-secret", algorithm=JWT_ALGORITHM)

        result = verify_jwt_token(invalid_token)

        assert result is None

    def test_verify_jwt_token_malformed(self):
        """Test verification of malformed token"""
        result = verify_jwt_token("not.a.valid.jwt.token")

        assert result is None

    def test_verify_jwt_token_invalid_logging(self, caplog):
        """Test verification logs invalid tokens"""
        import logging

        caplog.set_level(logging.WARNING)

        verify_jwt_token("invalid-token")

        # Check log message
        assert any("Invalid JWT token" in record.message for record in caplog.records)

    def test_verify_jwt_token_empty_string(self):
        """Test verification of empty token"""
        result = verify_jwt_token("")

        assert result is None

    def test_verify_jwt_token_tampered(self):
        """Test verification of tampered token"""
        # Generate valid token
        token = generate_jwt_token("10.0.0.1")

        # Tamper with token by changing a character
        tampered = token[:-5] + "XXXXX"

        result = verify_jwt_token(tampered)

        assert result is None


class TestExtractTokenFromHeader:
    """Test token extraction from Authorization header"""

    def test_extract_token_valid_bearer(self):
        """Test extraction from valid Bearer header"""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token"
        auth_header = f"Bearer {token}"

        result = extract_token_from_header(auth_header)

        assert result == token

    def test_extract_token_case_insensitive(self):
        """Test Bearer keyword is case insensitive"""
        token = "test.jwt.token"

        # Test different cases
        for bearer in ["Bearer", "bearer", "BEARER", "BeArEr"]:
            auth_header = f"{bearer} {token}"
            result = extract_token_from_header(auth_header)
            assert result == token

    def test_extract_token_none_header(self):
        """Test extraction from None header"""
        result = extract_token_from_header(None)

        assert result is None

    def test_extract_token_empty_string(self):
        """Test extraction from empty string"""
        result = extract_token_from_header("")

        assert result is None

    def test_extract_token_missing_bearer(self):
        """Test extraction from header without Bearer keyword"""
        result = extract_token_from_header("just-a-token")

        assert result is None

    def test_extract_token_wrong_format(self):
        """Test extraction from malformed header"""
        # Too many parts
        result = extract_token_from_header("Bearer token extra parts")
        assert result is None

        # Wrong keyword
        result = extract_token_from_header("Basic token123")
        assert result is None

    def test_extract_token_logging_invalid(self, caplog):
        """Test extraction logs invalid format"""
        import logging

        caplog.set_level(logging.WARNING)

        extract_token_from_header("InvalidFormat token")

        # Check log message
        assert any(
            "Invalid Authorization header format" in record.message
            for record in caplog.records
        )

    def test_extract_token_with_whitespace(self):
        """Test extraction handles extra whitespace"""
        token = "test.jwt.token"
        auth_header = f"  Bearer   {token}  "

        # Should handle leading/trailing spaces in header
        # but split() will handle internal spaces
        result = extract_token_from_header(auth_header.strip())

        assert result == token

    def test_extract_token_truncated_logging(self, caplog):
        """Test that long invalid headers are truncated in logs"""
        import logging

        caplog.set_level(logging.WARNING)

        long_header = "Invalid " + ("x" * 100)
        extract_token_from_header(long_header)

        # Check that log message exists and is truncated
        assert any(
            "Invalid Authorization header format" in record.message
            and "..." in record.message
            for record in caplog.records
        )


class TestIntegration:
    """Integration tests for JWT workflow"""

    def test_full_jwt_workflow(self):
        """Test complete JWT generation and verification workflow"""
        # 1. Generate token for a client
        client_ip = "192.168.100.50"
        token = generate_jwt_token(client_ip)

        # 2. Create Authorization header
        auth_header = f"Bearer {token}"

        # 3. Extract token from header
        extracted_token = extract_token_from_header(auth_header)
        assert extracted_token == token

        # 4. Verify token
        payload = verify_jwt_token(extracted_token)
        assert payload is not None
        assert payload["sub"] == "admin"
        assert payload["ip"] == client_ip

    def test_jwt_workflow_with_expired_token(self):
        """Test workflow with expired token"""
        # Create expired token
        payload = {
            "sub": "admin",
            "ip": "10.0.0.1",
            "iat": datetime.now(timezone.utc) - timedelta(days=10),
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        }
        expired_token = pyjwt.encode(payload, SESSION_SECRET, algorithm=JWT_ALGORITHM)

        # Try to verify
        result = verify_jwt_token(expired_token)
        assert result is None

    def test_jwt_workflow_multiple_users(self):
        """Test JWT workflow with multiple concurrent users"""
        users = [
            ("192.168.1.10", "user1"),
            ("192.168.1.20", "user2"),
            ("10.0.0.5", "user3"),
        ]

        tokens = {}
        for ip, name in users:
            tokens[name] = generate_jwt_token(ip)

        # Verify all tokens work independently
        for (ip, name) in users:
            token = tokens[name]
            auth_header = f"Bearer {token}"
            extracted = extract_token_from_header(auth_header)
            payload = verify_jwt_token(extracted)

            assert payload is not None
            assert payload["ip"] == ip
            assert payload["sub"] == "admin"
