"""
Comprehensive tests for SSRF (Server-Side Request Forgery) protection.
Tests the validate_url_against_ssrf() function in api/routers/public.py
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


class TestSSRFProtection:
    """Tests for SSRF URL validation"""

    def test_valid_https_url_passes(self):
        """Valid HTTPS URL to external domain should pass"""
        from api.routers.public import validate_url_against_ssrf

        # Mock socket.gethostbyname to return a public IP
        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'):
            result = validate_url_against_ssrf("https://cf.geekdo-images.com/image.jpg")
            assert result is True

    def test_valid_http_url_passes(self):
        """Valid HTTP URL to external domain should pass"""
        from api.routers.public import validate_url_against_ssrf

        with patch('api.routers.public.socket.gethostbyname', return_value='93.184.216.34'):
            result = validate_url_against_ssrf("http://example.com/image.png")
            assert result is True

    # === Invalid Scheme Tests ===

    def test_ftp_scheme_blocked(self):
        """FTP scheme should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        with pytest.raises(HTTPException) as exc_info:
            validate_url_against_ssrf("ftp://example.com/file.txt")
        assert exc_info.value.status_code == 400
        assert "Invalid URL scheme: ftp" in exc_info.value.detail

    def test_file_scheme_blocked(self):
        """File scheme should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        with pytest.raises(HTTPException) as exc_info:
            validate_url_against_ssrf("file:///etc/passwd")
        assert exc_info.value.status_code == 400
        assert "Invalid URL scheme: file" in exc_info.value.detail

    def test_gopher_scheme_blocked(self):
        """Gopher scheme should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        with pytest.raises(HTTPException) as exc_info:
            validate_url_against_ssrf("gopher://example.com/1")
        assert exc_info.value.status_code == 400
        assert "Invalid URL scheme: gopher" in exc_info.value.detail

    def test_data_scheme_blocked(self):
        """Data URI scheme should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        with pytest.raises(HTTPException) as exc_info:
            validate_url_against_ssrf("data:text/html,<script>alert(1)</script>")
        assert exc_info.value.status_code == 400
        assert "Invalid URL scheme: data" in exc_info.value.detail

    def test_javascript_scheme_blocked(self):
        """JavaScript scheme should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        with pytest.raises(HTTPException) as exc_info:
            validate_url_against_ssrf("javascript:alert(1)")
        assert exc_info.value.status_code == 400
        assert "Invalid URL scheme" in exc_info.value.detail

    def test_ldap_scheme_blocked(self):
        """LDAP scheme should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        with pytest.raises(HTTPException) as exc_info:
            validate_url_against_ssrf("ldap://example.com/dc=example,dc=com")
        assert exc_info.value.status_code == 400
        assert "Invalid URL scheme: ldap" in exc_info.value.detail

    def test_empty_scheme_blocked(self):
        """URL without scheme should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        with pytest.raises(HTTPException) as exc_info:
            validate_url_against_ssrf("//example.com/image.jpg")
        assert exc_info.value.status_code == 400

    # === Private IP Range Tests ===

    def test_private_ip_10_range_blocked(self):
        """Private IP 10.x.x.x should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        with patch('api.routers.public.socket.gethostbyname', return_value='10.0.0.1'):
            with pytest.raises(HTTPException) as exc_info:
                validate_url_against_ssrf("https://internal.example.com/image.jpg")
            assert exc_info.value.status_code == 400
            assert "private IP" in exc_info.value.detail

    def test_private_ip_192_168_range_blocked(self):
        """Private IP 192.168.x.x should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        with patch('api.routers.public.socket.gethostbyname', return_value='192.168.1.1'):
            with pytest.raises(HTTPException) as exc_info:
                validate_url_against_ssrf("https://router.local/image.jpg")
            assert exc_info.value.status_code == 400
            assert "private IP" in exc_info.value.detail

    def test_private_ip_172_16_range_blocked(self):
        """Private IP 172.16-31.x.x should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        for ip in ['172.16.0.1', '172.20.0.1', '172.31.255.255']:
            with patch('api.routers.public.socket.gethostbyname', return_value=ip):
                with pytest.raises(HTTPException) as exc_info:
                    validate_url_against_ssrf(f"https://internal-{ip.replace('.', '-')}.example.com/image.jpg")
                assert exc_info.value.status_code == 400
                assert "private IP" in exc_info.value.detail

    def test_private_ip_172_15_not_blocked(self):
        """172.15.x.x is NOT private and should pass"""
        from api.routers.public import validate_url_against_ssrf

        # 172.15 is public, not private
        with patch('api.routers.public.socket.gethostbyname', return_value='172.15.0.1'):
            result = validate_url_against_ssrf("https://example.com/image.jpg")
            assert result is True

    # === Loopback Address Tests ===

    def test_loopback_127_0_0_1_blocked(self):
        """Loopback 127.0.0.1 should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        with patch('api.routers.public.socket.gethostbyname', return_value='127.0.0.1'):
            with pytest.raises(HTTPException) as exc_info:
                validate_url_against_ssrf("https://localhost/image.jpg")
            assert exc_info.value.status_code == 400
            # Note: is_private catches loopback first in Python's ipaddress module
            assert "private IP" in exc_info.value.detail or "loopback" in exc_info.value.detail

    def test_loopback_127_x_x_x_blocked(self):
        """Any 127.x.x.x should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        for ip in ['127.0.0.1', '127.1.1.1', '127.255.255.255']:
            with patch('api.routers.public.socket.gethostbyname', return_value=ip):
                with pytest.raises(HTTPException) as exc_info:
                    validate_url_against_ssrf(f"https://test-{ip.replace('.', '-')}.com/image.jpg")
                assert exc_info.value.status_code == 400
                # Note: is_private catches loopback first in Python's ipaddress module
                assert "private IP" in exc_info.value.detail or "loopback" in exc_info.value.detail

    # === Link-Local Address Tests ===

    def test_link_local_169_254_blocked(self):
        """Link-local 169.254.x.x should be blocked (AWS metadata)"""
        from api.routers.public import validate_url_against_ssrf

        # This is the AWS metadata service IP
        with patch('api.routers.public.socket.gethostbyname', return_value='169.254.169.254'):
            with pytest.raises(HTTPException) as exc_info:
                validate_url_against_ssrf("https://metadata.internal/latest/meta-data/")
            assert exc_info.value.status_code == 400
            # Link-local is blocked (may be caught by is_private or is_link_local)
            assert "link-local" in exc_info.value.detail or "private IP" in exc_info.value.detail

    def test_link_local_range_blocked(self):
        """Various link-local addresses should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        for ip in ['169.254.0.1', '169.254.100.50', '169.254.255.255']:
            with patch('api.routers.public.socket.gethostbyname', return_value=ip):
                with pytest.raises(HTTPException) as exc_info:
                    validate_url_against_ssrf(f"https://link-local-{ip.replace('.', '-')}.com/")
                assert exc_info.value.status_code == 400
                # Link-local is blocked (may be caught by is_private or is_link_local)
                assert "link-local" in exc_info.value.detail or "private IP" in exc_info.value.detail

    # === Reserved IP Range Tests ===

    def test_reserved_0_0_0_0_blocked(self):
        """Reserved 0.0.0.0 should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        with patch('api.routers.public.socket.gethostbyname', return_value='0.0.0.0'):
            with pytest.raises(HTTPException) as exc_info:
                validate_url_against_ssrf("https://zero.example.com/image.jpg")
            assert exc_info.value.status_code == 400
            # 0.0.0.0 is considered "unspecified" which is_reserved=True
            # It may also show as different error depending on Python version

    def test_reserved_255_255_255_255_blocked(self):
        """Reserved 255.255.255.255 (broadcast) should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        with patch('api.routers.public.socket.gethostbyname', return_value='255.255.255.255'):
            with pytest.raises(HTTPException) as exc_info:
                validate_url_against_ssrf("https://broadcast.example.com/image.jpg")
            assert exc_info.value.status_code == 400
            # 255.255.255.255 is reserved/broadcast

    # === Multicast Address Tests ===

    def test_multicast_224_range_blocked(self):
        """Multicast 224.0.0.0/4 should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        for ip in ['224.0.0.1', '239.255.255.255', '230.0.0.1']:
            with patch('api.routers.public.socket.gethostbyname', return_value=ip):
                with pytest.raises(HTTPException) as exc_info:
                    validate_url_against_ssrf(f"https://multicast-{ip.replace('.', '-')}.com/")
                assert exc_info.value.status_code == 400
                assert "multicast" in exc_info.value.detail

    # === Hostname Resolution Tests ===

    def test_dns_resolution_failure_blocked(self):
        """DNS resolution failure should be blocked"""
        from api.routers.public import validate_url_against_ssrf
        import socket

        with patch('api.routers.public.socket.gethostbyname', side_effect=socket.gaierror("Name resolution failed")):
            with pytest.raises(HTTPException) as exc_info:
                validate_url_against_ssrf("https://nonexistent-domain-xyz.com/image.jpg")
            assert exc_info.value.status_code == 400
            assert "Cannot resolve hostname" in exc_info.value.detail

    def test_empty_hostname_blocked(self):
        """URL without hostname should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        with pytest.raises(HTTPException) as exc_info:
            validate_url_against_ssrf("https:///image.jpg")
        assert exc_info.value.status_code == 400
        assert "valid hostname" in exc_info.value.detail

    def test_url_with_only_port_blocked(self):
        """URL with only port (no hostname) should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        with pytest.raises(HTTPException) as exc_info:
            validate_url_against_ssrf("https://:8080/image.jpg")
        assert exc_info.value.status_code == 400

    # === Edge Cases ===

    def test_url_with_credentials_handled(self):
        """URL with username:password should be handled"""
        from api.routers.public import validate_url_against_ssrf

        with patch('api.routers.public.socket.gethostbyname', return_value='93.184.216.34'):
            result = validate_url_against_ssrf("https://user:pass@example.com/image.jpg")
            assert result is True

    def test_url_with_port_handled(self):
        """URL with custom port should be handled"""
        from api.routers.public import validate_url_against_ssrf

        with patch('api.routers.public.socket.gethostbyname', return_value='93.184.216.34'):
            result = validate_url_against_ssrf("https://example.com:8443/image.jpg")
            assert result is True

    def test_url_with_query_params_handled(self):
        """URL with query parameters should be handled"""
        from api.routers.public import validate_url_against_ssrf

        with patch('api.routers.public.socket.gethostbyname', return_value='151.101.1.140'):
            result = validate_url_against_ssrf("https://cf.geekdo-images.com/image.jpg?w=200&h=200")
            assert result is True

    def test_url_with_fragment_handled(self):
        """URL with fragment should be handled"""
        from api.routers.public import validate_url_against_ssrf

        with patch('api.routers.public.socket.gethostbyname', return_value='93.184.216.34'):
            result = validate_url_against_ssrf("https://example.com/page#section")
            assert result is True

    def test_ipv4_literal_in_url_public(self):
        """IPv4 literal (public) in URL should pass"""
        from api.routers.public import validate_url_against_ssrf

        # Direct IP that's public
        with patch('api.routers.public.socket.gethostbyname', return_value='8.8.8.8'):
            result = validate_url_against_ssrf("https://8.8.8.8/image.jpg")
            assert result is True

    def test_ipv4_literal_in_url_private(self):
        """IPv4 literal (private) in URL should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        # Direct private IP in URL
        with patch('api.routers.public.socket.gethostbyname', return_value='10.0.0.1'):
            with pytest.raises(HTTPException) as exc_info:
                validate_url_against_ssrf("https://10.0.0.1/image.jpg")
            assert exc_info.value.status_code == 400
            assert "private IP" in exc_info.value.detail

    def test_case_insensitive_scheme(self):
        """URL scheme should be case-insensitive"""
        from api.routers.public import validate_url_against_ssrf

        with patch('api.routers.public.socket.gethostbyname', return_value='93.184.216.34'):
            result = validate_url_against_ssrf("HTTPS://example.com/image.jpg")
            assert result is True

    def test_very_long_url_handled(self):
        """Very long URL should be handled"""
        from api.routers.public import validate_url_against_ssrf

        long_path = "a" * 2000
        with patch('api.routers.public.socket.gethostbyname', return_value='93.184.216.34'):
            result = validate_url_against_ssrf(f"https://example.com/{long_path}")
            assert result is True

    def test_unicode_hostname_handled(self):
        """Unicode hostname (IDN) should be handled"""
        from api.routers.public import validate_url_against_ssrf
        import socket

        # IDN domains get converted to punycode
        with patch('api.routers.public.socket.gethostbyname', return_value='93.184.216.34'):
            result = validate_url_against_ssrf("https://münchen.example.com/image.jpg")
            assert result is True

    def test_unexpected_exception_handled(self):
        """Unexpected exceptions should be handled gracefully"""
        from api.routers.public import validate_url_against_ssrf

        with patch('api.routers.public.urlparse', side_effect=Exception("Unexpected error")):
            with pytest.raises(HTTPException) as exc_info:
                validate_url_against_ssrf("https://example.com/image.jpg")
            assert exc_info.value.status_code == 400
            assert "URL validation failed" in exc_info.value.detail


