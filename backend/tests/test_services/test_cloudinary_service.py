"""
Comprehensive Tests for Cloudinary Service
Sprint: Test Coverage Improvement

Tests all Cloudinary service functionality including:
- Service initialization and configuration
- URL generation with public IDs
- Image uploads with various scenarios
- Responsive image URL generation
- Image deletion
- Error handling and fallbacks
"""

import hashlib
import io
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import cloudinary
import cloudinary.uploader
import httpx

from services.cloudinary_service import CloudinaryService


class TestCloudinaryServiceInit:
    """Test CloudinaryService initialization"""

    @patch("services.cloudinary_service.cloudinary.config")
    def test_init_with_valid_config(self, mock_config):
        """Should initialize with enabled=True when config is valid"""
        # Mock valid configuration
        mock_config.return_value.cloud_name = "test_cloud"
        mock_config.return_value.api_key = "test_key"
        mock_config.return_value.api_secret = "test_secret"

        service = CloudinaryService()

        assert service.enabled is True
        assert service.folder == "boardgame-library"
        assert isinstance(service._failed_uploads, set)
        assert len(service._failed_uploads) == 0

    @patch("services.cloudinary_service.cloudinary.config")
    def test_init_with_missing_config(self, mock_config):
        """Should initialize with enabled=False when config is incomplete"""
        # Mock incomplete configuration
        mock_config.return_value.cloud_name = None
        mock_config.return_value.api_key = "test_key"
        mock_config.return_value.api_secret = "test_secret"

        service = CloudinaryService()

        assert service.enabled is False

    @patch("services.cloudinary_service.cloudinary.config")
    def test_init_with_no_config(self, mock_config):
        """Should initialize with enabled=False when no config provided"""
        mock_config.return_value.cloud_name = None
        mock_config.return_value.api_key = None
        mock_config.return_value.api_secret = None

        service = CloudinaryService()

        assert service.enabled is False


class TestGetPublicId:
    """Test _get_public_id method"""

    @patch("services.cloudinary_service.cloudinary.config")
    def test_get_public_id_with_folder(self, mock_config):
        """Should return public_id with folder prefix"""
        mock_config.return_value.cloud_name = "test"
        mock_config.return_value.api_key = "key"
        mock_config.return_value.api_secret = "secret"

        service = CloudinaryService()
        url = "https://example.com/image.jpg"
        expected_hash = hashlib.md5(url.encode()).hexdigest()

        public_id = service._get_public_id(url, include_folder=True)

        assert public_id == f"boardgame-library/{expected_hash}"

    @patch("services.cloudinary_service.cloudinary.config")
    def test_get_public_id_without_folder(self, mock_config):
        """Should return public_id without folder prefix"""
        mock_config.return_value.cloud_name = "test"
        mock_config.return_value.api_key = "key"
        mock_config.return_value.api_secret = "secret"

        service = CloudinaryService()
        url = "https://example.com/image.jpg"
        expected_hash = hashlib.md5(url.encode()).hexdigest()

        public_id = service._get_public_id(url, include_folder=False)

        assert public_id == expected_hash

    @patch("services.cloudinary_service.cloudinary.config")
    def test_get_public_id_deterministic(self, mock_config):
        """Should return same public_id for same URL"""
        mock_config.return_value.cloud_name = "test"
        mock_config.return_value.api_key = "key"
        mock_config.return_value.api_secret = "secret"

        service = CloudinaryService()
        url = "https://example.com/image.jpg"

        public_id1 = service._get_public_id(url)
        public_id2 = service._get_public_id(url)

        assert public_id1 == public_id2


