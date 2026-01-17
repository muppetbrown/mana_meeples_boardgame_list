"""
Comprehensive tests for Cloudinary service (services/cloudinary_service.py)
Target: 0% → 85% coverage
Focus: Initialization, upload, compression, URL generation, error handling
"""
import pytest
import io
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import httpx
from PIL import Image

from services.cloudinary_service import CloudinaryService


class TestInitialization:
    """Test Cloudinary service initialization"""

    @patch('services.cloudinary_service.cloudinary.config')
    def test_init_with_valid_config(self, mock_config):
        """Should initialize with valid Cloudinary configuration"""
        mock_config.return_value = MagicMock(
            cloud_name='test_cloud',
            api_key='test_key',
            api_secret='test_secret'
        )

        service = CloudinaryService()

        assert service.folder == 'boardgame-library'
        assert service.enabled is True
        assert isinstance(service._failed_uploads, set)

    @patch('services.cloudinary_service.cloudinary.config')
    def test_init_disabled_when_missing_config(self, mock_config):
        """Should disable service when config missing"""
        mock_config.return_value = MagicMock(
            cloud_name=None,
            api_key='test_key',
            api_secret='test_secret'
        )

        service = CloudinaryService()

        assert service.enabled is False

    @patch('services.cloudinary_service.cloudinary.config')
    def test_check_cloudinary_enabled_all_fields(self, mock_config):
        """Should check all required config fields"""
        # Missing api_secret
        mock_config.return_value = MagicMock(
            cloud_name='test',
            api_key='test',
            api_secret=None
        )

        service = CloudinaryService()

        assert service.enabled is False


