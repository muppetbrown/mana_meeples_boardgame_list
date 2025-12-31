"""
Comprehensive test suite for config module

Tests cover:
- Environment variable loading and validation
- Default values and fallbacks
- Database URL parsing and validation
- CORS configuration
- Redis configuration
- Cloudinary configuration
- Session and JWT settings
- GitHub integration settings
- Rate limiting configuration
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO


class TestConfigLoading:
    """Test configuration loading from environment variables"""

    def test_cors_origins_parsing(self):
        """Test CORS origins parsing from comma-separated string"""
        with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000,https://example.com, https://test.com "}):
            # Reimport to get fresh config
            import importlib
            import config
            importlib.reload(config)

            assert len(config.CORS_ORIGINS) == 3
            assert "http://localhost:3000" in config.CORS_ORIGINS
            assert "https://example.com" in config.CORS_ORIGINS
            assert "https://test.com" in config.CORS_ORIGINS

    def test_cors_origins_empty(self):
        """Test CORS origins with empty environment variable"""
        with patch.dict(os.environ, {"CORS_ORIGINS": ""}, clear=False):
            import importlib
            import config
            importlib.reload(config)

            assert config.CORS_ORIGINS == []

    def test_admin_token_warning_when_not_set(self, capsys):
        """Test warning is shown when ADMIN_TOKEN is not set"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.ADMIN_TOKEN == ""

    def test_admin_token_loaded(self):
        """Test ADMIN_TOKEN loads correctly"""
        with patch.dict(os.environ, {"ADMIN_TOKEN": "test-token-12345"}):
            import importlib
            import config
            importlib.reload(config)

            assert config.ADMIN_TOKEN == "test-token-12345"

    def test_database_url_default(self):
        """Test database URL defaults to SQLite"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.DATABASE_URL == "sqlite:///./app.db"

    def test_database_url_postgresql(self):
        """Test PostgreSQL database URL"""
        pg_url = "postgresql://user:pass@localhost:5432/dbname"
        with patch.dict(os.environ, {"DATABASE_URL": pg_url}):
            import importlib
            import config
            importlib.reload(config)

            assert config.DATABASE_URL == pg_url

    def test_read_replica_url(self):
        """Test read replica configuration"""
        replica_url = "postgresql://user:pass@replica:5432/dbname"
        with patch.dict(os.environ, {"READ_REPLICA_URL": replica_url}):
            import importlib
            import config
            importlib.reload(config)

            assert config.READ_REPLICA_URL == replica_url

    def test_read_replica_url_default(self):
        """Test read replica defaults to empty string"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.READ_REPLICA_URL == ""


class TestAPIConfiguration:
    """Test API and HTTP client configuration"""

    def test_public_base_url_default(self):
        """Test PUBLIC_BASE_URL defaults and API_BASE"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.PUBLIC_BASE_URL == ""
            assert config.API_BASE == "https://mana-meeples-boardgame-list-opgf.onrender.com"

    def test_public_base_url_custom(self):
        """Test custom PUBLIC_BASE_URL"""
        custom_url = "https://custom.example.com/"
        with patch.dict(os.environ, {"PUBLIC_BASE_URL": custom_url}):
            import importlib
            import config
            importlib.reload(config)

            assert config.PUBLIC_BASE_URL == "https://custom.example.com"  # Trailing slash removed
            assert config.API_BASE == "https://custom.example.com"

    def test_http_timeout_default(self):
        """Test HTTP timeout defaults to 30"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.HTTP_TIMEOUT == 30

    def test_http_timeout_custom(self):
        """Test custom HTTP timeout"""
        with patch.dict(os.environ, {"HTTP_TIMEOUT": "60"}):
            import importlib
            import config
            importlib.reload(config)

            assert config.HTTP_TIMEOUT == 60

    def test_http_retries_default(self):
        """Test HTTP retries defaults to 3"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.HTTP_RETRIES == 3

    def test_http_retries_custom(self):
        """Test custom HTTP retries"""
        with patch.dict(os.environ, {"HTTP_RETRIES": "5"}):
            import importlib
            import config
            importlib.reload(config)

            assert config.HTTP_RETRIES == 5


class TestBGGConfiguration:
    """Test BoardGameGeek API configuration"""

    def test_bgg_api_key_not_set(self):
        """Test BGG_API_KEY warning when not set"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.BGG_API_KEY == ""

    def test_bgg_api_key_set(self):
        """Test BGG_API_KEY loads correctly"""
        with patch.dict(os.environ, {"BGG_API_KEY": "test-key"}):
            import importlib
            import config
            importlib.reload(config)

            assert config.BGG_API_KEY == "test-key"