class TestSSRFProtectionIntegration:
    """Integration tests for SSRF protection in image proxy endpoint"""

    def test_image_proxy_blocks_private_ip(self, client):
        """Image proxy endpoint should block private IP addresses"""
        with patch('api.routers.public.socket.gethostbyname', return_value='192.168.1.1'):
            response = client.get("/api/public/image-proxy?url=https://internal.example.com/image.jpg")
            assert response.status_code == 400
            assert "private IP" in response.json()["detail"]

    def test_image_proxy_blocks_localhost(self, client):
        """Image proxy endpoint should block localhost"""
        with patch('api.routers.public.socket.gethostbyname', return_value='127.0.0.1'):
            response = client.get("/api/public/image-proxy?url=https://localhost/image.jpg")
            assert response.status_code == 400
            detail = response.json()["detail"]
            assert "loopback" in detail or "private IP" in detail

    def test_image_proxy_blocks_metadata_service(self, client):
        """Image proxy should block AWS/cloud metadata service IPs"""
        with patch('api.routers.public.socket.gethostbyname', return_value='169.254.169.254'):
            response = client.get("/api/public/image-proxy?url=http://169.254.169.254/latest/meta-data/")
            assert response.status_code == 400
            detail = response.json()["detail"]
            assert "link-local" in detail or "private IP" in detail

    def test_image_proxy_blocks_invalid_scheme(self, client):
        """Image proxy endpoint should block non-HTTP schemes"""
        response = client.get("/api/public/image-proxy?url=file:///etc/passwd")
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "Invalid URL scheme" in detail or "Invalid image URL" in detail