class TestUploadFromUrl:
    """Test upload_from_url method"""

    @pytest.mark.asyncio
    @patch("services.cloudinary_service.cloudinary.config")
    async def test_upload_when_disabled(self, mock_config):
        """Should return None when Cloudinary is disabled"""
        mock_config.return_value.cloud_name = None
        mock_config.return_value.api_key = None
        mock_config.return_value.api_secret = None

        service = CloudinaryService()
        mock_client = AsyncMock()

        result = await service.upload_from_url(
            "https://example.com/image.jpg", mock_client
        )

        assert result is None

    @pytest.mark.asyncio
    @patch("services.cloudinary_service.cloudinary.config")
    @patch("services.cloudinary_service.cloudinary.uploader.upload")
    async def test_successful_upload(self, mock_upload, mock_config):
        """Should successfully upload image and return result"""
        # Mock configuration
        mock_config.return_value.cloud_name = "test"
        mock_config.return_value.api_key = "key"
        mock_config.return_value.api_secret = "secret"

        # Mock HTTP client response
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = b"fake_image_bytes"
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response

        # Mock Cloudinary upload response
        mock_upload.return_value = {
            "secure_url": "https://cloudinary.com/image.jpg",
            "format": "jpg",
            "bytes": 100,
        }

        service = CloudinaryService()
        result = await service.upload_from_url(
            "https://example.com/image.jpg", mock_client, game_id=123
        )

        assert result is not None
        assert result["secure_url"] == "https://cloudinary.com/image.jpg"
        assert result["format"] == "jpg"
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.cloudinary_service.cloudinary.config")
    async def test_upload_with_http_error(self, mock_config):
        """Should handle HTTP error when downloading image"""
        mock_config.return_value.cloud_name = "test"
        mock_config.return_value.api_key = "key"
        mock_config.return_value.api_secret = "secret"

        # Mock HTTP client to raise error
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPError("Network error")

        service = CloudinaryService()
        url = "https://example.com/image.jpg"
        result = await service.upload_from_url(url, mock_client)

        assert result is None
        assert url in service._failed_uploads

    @pytest.mark.asyncio
    @patch("services.cloudinary_service.cloudinary.config")
    @patch("services.cloudinary_service.cloudinary.uploader.upload")
    async def test_upload_with_cloudinary_error(self, mock_upload, mock_config):
        """Should handle Cloudinary API error"""
        mock_config.return_value.cloud_name = "test"
        mock_config.return_value.api_key = "key"
        mock_config.return_value.api_secret = "secret"

        # Mock HTTP client
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = b"fake_image_bytes"
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response

        # Mock Cloudinary to raise error
        mock_upload.side_effect = cloudinary.exceptions.Error("Upload failed")

        service = CloudinaryService()
        url = "https://example.com/image.jpg"
        result = await service.upload_from_url(url, mock_client)

        assert result is None
        assert url in service._failed_uploads

    @pytest.mark.asyncio
    @patch("services.cloudinary_service.cloudinary.config")
    async def test_upload_with_large_file(self, mock_config):
        """Should reject files larger than 10MB"""
        mock_config.return_value.cloud_name = "test"
        mock_config.return_value.api_key = "key"
        mock_config.return_value.api_secret = "secret"

        # Mock HTTP client with large file
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        # Create image larger than 10MB
        mock_response.content = b"x" * (11 * 1024 * 1024)  # 11MB
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response

        service = CloudinaryService()
        url = "https://example.com/image.jpg"
        result = await service.upload_from_url(url, mock_client)

        assert result is None
        assert url in service._failed_uploads

    @pytest.mark.asyncio
    @patch("services.cloudinary_service.cloudinary.config")
    @patch("services.cloudinary_service.cloudinary.uploader.upload")
    async def test_upload_with_game_id_metadata(self, mock_upload, mock_config):
        """Should include game_id in context when provided"""
        mock_config.return_value.cloud_name = "test"
        mock_config.return_value.api_key = "key"
        mock_config.return_value.api_secret = "secret"

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = b"fake_image_bytes"
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response

        mock_upload.return_value = {"secure_url": "https://cloudinary.com/image.jpg"}

        service = CloudinaryService()
        await service.upload_from_url(
            "https://example.com/image.jpg", mock_client, game_id=456
        )

        # Verify game_id was passed in context
        call_args = mock_upload.call_args
        assert "context" in call_args[1]
        assert call_args[1]["context"] == "game_id=456"


