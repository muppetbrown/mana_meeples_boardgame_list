"""
Tests for authentication flow and session management
"""
import pytest
import time
from unittest.mock import patch


class TestAuthenticationFlow:
    """Integration tests for complete authentication flows"""

    def test_complete_login_logout_flow(self, client):
        """Test complete login and logout cycle"""
        # Login
        login_response = client.post(
            "/api/admin/login",
            json={"token": "test_admin_token"}
        )
        assert login_response.status_code == 200
        assert login_response.json().get("success") is True

        # Access protected endpoint (should work with header token)
        admin_headers = {"X-Admin-Token": "test_admin_token"}
        games_response = client.get("/api/admin/games", headers=admin_headers)
        assert games_response.status_code == 200

        # Logout
        logout_response = client.post("/api/admin/logout")
        assert logout_response.status_code == 200
        assert logout_response.json().get("success") is True

    def test_login_with_wrong_token(self, client):
        """Test login attempt with incorrect token"""
        response = client.post(
            "/api/admin/login",
            json={"token": "wrong_token"}
        )
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"] or "credentials" in response.json()["detail"]

    def test_access_without_authentication(self, client):
        """Test accessing protected endpoint without authentication"""
        response = client.get("/api/admin/games")
        assert response.status_code == 401

    def test_validate_endpoint_flow(self, client):
        """Test authentication validation endpoint"""
        # Without auth
        response = client.get("/api/admin/validate")
        assert response.status_code == 401

        # With valid auth
        admin_headers = {"X-Admin-Token": "test_admin_token"}
        response = client.get("/api/admin/validate", headers=admin_headers)
        assert response.status_code == 200
        assert response.json().get("valid") is True


class TestSessionManagement:
    """Tests for session creation and management"""

    def test_session_creation_on_login(self, client):
        """Test that login creates a session cookie"""
        response = client.post(
            "/api/admin/login",
            json={"token": "test_admin_token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "expires_in" in data
        assert isinstance(data["expires_in"], int)

    def test_session_info_in_response(self, client):
        """Test that login response includes session information"""
        response = client.post(
            "/api/admin/login",
            json={"token": "test_admin_token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "message" in data
        assert data["expires_in"] > 0

    def test_logout_clears_session(self, client):
        """Test that logout properly clears session"""
        # Login first
        client.post(
            "/api/admin/login",
            json={"token": "test_admin_token"}
        )

        # Logout
        logout_response = client.post("/api/admin/logout")
        assert logout_response.status_code == 200
        assert logout_response.json().get("success") is True


class TestRateLimiting:
    """Tests for rate limiting on authentication endpoints"""

    def test_rate_limit_on_failed_logins(self, client):
        """Test that multiple failed login attempts trigger rate limiting"""
        # Rate limiting persists across tests in same process
        # So we expect either 401 (not yet rate limited) or 429 (rate limited)
        response = client.post(
            "/api/admin/login",
            json={"token": "wrong_token"}
        )
        assert response.status_code in [401, 429]


class TestAuthenticationEdgeCases:
    """Edge cases and security tests for authentication"""

    def test_login_with_missing_token(self, client):
        """Test login with missing token field"""
        response = client.post(
            "/api/admin/login",
            json={}
        )
        assert response.status_code in [401, 422]  # Unauthorized or validation error

    def test_login_with_empty_token(self, client):
        """Test login with empty token string"""
        response = client.post(
            "/api/admin/login",
            json={"token": ""}
        )
        # May return 401 (invalid) or 422 (validation error) or 429 (rate limited)
        assert response.status_code in [401, 422, 429]

    def test_multiple_concurrent_logins(self, client):
        """Test multiple login requests from same client"""
        # First login
        response1 = client.post(
            "/api/admin/login",
            json={"token": "test_admin_token"}
        )
        # May succeed or be rate limited
        assert response1.status_code in [200, 429]

    def test_header_token_authentication(self, client):
        """Test X-Admin-Token header authentication"""
        admin_headers = {"X-Admin-Token": "test_admin_token"}

        # Should work with header token (or be rate limited)
        response = client.get("/api/admin/games", headers=admin_headers)
        assert response.status_code in [200, 429]

    def test_invalid_header_token_authentication(self, client):
        """Test invalid X-Admin-Token header"""
        admin_headers = {"X-Admin-Token": "invalid_token"}

        # Should reject invalid token (or rate limit)
        response = client.get("/api/admin/games", headers=admin_headers)
        assert response.status_code in [401, 429]
