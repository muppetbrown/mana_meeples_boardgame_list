# services/cloudinary_service.py
"""
Cloudinary service for image optimization and CDN delivery.
Handles uploading BGG images to Cloudinary with automatic transformations.
"""
import os
import logging
import hashlib
import io
from typing import Optional, Dict
import httpx
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary import CloudinaryImage

logger = logging.getLogger(__name__)

# Configure Cloudinary from environment variables
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "dsobsswqq"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "159742555664292"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "6-fZDSeelRLTGe9J4a-w0GG8Gow"),
    secure=True
)


class CloudinaryService:
    """Service for Cloudinary image operations"""

    def __init__(self):
        """Initialize Cloudinary service"""
        self.folder = "boardgame-library"  # Organize images in folder
        self.enabled = self._check_cloudinary_enabled()

    def _check_cloudinary_enabled(self) -> bool:
        """Check if Cloudinary is properly configured"""
        config = cloudinary.config()
        if not all([config.cloud_name, config.api_key, config.api_secret]):
            logger.warning("Cloudinary not fully configured, service disabled")
            return False
        return True

    def _get_public_id(self, url: str, include_folder: bool = True) -> str:
        """
        Generate a unique public_id for Cloudinary based on URL.
        Uses MD5 hash of URL for consistency.

        Args:
            url: The original image URL
            include_folder: Whether to include folder in public_id

        Returns:
            Public ID string (e.g., "abc123def456" or "boardgame-library/abc123def456")
        """
        url_hash = hashlib.md5(url.encode()).hexdigest()
        if include_folder:
            return f"{self.folder}/{url_hash}"
        return url_hash

    async def upload_from_url(
        self,
        url: str,
        http_client: httpx.AsyncClient,
        game_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Upload an image from URL to Cloudinary.

        Downloads the image first with proper headers (to work around BGG's restrictions),
        then uploads the bytes to Cloudinary.

        Args:
            url: The source image URL (usually from BGG)
            http_client: httpx client for downloading the image
            game_id: Optional game ID for metadata

        Returns:
            Cloudinary response dict with URLs and metadata, or None if failed
        """
        if not self.enabled:
            logger.warning("Cloudinary not enabled, skipping upload")
            return None

        try:
            # Use hash only as public_id, folder is specified separately
            hash_only = self._get_public_id(url, include_folder=False)
            full_public_id = self._get_public_id(url, include_folder=True)

            # Check if image already exists in Cloudinary (using full path)
            try:
                existing = cloudinary.api.resource(full_public_id)
                logger.info(f"Image already exists in Cloudinary: {full_public_id}")
                return existing
            except cloudinary.exceptions.NotFound:
                # Image doesn't exist, proceed with upload
                pass

            # First, download the image from BGG with proper headers
            # BGG requires User-Agent and Referer headers to prevent hotlinking
            logger.info(f"Downloading image from BGG: {url}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://boardgamegeek.com/",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }

            response = await http_client.get(url, headers=headers)
            response.raise_for_status()

            image_bytes = response.content
            logger.info(f"Downloaded {len(image_bytes)} bytes from BGG")

            # Upload with optimizations
            # Use hash as public_id, folder specified separately to avoid double-nesting
            upload_options = {
                "public_id": hash_only,  # Just the hash, no folder prefix
                "folder": self.folder,  # Folder specified separately
                "overwrite": False,  # Don't overwrite existing
                "resource_type": "image",
                "quality": "auto:best",  # Automatic quality optimization
                "tags": ["boardgame"],
            }

            # Add game_id as context if provided
            if game_id:
                upload_options["context"] = f"game_id={game_id}"

            # Upload the image bytes to Cloudinary (not from URL)
            # Create a file-like object from bytes
            image_file = io.BytesIO(image_bytes)
            result = cloudinary.uploader.upload(image_file, **upload_options)

            logger.info(
                f"Uploaded to Cloudinary: {full_public_id} "
                f"(format: {result.get('format')}, size: {result.get('bytes')} bytes)"
            )

            return result

        except httpx.HTTPError as e:
            logger.error(f"Failed to download image from BGG: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to upload to Cloudinary: {e}")
            return None

    def get_image_url(
        self,
        url: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        quality: str = "auto:best",
        format: str = "auto",
        crop: str = "fill",
        gravity: str = "auto"
    ) -> str:
        """
        Get optimized Cloudinary URL for an image.

        Args:
            url: Original image URL
            width: Target width (optional)
            height: Target height (optional)
            quality: Quality setting (default: auto:best)
            format: Output format (default: auto for WebP/AVIF)
            crop: Crop mode (default: fill)
            gravity: Crop gravity (default: auto)

        Returns:
            Cloudinary URL with transformations, or original URL if not uploaded
        """
        if not self.enabled:
            return url

        try:
            public_id = self._get_public_id(url)

            # Build transformation parameters
            transformation = {
                "quality": quality,
                "fetch_format": format,
            }

            if width:
                transformation["width"] = width
            if height:
                transformation["height"] = height
            if width or height:
                transformation["crop"] = crop
                transformation["gravity"] = gravity

            # Generate URL with transformations
            cloudinary_url = CloudinaryImage(public_id).build_url(
                **transformation
            )

            return cloudinary_url

        except Exception as e:
            logger.error(f"Failed to generate Cloudinary URL: {e}")
            return url  # Fallback to original URL

    def get_responsive_urls(self, url: str) -> Dict[str, str]:
        """
        Get multiple responsive image URLs for different screen sizes.

        Args:
            url: Original image URL

        Returns:
            Dict with size keys and Cloudinary URLs
        """
        if not self.enabled:
            return {
                "thumbnail": url,
                "small": url,
                "medium": url,
                "large": url,
                "original": url
            }

        return {
            "thumbnail": self.get_image_url(url, width=200, height=200),
            "small": self.get_image_url(url, width=400, height=400),
            "medium": self.get_image_url(url, width=800, height=800),
            "large": self.get_image_url(url, width=1200, height=1200),
            "original": self.get_image_url(url),  # Auto format, no resize
        }

    def delete_image(self, url: str) -> bool:
        """
        Delete an image from Cloudinary.

        Args:
            url: Original image URL

        Returns:
            True if deleted, False otherwise
        """
        if not self.enabled:
            return False

        try:
            public_id = self._get_public_id(url)
            result = cloudinary.uploader.destroy(public_id)

            if result.get("result") == "ok":
                logger.info(f"Deleted from Cloudinary: {public_id}")
                return True
            else:
                logger.warning(f"Failed to delete from Cloudinary: {result}")
                return False

        except Exception as e:
            logger.error(f"Error deleting from Cloudinary: {e}")
            return False


# Global instance
cloudinary_service = CloudinaryService()
