"""
Comprehensive tests for JWT utilities
Tests token generation, verification, and extraction
"""
import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch

from utils.jwt_utils import (
    generate_jwt_token,
    verify_jwt_token,
    extract_token_from_header,
    JWT_ALGORITHM,
)
from config import SESSION_SECRET, JWT_EXPIRATION_DAYS


class TestJWTTokenGeneration:
    """Test JWT token generation"""

    def test_generate_jwt_token_basic(self):
        """Should generate a valid JWT token"""
        client_ip = "192.168.1.1"
        token = generate_jwt_token(client_ip)

        # Token should be a non-empty string
        assert token
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_jwt_token_contains_correct_payload(self):
        """Should generate token with correct payload structure"""
        client_ip = "10.0.0.1"
        token = generate_jwt_token(client_ip)

        # Decode token without verification to inspect payload
        payload = jwt.decode(token, SESSION_SECRET, algorithms=[JWT_ALGORITHM])

        # Verify payload structure
        assert payload["sub"] == "admin"
        assert payload["ip"] == client_ip
        assert "iat" in payload
        assert "exp" in payload

    def test_generate_jwt_token_has_correct_expiration(self):
        """Should set token expiration to configured days"""
        token = generate_jwt_token("127.0.0.1")
        payload = jwt.decode(token, SESSION_SECRET, algorithms=[JWT_ALGORITHM])

        # Calculate expected expiration
        issued_at = datetime.fromtimestamp(payload["iat"])
        expires_at = datetime.fromtimestamp(payload["exp"])
        token_lifetime = expires_at - issued_at

        # Should be approximately JWT_EXPIRATION_DAYS (within 1 second tolerance)
        expected_lifetime = timedelta(days=JWT_EXPIRATION_DAYS)
        assert abs(token_lifetime - expected_lifetime).total_seconds() < 1

    def test_generate_jwt_token_different_ips(self):
        """Should generate different tokens for different IPs"""
        token1 = generate_jwt_token("192.168.1.1")
        token2 = generate_jwt_token("192.168.1.2")

        # Tokens should be different
        assert token1 != token2

        # But both should be valid
        payload1 = verify_jwt_token(token1)
        payload2 = verify_jwt_token(token2)
        assert payload1 is not None
        assert payload2 is not None
        assert payload1["ip"] != payload2["ip"]

    def test_generate_jwt_token_consistent_for_same_ip_at_same_time(self):
        """Should generate same token for same IP at the same time"""
        client_ip = "192.168.1.100"

        # Mock datetime to ensure same timestamp
        fixed_time = datetime(2025, 1, 1, 12, 0, 0)
        with patch('utils.jwt_utils.datetime') as mock_dt:
            mock_dt.utcnow.return_value = fixed_time

            token1 = generate_jwt_token(client_ip)
            token2 = generate_jwt_token(client_ip)

            # Tokens should be identical
            assert token1 == token2


class TestJWTTokenVerification:
    """Test JWT token verification"""

    def test_verify_valid_token(self):
        """Should successfully verify a valid token"""
        client_ip = "192.168.1.1"
        token = generate_jwt_token(client_ip)
        payload = verify_jwt_token(token)

        assert payload is not None
        assert payload["sub"] == "admin"
        assert payload["ip"] == client_ip

    def test_verify_expired_token(self):
        """Should return None for expired token"""
        # Create a token that's already expired
        past_time = datetime.utcnow() - timedelta(days=10)
        expired_payload = {
            "sub": "admin",
            "ip": "192.168.1.1",
            "iat": past_time,
            "exp": past_time + timedelta(seconds=1),  # Expired 10 days ago
        }
        expired_token = jwt.encode(expired_payload, SESSION_SECRET, algorithm=JWT_ALGORITHM)

        # Verification should return None
        result = verify_jwt_token(expired_token)
        assert result is None

    def test_verify_invalid_token_format(self):
        """Should return None for malformed token"""
        invalid_token = "not.a.valid.jwt.token"
        result = verify_jwt_token(invalid_token)
        assert result is None

    def test_verify_token_with_wrong_signature(self):
        """Should return None for token with wrong signature"""
        # Create token with different secret
        wrong_secret_token = jwt.encode(
            {"sub": "admin", "ip": "192.168.1.1", "exp": datetime.utcnow() + timedelta(days=1)},
            "wrong_secret",
            algorithm=JWT_ALGORITHM
        )

        result = verify_jwt_token(wrong_secret_token)
        assert result is None

    def test_verify_empty_token(self):
        """Should return None for empty token"""
        result = verify_jwt_token("")
        assert result is None

    def test_verify_token_with_missing_fields(self):
        """Should handle token with missing required fields"""
        # Token without 'sub' field - still valid JWT but missing app-specific field
        minimal_payload = {
            "exp": datetime.utcnow() + timedelta(days=1),
        }
        minimal_token = jwt.encode(minimal_payload, SESSION_SECRET, algorithm=JWT_ALGORITHM)

        # Should still decode successfully (JWT itself is valid)
        result = verify_jwt_token(minimal_token)
        assert result is not None
        assert "sub" not in result

    def test_verify_token_at_expiration_boundary(self):
        """Should handle token at exact expiration time"""
        # Create token expiring in 1 second
        soon_to_expire = {
            "sub": "admin",
            "ip": "192.168.1.1",
            "exp": datetime.utcnow() + timedelta(seconds=1),
        }
        token = jwt.encode(soon_to_expire, SESSION_SECRET, algorithm=JWT_ALGORITHM)

        # Should be valid immediately
        result = verify_jwt_token(token)
        assert result is not None