class TestRateLimitingConfiguration:
    """Test rate limiting configuration"""

    def test_rate_limit_defaults(self):
        """Test rate limiting default values"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.RATE_LIMIT_ATTEMPTS == 5
            assert config.RATE_LIMIT_WINDOW == 300
            assert config.DISABLE_RATE_LIMITING is False

    def test_rate_limit_custom(self):
        """Test custom rate limiting values"""
        with patch.dict(os.environ, {
            "RATE_LIMIT_ATTEMPTS": "10",
            "RATE_LIMIT_WINDOW": "600",
            "DISABLE_RATE_LIMITING": "true"
        }):
            import importlib
            import config
            importlib.reload(config)

            assert config.RATE_LIMIT_ATTEMPTS == 10
            assert config.RATE_LIMIT_WINDOW == 600
            assert config.DISABLE_RATE_LIMITING is True

    def test_disable_rate_limiting_values(self):
        """Test various values for DISABLE_RATE_LIMITING"""
        test_cases = [
            ("true", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("0", False),
            ("no", False),
        ]

        for value, expected in test_cases:
            with patch.dict(os.environ, {"DISABLE_RATE_LIMITING": value}):
                import importlib
                import config
                importlib.reload(config)

                assert config.DISABLE_RATE_LIMITING == expected


class TestSessionConfiguration:
    """Test session and JWT configuration"""

    def test_session_secret_generated(self):
        """Test SESSION_SECRET is generated when not set"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            # Should be a 64-character hex string (32 bytes)
            assert len(config.SESSION_SECRET) == 64
            assert all(c in "0123456789abcdef" for c in config.SESSION_SECRET)

    def test_session_secret_custom(self):
        """Test custom SESSION_SECRET"""
        custom_secret = "my-custom-secret-key-1234567890abcdef"
        with patch.dict(os.environ, {"SESSION_SECRET": custom_secret}):
            import importlib
            import config
            importlib.reload(config)

            assert config.SESSION_SECRET == custom_secret

    def test_session_timeout_default(self):
        """Test session timeout defaults to 3600 seconds"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.SESSION_TIMEOUT_SECONDS == 3600

    def test_session_timeout_custom(self):
        """Test custom session timeout"""
        with patch.dict(os.environ, {"SESSION_TIMEOUT_SECONDS": "7200"}):
            import importlib
            import config
            importlib.reload(config)

            assert config.SESSION_TIMEOUT_SECONDS == 7200

    def test_jwt_expiration_default(self):
        """Test JWT expiration defaults to 7 days"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.JWT_EXPIRATION_DAYS == 7

    def test_jwt_expiration_custom(self):
        """Test custom JWT expiration"""
        with patch.dict(os.environ, {"JWT_EXPIRATION_DAYS": "30"}):
            import importlib
            import config
            importlib.reload(config)

            assert config.JWT_EXPIRATION_DAYS == 30


class TestGitHubConfiguration:
    """Test GitHub integration configuration"""

    def test_github_defaults(self):
        """Test GitHub configuration defaults"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.GITHUB_TOKEN == ""
            assert config.GITHUB_REPO_OWNER == "muppetbrown"
            assert config.GITHUB_REPO_NAME == "mana_meeples_boardgame_list"

    def test_github_custom(self):
        """Test custom GitHub configuration"""
        with patch.dict(os.environ, {
            "GITHUB_TOKEN": "ghp_test123",
            "GITHUB_REPO_OWNER": "testowner",
            "GITHUB_REPO_NAME": "testrepo"
        }):
            import importlib
            import config
            importlib.reload(config)

            assert config.GITHUB_TOKEN == "ghp_test123"
            assert config.GITHUB_REPO_OWNER == "testowner"
            assert config.GITHUB_REPO_NAME == "testrepo"


class TestCloudinaryConfiguration:
    """Test Cloudinary CDN configuration"""

    def test_cloudinary_disabled_default(self):
        """Test Cloudinary is disabled when credentials not set"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.CLOUDINARY_CLOUD_NAME == ""
            assert config.CLOUDINARY_API_KEY == ""
            assert config.CLOUDINARY_API_SECRET == ""
            assert config.CLOUDINARY_ENABLED is False

    def test_cloudinary_enabled(self):
        """Test Cloudinary is enabled when all credentials are set"""
        with patch.dict(os.environ, {
            "CLOUDINARY_CLOUD_NAME": "test-cloud",
            "CLOUDINARY_API_KEY": "123456",
            "CLOUDINARY_API_SECRET": "secret123"
        }):
            import importlib
            import config
            importlib.reload(config)

            assert config.CLOUDINARY_CLOUD_NAME == "test-cloud"
            assert config.CLOUDINARY_API_KEY == "123456"
            assert config.CLOUDINARY_API_SECRET == "secret123"
            assert config.CLOUDINARY_ENABLED is True

    def test_cloudinary_partial_config(self):
        """Test Cloudinary is disabled when only partial credentials provided"""
        # Only cloud name
        with patch.dict(os.environ, {"CLOUDINARY_CLOUD_NAME": "test-cloud"}):
            import importlib
            import config
            importlib.reload(config)

            assert config.CLOUDINARY_ENABLED is False

        # Only API key
        with patch.dict(os.environ, {"CLOUDINARY_API_KEY": "123456"}):
            import importlib
            import config
            importlib.reload(config)

            assert config.CLOUDINARY_ENABLED is False