class TestSSRFBypassAttempts:
    """Tests for common SSRF bypass attempts"""

    def test_decimal_ip_encoding_blocked(self):
        """Decimal IP encoding (e.g., 2130706433 for 127.0.0.1) should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        # Even if someone tries decimal notation, gethostbyname still resolves it
        with patch('api.routers.public.socket.gethostbyname', return_value='127.0.0.1'):
            with pytest.raises(HTTPException) as exc_info:
                validate_url_against_ssrf("https://2130706433/image.jpg")
            assert exc_info.value.status_code == 400

    def test_hex_ip_encoding_blocked(self):
        """Hex IP encoding (e.g., 0x7f000001 for 127.0.0.1) should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        with patch('api.routers.public.socket.gethostbyname', return_value='127.0.0.1'):
            with pytest.raises(HTTPException) as exc_info:
                validate_url_against_ssrf("https://0x7f000001/image.jpg")
            assert exc_info.value.status_code == 400

    def test_octal_ip_encoding_blocked(self):
        """Octal IP encoding should be blocked"""
        from api.routers.public import validate_url_against_ssrf

        with patch('api.routers.public.socket.gethostbyname', return_value='127.0.0.1'):
            with pytest.raises(HTTPException) as exc_info:
                validate_url_against_ssrf("https://0177.0.0.1/image.jpg")
            assert exc_info.value.status_code == 400

    def test_double_url_encoding_not_bypassed(self):
        """Double URL encoding should not bypass checks"""
        from api.routers.public import validate_url_against_ssrf

        # %31%32%37%2e%30%2e%30%2e%31 = 127.0.0.1 URL encoded
        with patch('api.routers.public.socket.gethostbyname', return_value='127.0.0.1'):
            with pytest.raises(HTTPException) as exc_info:
                validate_url_against_ssrf("https://%31%32%37%2e%30%2e%30%2e%31/image.jpg")
            assert exc_info.value.status_code == 400

    def test_redirect_to_internal_blocked(self):
        """Even if external domain redirects to internal, initial check passes
        (Note: actual redirect handling happens in the image proxy, not validation)"""
        from api.routers.public import validate_url_against_ssrf

        # Initial validation only checks the provided URL
        with patch('api.routers.public.socket.gethostbyname', return_value='93.184.216.34'):
            result = validate_url_against_ssrf("https://example.com/redirect-to-internal")
            assert result is True


class TestPublicIPRanges:
    """Tests ensuring legitimate public IPs are allowed"""

    @pytest.mark.parametrize("ip,description", [
        ("8.8.8.8", "Google DNS"),
        ("1.1.1.1", "Cloudflare DNS"),
        ("151.101.1.140", "BGG Image CDN"),
        ("93.184.216.34", "Example.com"),
        ("198.41.0.4", "Root DNS A"),
        ("172.15.0.1", "Just outside 172.16 private range"),
        ("172.32.0.1", "Just outside 172.31 private range"),
        ("192.167.1.1", "Just outside 192.168 private range"),
        ("9.255.255.255", "Just outside 10.0.0.0 private range"),
        ("11.0.0.1", "Just outside 10.x private range"),
    ])
    def test_public_ips_allowed(self, ip, description):
        """Public IP addresses should be allowed"""
        from api.routers.public import validate_url_against_ssrf

        with patch('api.routers.public.socket.gethostbyname', return_value=ip):
            result = validate_url_against_ssrf("https://example.com/image.jpg")
            assert result is True, f"Public IP {ip} ({description}) should be allowed"