class TestGetImageUrl:
    """Test get_image_url method"""

    @patch("services.cloudinary_service.cloudinary.config")
    def test_get_image_url_when_disabled(self, mock_config):
        """Should return original URL when Cloudinary is disabled"""
        mock_config.return_value.cloud_name = None
        mock_config.return_value.api_key = None
        mock_config.return_value.api_secret = None

        service = CloudinaryService()
        original_url = "https://example.com/image.jpg"

        result = service.get_image_url(original_url)

        assert result == original_url

    @patch("services.cloudinary_service.cloudinary.config")
    @patch("services.cloudinary_service.CloudinaryImage")
    def test_get_image_url_basic(self, mock_cloudinary_image, mock_config):
        """Should generate basic Cloudinary URL"""
        mock_config.return_value.cloud_name = "test"
        mock_config.return_value.api_key = "key"
        mock_config.return_value.api_secret = "secret"

        # Mock CloudinaryImage.build_url
        mock_image = MagicMock()
        mock_image.build_url.return_value = "https://cloudinary.com/transformed.jpg"
        mock_cloudinary_image.return_value = mock_image

        service = CloudinaryService()
        result = service.get_image_url("https://example.com/image.jpg")

        assert result == "https://cloudinary.com/transformed.jpg"
        mock_image.build_url.assert_called_once()

    @patch("services.cloudinary_service.cloudinary.config")
    @patch("services.cloudinary_service.CloudinaryImage")
    def test_get_image_url_with_dimensions(self, mock_cloudinary_image, mock_config):
        """Should include width and height in transformation"""
        mock_config.return_value.cloud_name = "test"
        mock_config.return_value.api_key = "key"
        mock_config.return_value.api_secret = "secret"

        mock_image = MagicMock()
        mock_image.build_url.return_value = "https://cloudinary.com/transformed.jpg"
        mock_cloudinary_image.return_value = mock_image

        service = CloudinaryService()
        service.get_image_url(
            "https://example.com/image.jpg", width=800, height=600
        )

        # Verify transformations were applied
        call_kwargs = mock_image.build_url.call_args[1]
        assert call_kwargs["width"] == 800
        assert call_kwargs["height"] == 600
        assert "crop" in call_kwargs

    @patch("services.cloudinary_service.cloudinary.config")
    def test_get_image_url_for_failed_upload(self, mock_config):
        """Should return original URL for previously failed uploads"""
        mock_config.return_value.cloud_name = "test"
        mock_config.return_value.api_key = "key"
        mock_config.return_value.api_secret = "secret"

        service = CloudinaryService()
        url = "https://example.com/failed.jpg"
        service._failed_uploads.add(url)

        result = service.get_image_url(url)

        assert result == url

    @patch("services.cloudinary_service.cloudinary.config")
    @patch("services.cloudinary_service.CloudinaryImage")
    def test_get_image_url_with_quality(self, mock_cloudinary_image, mock_config):
        """Should apply quality transformation"""
        mock_config.return_value.cloud_name = "test"
        mock_config.return_value.api_key = "key"
        mock_config.return_value.api_secret = "secret"

        mock_image = MagicMock()
        mock_image.build_url.return_value = "https://cloudinary.com/transformed.jpg"
        mock_cloudinary_image.return_value = mock_image

        service = CloudinaryService()
        service.get_image_url("https://example.com/image.jpg", quality="auto:eco")

        call_kwargs = mock_image.build_url.call_args[1]
        assert call_kwargs["quality"] == "auto:eco"