class TestPublicIdGeneration:
    """Test public ID generation from URLs"""

    @patch('services.cloudinary_service.cloudinary.config')
    def test_get_public_id_with_folder(self, mock_config):
        """Should generate public ID with folder"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )
        service = CloudinaryService()

        url = "https://example.com/image.jpg"
        public_id = service._get_public_id(url, include_folder=True)

        assert public_id.startswith('boardgame-library/')
        assert len(public_id) > len('boardgame-library/')  # Has hash

    @patch('services.cloudinary_service.cloudinary.config')
    def test_get_public_id_without_folder(self, mock_config):
        """Should generate public ID without folder"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )
        service = CloudinaryService()

        url = "https://example.com/image.jpg"
        public_id = service._get_public_id(url, include_folder=False)

        assert 'boardgame-library' not in public_id
        assert len(public_id) == 32  # MD5 hash length

    @patch('services.cloudinary_service.cloudinary.config')
    def test_get_public_id_consistent_hashing(self, mock_config):
        """Should generate same hash for same URL"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )
        service = CloudinaryService()

        url = "https://example.com/image.jpg"
        id1 = service._get_public_id(url)
        id2 = service._get_public_id(url)

        assert id1 == id2


class TestImageUpload:
    """Test image upload functionality"""

    @pytest.mark.asyncio
    @patch('services.cloudinary_service.cloudinary.config')
    @patch('services.cloudinary_service.cloudinary.uploader.upload')
    async def test_upload_from_url_success(self, mock_upload, mock_config):
        """Should successfully upload image from URL"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )

        # Create a small valid image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        # Mock Cloudinary upload
        mock_upload.return_value = {
            'public_id': 'test_id',
            'secure_url': 'https://cloudinary.com/test.jpg',
            'format': 'jpg',
            'bytes': 1000
        }

        service = CloudinaryService()
        result = await service.upload_from_url(
            "https://example.com/test.jpg",
            mock_http_client,
            game_id=123
        )

        assert result is not None
        assert result['public_id'] == 'test_id'
        assert mock_upload.called
        # Verify game_id was added to context
        call_kwargs = mock_upload.call_args[1]
        assert 'context' in call_kwargs
        assert 'game_id=123' in call_kwargs['context']

    @pytest.mark.asyncio
    @patch('services.cloudinary_service.cloudinary.config')
    async def test_upload_disabled_service(self, mock_config):
        """Should return None when service disabled"""
        mock_config.return_value = MagicMock(
            cloud_name=None, api_key=None, api_secret=None
        )

        service = CloudinaryService()
        assert service.enabled is False

        result = await service.upload_from_url(
            "https://example.com/test.jpg",
            MagicMock(),
            game_id=123
        )

        assert result is None

    @pytest.mark.asyncio
    @patch('services.cloudinary_service.cloudinary.config')
    async def test_upload_downloads_with_bgg_headers(self, mock_config):
        """Should use proper headers for BGG downloads"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )

        # Create small valid image
        img = Image.new('RGB', (100, 100), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')

        mock_response = Mock()
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        with patch('services.cloudinary_service.cloudinary.uploader.upload'):
            service = CloudinaryService()
            await service.upload_from_url(
                "https://boardgamegeek.com/image.jpg",
                mock_http_client
            )

        # Verify headers were used
        call_args = mock_http_client.get.call_args
        headers = call_args[1]['headers']
        assert 'User-Agent' in headers
        assert 'Referer' in headers
        assert 'boardgamegeek.com' in headers['Referer']

    @pytest.mark.asyncio
    @patch('services.cloudinary_service.cloudinary.config')
    @patch('services.cloudinary_service.cloudinary.uploader.upload')
    async def test_image_compression_webp_strategy(self, mock_upload, mock_config):
        """Should compress large images using WebP"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )

        # Create a large image that needs compression (> 10MB uncompressed)
        # A 3000x3000 RGB image is ~27MB uncompressed
        img = Image.new('RGB', (3000, 3000), color='green')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')

        mock_response = Mock()
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        mock_upload.return_value = {
            'public_id': 'test_id',
            'format': 'webp',  # Should use WebP
            'bytes': 500000
        }

        service = CloudinaryService()
        result = await service.upload_from_url(
            "https://example.com/large.png",
            mock_http_client
        )

        assert result is not None
        # Image should have been compressed
        assert mock_upload.called

    @pytest.mark.asyncio
    @patch('services.cloudinary_service.cloudinary.config')
    async def test_oversized_image_handling(self, mock_config):
        """Should handle extremely large images"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )

        # Create very large image
        img = Image.new('RGB', (5000, 5000), color='yellow')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')

        mock_response = Mock()
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        with patch('services.cloudinary_service.cloudinary.uploader.upload') as mock_upload:
            mock_upload.return_value = {
                'public_id': 'test_id',
                'format': 'webp',
                'bytes': 800000
            }

            service = CloudinaryService()
            result = await service.upload_from_url(
                "https://example.com/huge.png",
                mock_http_client
            )

            assert result is not None

    @pytest.mark.asyncio
    @patch('services.cloudinary_service.cloudinary.config')
    async def test_pillow_processing_failure_fallback(self, mock_config):
        """Should fallback to original bytes if Pillow fails"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )

        # Invalid image data
        mock_response = Mock()
        mock_response.content = b'not an image'
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        with patch('services.cloudinary_service.cloudinary.uploader.upload') as mock_upload:
            mock_upload.return_value = {
                'public_id': 'test_id',
                'format': 'bin',
                'bytes': 13
            }

            service = CloudinaryService()
            result = await service.upload_from_url(
                "https://example.com/corrupt.jpg",
                mock_http_client
            )

            # Should still attempt upload with original bytes
            assert mock_upload.called

    @pytest.mark.asyncio
    @patch('services.cloudinary_service.cloudinary.config')
    async def test_failed_upload_tracking(self, mock_config):
        """Should track failed uploads"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )

        mock_http_client = MagicMock()
        mock_http_client.get = AsyncMock(side_effect=httpx.HTTPError("Network error"))

        service = CloudinaryService()
        url = "https://example.com/fail.jpg"

        result = await service.upload_from_url(url, mock_http_client)

        assert result is None
        assert url in service._failed_uploads

    @pytest.mark.asyncio
    @patch('services.cloudinary_service.cloudinary.config')
    async def test_network_error_handling(self, mock_config):
        """Should handle network errors gracefully"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )

        mock_http_client = MagicMock()
        mock_http_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        service = CloudinaryService()
        result = await service.upload_from_url(
            "https://example.com/timeout.jpg",
            mock_http_client
        )

        assert result is None

    @pytest.mark.asyncio
    @patch('services.cloudinary_service.cloudinary.config')
    @patch('services.cloudinary_service.cloudinary.uploader.upload')
    async def test_cloudinary_api_error_handling(self, mock_upload, mock_config):
        """Should handle Cloudinary API errors"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )

        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')

        mock_response = Mock()
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        # Mock Cloudinary error
        import cloudinary.exceptions
        mock_upload.side_effect = cloudinary.exceptions.Error("Rate limit exceeded")

        service = CloudinaryService()
        url = "https://example.com/ratelimit.jpg"
        result = await service.upload_from_url(url, mock_http_client)

        assert result is None
        assert url in service._failed_uploads


class TestURLGeneration:
    """Test URL generation and transformation"""

    @patch('services.cloudinary_service.cloudinary.config')
    @patch('services.cloudinary_service.CloudinaryImage')
    def test_generate_optimized_url(self, mock_cloudinary_image, mock_config):
        """Should generate optimized URL with transformations"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )

        mock_image = MagicMock()
        mock_image.build_url.return_value = 'https://cloudinary.com/optimized.jpg'
        mock_cloudinary_image.return_value = mock_image

        service = CloudinaryService()
        url = service.generate_optimized_url(
            "https://example.com/test.jpg",
            width=800,
            height=600
        )

        assert url == 'https://cloudinary.com/optimized.jpg'
        assert mock_image.build_url.called

    @patch('services.cloudinary_service.cloudinary.config')
    def test_generate_optimized_url_disabled_service(self, mock_config):
        """Should return original URL when service disabled"""
        mock_config.return_value = MagicMock(
            cloud_name=None, api_key=None, api_secret=None
        )

        service = CloudinaryService()
        original_url = "https://example.com/test.jpg"
        url = service.generate_optimized_url(original_url)

        assert url == original_url

    @patch('services.cloudinary_service.cloudinary.config')
    @patch('services.cloudinary_service.CloudinaryImage')
    def test_get_image_url_with_transformations(self, mock_cloudinary_image, mock_config):
        """Should apply transformations to image URL"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )

        mock_image = MagicMock()
        mock_image.build_url.return_value = 'https://cloudinary.com/transformed.jpg'
        mock_cloudinary_image.return_value = mock_image

        service = CloudinaryService()
        url = service.get_image_url(
            "https://example.com/test.jpg",
            width=400,
            height=300,
            quality="auto:good",
            crop="fill"
        )

        assert url == 'https://cloudinary.com/transformed.jpg'
        # Verify transformations were passed
        call_kwargs = mock_image.build_url.call_args[1]
        assert call_kwargs['width'] == 400
        assert call_kwargs['height'] == 300
        assert call_kwargs['crop'] == 'fill'

    @patch('services.cloudinary_service.cloudinary.config')
    def test_get_image_url_failed_upload_fallback(self, mock_config):
        """Should return original URL for previously failed uploads"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )

        service = CloudinaryService()
        failed_url = "https://example.com/failed.jpg"
        service._failed_uploads.add(failed_url)

        url = service.get_image_url(failed_url)

        assert url == failed_url  # Should return original

    @patch('services.cloudinary_service.cloudinary.config')
    @patch('services.cloudinary_service.CloudinaryImage')
    def test_get_responsive_urls(self, mock_cloudinary_image, mock_config):
        """Should generate multiple responsive URLs"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )

        mock_image = MagicMock()
        mock_image.build_url.return_value = 'https://cloudinary.com/responsive.jpg'
        mock_cloudinary_image.return_value = mock_image

        service = CloudinaryService()
        urls = service.get_responsive_urls("https://example.com/test.jpg")

        assert 'thumbnail' in urls
        assert 'small' in urls
        assert 'medium' in urls
        assert 'large' in urls
        assert 'original' in urls

    @patch('services.cloudinary_service.cloudinary.config')
    def test_responsive_urls_disabled_service(self, mock_config):
        """Should return original URL for all sizes when disabled"""
        mock_config.return_value = MagicMock(
            cloud_name=None, api_key=None, api_secret=None
        )

        service = CloudinaryService()
        original_url = "https://example.com/test.jpg"
        urls = service.get_responsive_urls(original_url)

        assert all(url == original_url for url in urls.values())


class TestImageDeletion:
    """Test image deletion from Cloudinary"""

    @patch('services.cloudinary_service.cloudinary.config')
    @patch('services.cloudinary_service.cloudinary.uploader.destroy')
    def test_delete_image_success(self, mock_destroy, mock_config):
        """Should successfully delete image"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )

        mock_destroy.return_value = {'result': 'ok'}

        service = CloudinaryService()
        result = service.delete_image("https://example.com/delete.jpg")

        assert result is True
        assert mock_destroy.called

    @patch('services.cloudinary_service.cloudinary.config')
    @patch('services.cloudinary_service.cloudinary.uploader.destroy')
    def test_delete_image_failure(self, mock_destroy, mock_config):
        """Should handle deletion failure"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )

        mock_destroy.return_value = {'result': 'not found'}

        service = CloudinaryService()
        result = service.delete_image("https://example.com/notfound.jpg")

        assert result is False

    @patch('services.cloudinary_service.cloudinary.config')
    def test_delete_image_disabled_service(self, mock_config):
        """Should return False when service disabled"""
        mock_config.return_value = MagicMock(
            cloud_name=None, api_key=None, api_secret=None
        )

        service = CloudinaryService()
        result = service.delete_image("https://example.com/test.jpg")

        assert result is False

    @patch('services.cloudinary_service.cloudinary.config')
    @patch('services.cloudinary_service.cloudinary.uploader.destroy')
    def test_delete_image_error_handling(self, mock_destroy, mock_config):
        """Should handle deletion errors"""
        mock_config.return_value = MagicMock(
            cloud_name='test', api_key='test', api_secret='test'
        )

        mock_destroy.side_effect = Exception("API error")

        service = CloudinaryService()
        result = service.delete_image("https://example.com/error.jpg")

        assert result is False