class TestTokenExtraction:
    """Test token extraction from Authorization header"""

    def test_extract_valid_bearer_token(self):
        """Should extract token from valid Bearer header"""
        token = "abc123xyz789"
        header = f"Bearer {token}"
        extracted = extract_token_from_header(header)
        assert extracted == token

    def test_extract_case_insensitive_bearer(self):
        """Should handle case-insensitive 'Bearer' keyword"""
        token = "abc123xyz789"

        # Try different cases
        assert extract_token_from_header(f"Bearer {token}") == token
        assert extract_token_from_header(f"bearer {token}") == token
        assert extract_token_from_header(f"BEARER {token}") == token
        assert extract_token_from_header(f"BeArEr {token}") == token

    def test_extract_from_none_header(self):
        """Should return None for None header"""
        result = extract_token_from_header(None)
        assert result is None

    def test_extract_from_empty_header(self):
        """Should return None for empty header"""
        result = extract_token_from_header("")
        assert result is None

    def test_extract_from_malformed_header_no_bearer(self):
        """Should return None for header without 'Bearer' keyword"""
        result = extract_token_from_header("abc123xyz789")
        assert result is None

    def test_extract_from_malformed_header_wrong_keyword(self):
        """Should return None for header with wrong keyword"""
        result = extract_token_from_header("Basic abc123xyz789")
        assert result is None

    def test_extract_from_header_with_extra_spaces(self):
        """Should return None for header with extra parts"""
        # More than 2 parts - invalid format
        result = extract_token_from_header("Bearer token extra_part")
        assert result is None

    def test_extract_bearer_only(self):
        """Should return None for 'Bearer' without token"""
        result = extract_token_from_header("Bearer")
        assert result is None

    def test_extract_real_jwt_token(self):
        """Should extract real JWT token from header"""
        real_token = generate_jwt_token("192.168.1.1")
        header = f"Bearer {real_token}"
        extracted = extract_token_from_header(header)

        assert extracted == real_token

        # Verify the extracted token is valid
        payload = verify_jwt_token(extracted)
        assert payload is not None


class TestJWTIntegration:
    """Integration tests for complete JWT workflow"""

    def test_complete_token_lifecycle(self):
        """Should handle complete token generation, extraction, and verification"""
        client_ip = "192.168.1.50"

        # Generate token
        token = generate_jwt_token(client_ip)
        assert token

        # Create Authorization header
        auth_header = f"Bearer {token}"

        # Extract token from header
        extracted_token = extract_token_from_header(auth_header)
        assert extracted_token == token

        # Verify extracted token
        payload = verify_jwt_token(extracted_token)
        assert payload is not None
        assert payload["sub"] == "admin"
        assert payload["ip"] == client_ip

    def test_invalid_token_workflow(self):
        """Should reject invalid token through complete workflow"""
        # Use an invalid token
        invalid_token = "invalid.jwt.token"
        auth_header = f"Bearer {invalid_token}"

        # Extract token
        extracted = extract_token_from_header(auth_header)
        assert extracted == invalid_token

        # Verification should fail
        payload = verify_jwt_token(extracted)
        assert payload is None

    def test_expired_token_workflow(self):
        """Should reject expired token through complete workflow"""
        # Create expired token
        past_time = datetime.utcnow() - timedelta(days=10)
        expired_payload = {
            "sub": "admin",
            "ip": "192.168.1.1",
            "iat": past_time,
            "exp": past_time + timedelta(seconds=1),
        }
        expired_token = jwt.encode(expired_payload, SESSION_SECRET, algorithm=JWT_ALGORITHM)
        auth_header = f"Bearer {expired_token}"

        # Extract token
        extracted = extract_token_from_header(auth_header)
        assert extracted == expired_token

        # Verification should fail
        payload = verify_jwt_token(extracted)
        assert payload is None

    def test_multiple_concurrent_tokens(self):
        """Should handle multiple valid tokens simultaneously"""
        ips = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
        tokens = [generate_jwt_token(ip) for ip in ips]

        # All tokens should be unique
        assert len(tokens) == len(set(tokens))

        # All tokens should verify correctly
        for token, ip in zip(tokens, ips):
            payload = verify_jwt_token(token)
            assert payload is not None
            assert payload["ip"] == ip