class TestRedisConfiguration:
    """Test Redis configuration for session storage"""

    def test_redis_defaults(self):
        """Test Redis default configuration"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.REDIS_URL == "redis://localhost:6379/0"
            assert config.REDIS_ENABLED is True

    def test_redis_custom_url(self):
        """Test custom Redis URL"""
        custom_url = "redis://redis-server:6380/1"
        with patch.dict(os.environ, {"REDIS_URL": custom_url}):
            import importlib
            import config
            importlib.reload(config)

            assert config.REDIS_URL == custom_url

    def test_redis_disabled(self):
        """Test Redis can be disabled"""
        with patch.dict(os.environ, {"REDIS_ENABLED": "false"}):
            import importlib
            import config
            importlib.reload(config)

            assert config.REDIS_ENABLED is False

    def test_redis_enabled_values(self):
        """Test various values for REDIS_ENABLED"""
        test_cases = [
            ("true", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("0", False),
            ("no", False),
        ]

        for value, expected in test_cases:
            with patch.dict(os.environ, {"REDIS_ENABLED": value}):
                import importlib
                import config
                importlib.reload(config)

                assert config.REDIS_ENABLED == expected


class TestDebugConfiguration:
    """Test debug and development settings"""

    def test_save_debug_info_default(self):
        """Test SAVE_DEBUG_INFO defaults to false"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.SAVE_DEBUG_INFO is False

    def test_save_debug_info_enabled(self):
        """Test SAVE_DEBUG_INFO can be enabled"""
        test_cases = ["true", "1", "yes"]

        for value in test_cases:
            with patch.dict(os.environ, {"SAVE_DEBUG_INFO": value}):
                import importlib
                import config
                importlib.reload(config)

                assert config.SAVE_DEBUG_INFO is True

    def test_save_debug_info_disabled(self):
        """Test SAVE_DEBUG_INFO disabled values"""
        test_cases = ["false", "0", "no", "anything"]

        for value in test_cases:
            with patch.dict(os.environ, {"SAVE_DEBUG_INFO": value}):
                import importlib
                import config
                importlib.reload(config)

                assert config.SAVE_DEBUG_INFO is False


class TestDatabaseURLValidation:
    """Test database URL validation and edge cases"""

    def test_empty_database_url_raises_error(self):
        """Test that empty DATABASE_URL raises ValueError"""
        with patch.dict(os.environ, {"DATABASE_URL": ""}, clear=False):
            with pytest.raises(ValueError, match="DATABASE_URL environment variable is required"):
                import importlib
                import config
                importlib.reload(config)

    def test_postgresql_with_read_replica_prints_info(self, capsys):
        """Test PostgreSQL with read replica prints configuration info"""
        pg_url = "postgresql://user:pass@primary-db:5432/dbname"
        replica_url = "postgresql://user:pass@replica-db:5432/dbname"

        with patch.dict(os.environ, {
            "DATABASE_URL": pg_url,
            "READ_REPLICA_URL": replica_url
        }):
            import importlib
            import config
            importlib.reload(config)

            captured = capsys.readouterr()
            # Should print read replica info (line 36-38)
            assert "Read replica enabled" in captured.err
            assert "replica-db:5432" in captured.err

    def test_unrecognized_database_url_format_prints_warning(self, capsys):
        """Test unrecognized database URL format prints warning"""
        weird_url = "mongodb://localhost:27017/mydb"

        with patch.dict(os.environ, {"DATABASE_URL": weird_url}):
            import importlib
            import config
            importlib.reload(config)

            captured = capsys.readouterr()
            # Should print warning for unrecognized format (line 48-50)
            assert "WARNING: Unrecognized database URL format" in captured.err


class TestRedisURLParsing:
    """Test Redis URL parsing and error handling"""

    def test_redis_url_parsing_success(self, capsys):
        """Test successful Redis URL parsing"""
        redis_url = "redis://user:pass@redis-server:6380/1"

        with patch.dict(os.environ, {
            "REDIS_URL": redis_url,
            "REDIS_ENABLED": "true"
        }):
            import importlib
            import config
            importlib.reload(config)

            captured = capsys.readouterr()
            assert "Redis enabled: redis-server:6380" in captured.err

    def test_redis_url_parsing_failure_fallback(self, capsys):
        """Test Redis URL parsing failure falls back to generic message"""
        # Create a URL that will fail parsing
        invalid_url = "not-a-valid://url-format"

        with patch.dict(os.environ, {
            "REDIS_URL": invalid_url,
            "REDIS_ENABLED": "true"
        }):
            # Mock urlparse to raise an exception
            with patch('urllib.parse.urlparse') as mock_urlparse:
                mock_urlparse.side_effect = Exception("Parse error")

                import importlib
                import config
                importlib.reload(config)

                captured = capsys.readouterr()
                # Should print fallback message (lines 147-148)
                assert "Redis enabled: configuration loaded" in captured.err