class TestGetResponsiveUrls:
    """Test get_responsive_urls method"""

    @patch("services.cloudinary_service.cloudinary.config")
    def test_get_responsive_urls_when_disabled(self, mock_config):
        """Should return original URL for all sizes when disabled"""
        mock_config.return_value.cloud_name = None
        mock_config.return_value.api_key = None
        mock_config.return_value.api_secret = None

        service = CloudinaryService()
        url = "https://example.com/image.jpg"

        result = service.get_responsive_urls(url)

        assert result["thumbnail"] == url
        assert result["small"] == url
        assert result["medium"] == url
        assert result["large"] == url
        assert result["original"] == url

    @patch("services.cloudinary_service.cloudinary.config")
    @patch.object(CloudinaryService, "get_image_url")
    def test_get_responsive_urls_when_enabled(self, mock_get_url, mock_config):
        """Should generate URLs for all responsive sizes"""
        mock_config.return_value.cloud_name = "test"
        mock_config.return_value.api_key = "key"
        mock_config.return_value.api_secret = "secret"

        # Mock get_image_url to return different URLs
        def mock_url_generator(url, width=None, height=None):
            if width == 200:
                return "https://cloudinary.com/thumb.jpg"
            elif width == 400:
                return "https://cloudinary.com/small.jpg"
            elif width == 800:
                return "https://cloudinary.com/medium.jpg"
            elif width == 1200:
                return "https://cloudinary.com/large.jpg"
            else:
                return "https://cloudinary.com/original.jpg"

        mock_get_url.side_effect = mock_url_generator

        service = CloudinaryService()
        result = service.get_responsive_urls("https://example.com/image.jpg")

        assert result["thumbnail"] == "https://cloudinary.com/thumb.jpg"
        assert result["small"] == "https://cloudinary.com/small.jpg"
        assert result["medium"] == "https://cloudinary.com/medium.jpg"
        assert result["large"] == "https://cloudinary.com/large.jpg"
        assert result["original"] == "https://cloudinary.com/original.jpg"


class TestDeleteImage:
    """Test delete_image method"""

    @patch("services.cloudinary_service.cloudinary.config")
    def test_delete_when_disabled(self, mock_config):
        """Should return False when Cloudinary is disabled"""
        mock_config.return_value.cloud_name = None
        mock_config.return_value.api_key = None
        mock_config.return_value.api_secret = None

        service = CloudinaryService()
        result = service.delete_image("https://example.com/image.jpg")

        assert result is False

    @patch("services.cloudinary_service.cloudinary.config")
    @patch("services.cloudinary_service.cloudinary.uploader.destroy")
    def test_delete_successful(self, mock_destroy, mock_config):
        """Should successfully delete image and return True"""
        mock_config.return_value.cloud_name = "test"
        mock_config.return_value.api_key = "key"
        mock_config.return_value.api_secret = "secret"

        mock_destroy.return_value = {"result": "ok"}

        service = CloudinaryService()
        result = service.delete_image("https://example.com/image.jpg")

        assert result is True
        mock_destroy.assert_called_once()

    @patch("services.cloudinary_service.cloudinary.config")
    @patch("services.cloudinary_service.cloudinary.uploader.destroy")
    def test_delete_failed(self, mock_destroy, mock_config):
        """Should return False when deletion fails"""
        mock_config.return_value.cloud_name = "test"
        mock_config.return_value.api_key = "key"
        mock_config.return_value.api_secret = "secret"

        mock_destroy.return_value = {"result": "not found"}

        service = CloudinaryService()
        result = service.delete_image("https://example.com/image.jpg")

        assert result is False

    @patch("services.cloudinary_service.cloudinary.config")
    @patch("services.cloudinary_service.cloudinary.uploader.destroy")
    def test_delete_with_exception(self, mock_destroy, mock_config):
        """Should handle exception and return False"""
        mock_config.return_value.cloud_name = "test"
        mock_config.return_value.api_key = "key"
        mock_config.return_value.api_secret = "secret"

        mock_destroy.side_effect = Exception("API error")

        service = CloudinaryService()
        result = service.delete_image("https://example.com/image.jpg")

        assert result is False
