# tests/test_api/test_security.py
"""
Tests for security enhancements added in Sprint 1.

Tests cover:
1. Input validation on fix-sequence endpoint
2. Rate limiting on image proxy
3. Security headers middleware
4. URL validation on image proxy
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestFixSequenceValidation:
    """Test input validation on fix-sequence endpoint"""

    def test_fix_sequence_valid_table(self):
        """Should accept valid table names"""
        # Note: This will fail without admin auth, but we're testing validation
        response = client.post(
            "/api/admin/fix-sequence",
            json={"table_name": "boardgames"}
        )
        # Should get 401 (auth required), not 400 (validation error)
        assert response.status_code == 401

    def test_fix_sequence_invalid_table(self):
        """Should reject invalid table names"""
        # Try SQL injection attempt
        response = client.post(
            "/api/admin/fix-sequence",
            json={"table_name": "boardgames; DROP TABLE users;--"}
        )
        # Should get 422 (validation error) before reaching auth
        assert response.status_code == 422
        assert "validation" in response.json()["detail"][0]["type"]

    def test_fix_sequence_whitelist_enforcement(self):
        """Should only allow whitelisted tables"""
        response = client.post(
            "/api/admin/fix-sequence",
            json={"table_name": "users"}  # Not in whitelist
        )
        assert response.status_code == 422

    def test_fix_sequence_special_characters(self):
        """Should reject table names with special characters"""
        response = client.post(
            "/api/admin/fix-sequence",
            json={"table_name": "board'games"}
        )
        assert response.status_code == 422


class TestImageProxyRateLimiting:
    """Test rate limiting on image proxy endpoint"""

    def test_image_proxy_rate_limit(self):
        """Should enforce 60 requests/minute rate limit"""
        # Make 61 requests rapidly
        url = "https://cf.geekdo-images.com/test.jpg"

        for i in range(61):
            response = client.get(f"/api/public/image-proxy?url={url}")

            if i < 60:
                # First 60 should succeed or fail for other reasons (not rate limit)
                assert response.status_code != 429
            else:
                # 61st should be rate limited
                assert response.status_code == 429
                assert "rate limit" in response.json()["detail"].lower()


class TestImageProxyURLValidation:
    """Test URL validation on image proxy"""

    def test_image_proxy_trusted_domain_bgg(self):
        """Should accept BoardGameGeek images"""
        response = client.get(
            "/api/public/image-proxy?url=https://cf.geekdo-images.com/test.jpg"
        )
        # May fail to fetch, but shouldn't reject URL
        assert response.status_code != 400

    def test_image_proxy_untrusted_domain(self):
        """Should reject images from untrusted domains"""
        response = client.get(
            "/api/public/image-proxy?url=https://evil.com/malware.jpg"
        )
        assert response.status_code == 400
        assert "only supports BoardGameGeek" in response.json()["detail"]

    def test_image_proxy_localhost_blocked(self):
        """Should block localhost URLs to prevent SSRF"""
        response = client.get(
            "/api/public/image-proxy?url=http://localhost:8000/api/admin/games"
        )
        assert response.status_code == 400


class TestSecurityHeaders:
    """Test security headers middleware"""

    def test_security_headers_present(self):
        """Should add all security headers to responses"""
        response = client.get("/api/health")

        # Check all expected security headers
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "max-age=31536000" in response.headers.get("Strict-Transport-Security", "")
        assert response.headers.get("Content-Security-Policy") is not None
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert response.headers.get("Permissions-Policy") is not None

    def test_csp_header_content(self):
        """Should have proper Content-Security-Policy"""
        response = client.get("/api/health")
        csp = response.headers.get("Content-Security-Policy")

        # Check key CSP directives
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "cf.geekdo-images.com" in csp  # Allow BGG images

    def test_permissions_policy_restrictive(self):
        """Should disable risky browser features"""
        response = client.get("/api/health")
        permissions = response.headers.get("Permissions-Policy")

        # Check that risky features are disabled
        assert "geolocation=()" in permissions
        assert "microphone=()" in permissions
        assert "camera=()" in permissions
        assert "payment=()" in permissions


class TestSecurityIntegration:
    """Integration tests for security features"""

    def test_sql_injection_prevention(self):
        """Should prevent SQL injection attacks"""
        # Try various SQL injection attempts
        injection_attempts = [
            "boardgames'; DROP TABLE users;--",
            "boardgames UNION SELECT * FROM users",
            "boardgames; DELETE FROM boardgames WHERE 1=1;--",
        ]

        for attempt in injection_attempts:
            response = client.post(
                "/api/admin/fix-sequence",
                json={"table_name": attempt}
            )
            # Should reject with validation error, not execute SQL
            assert response.status_code in [422, 401]  # Validation or auth error

    def test_ssrf_prevention(self):
        """Should prevent Server-Side Request Forgery via image proxy"""
        # Try to access internal services
        ssrf_attempts = [
            "http://localhost:8000/api/admin/games",
            "http://127.0.0.1:8000/api/health/db",
            "http://metadata.google.internal/",
            "http://169.254.169.254/latest/meta-data/",
        ]

        for url in ssrf_attempts:
            response = client.get(f"/api/public/image-proxy?url={url}")
            # Should reject with 400
            assert response.status_code == 400

    def test_clickjacking_prevention(self):
        """Should prevent clickjacking via X-Frame-Options"""
        response = client.get("/api/health")

        # Check both headers that prevent framing
        assert response.headers.get("X-Frame-Options") == "DENY"

        csp = response.headers.get("Content-Security-Policy", "")
        assert "frame-ancestors 'none'" in csp


# Run with: pytest backend/tests/test_api/test_security.py -v
