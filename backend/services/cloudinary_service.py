# services/cloudinary_service.py
"""
Cloudinary service for image optimization and CDN delivery.
Handles uploading BGG images to Cloudinary with automatic transformations.
"""
import os
import logging
import hashlib
import io
from typing import Optional, Dict, Set
import httpx
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary import CloudinaryImage
from PIL import Image

logger = logging.getLogger(__name__)

# Configure Cloudinary from environment variables
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


class CloudinaryService:
    """Service for Cloudinary image operations"""

    def __init__(self):
        """Initialize Cloudinary service"""
        self.folder = "boardgame-library"  # Organize images in folder
        self.enabled = self._check_cloudinary_enabled()
        # Track URLs that failed to upload (in-memory cache)
        # This prevents repeated attempts to use broken Cloudinary URLs
        self._failed_uploads: Set[str] = set()

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

            # PERFORMANCE FIX: Don't check if image exists - let Cloudinary handle it
            # The overwrite=False option will skip upload if it exists
            # This eliminates a 4-6 second API call per request

            # First, download the image from BGG with proper headers
            # BGG requires User-Agent and Referer headers to prevent hotlinking
            logger.debug(f"Preparing to upload image from BGG: {url}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://boardgamegeek.com/",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }

            response = await http_client.get(url, headers=headers)
            response.raise_for_status()

            image_bytes = response.content
            image_size = len(image_bytes)
            logger.info(f"Downloaded {image_size} bytes from BGG")

            # CRITICAL: Always process images through Pillow to check uncompressed size
            # Cloudinary checks uncompressed pixel data, not compressed file size!
            # A 2.5MB compressed PNG can be 11MB uncompressed
            MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB in bytes

            # Try to open and process the image with Pillow
            # If this fails (e.g., mock test data, corrupted file), skip compression
            try:
                image = Image.open(io.BytesIO(image_bytes))
                original_size = image.size
                original_format = image.format or 'JPEG'
                logger.info(f"Opened image: {original_size}, format: {original_format}")

                # Get ACTUAL uncompressed size by saving as uncompressed PNG
                # This matches what Cloudinary will see when processing the image
                test_output = io.BytesIO()
                # Save with no compression to get true uncompressed size
                image.save(test_output, format='PNG', compress_level=0)
                uncompressed_size = len(test_output.getvalue())

                logger.info(
                    f"Image stats: {original_size[0]}x{original_size[1]}, "
                    f"mode: {image.mode}, {original_format} format, "
                    f"compressed: {image_size / (1024 * 1024):.2f}MB, "
                    f"uncompressed: {uncompressed_size / (1024 * 1024):.2f}MB"
                )

                # Resize if either compressed OR uncompressed size > 10MB
                needs_resize = (image_size > MAX_FILE_SIZE) or (uncompressed_size > MAX_FILE_SIZE)
            except Exception as e:
                # If we can't open the image (e.g., mock test data, corrupted file)
                # Upload the original bytes anyway - let Cloudinary handle it
                logger.warning(f"Could not open image with Pillow: {e}, uploading original bytes")
                needs_resize = False  # Skip compression, use original

            # Compression logic (only runs if needs_resize is True)
            if needs_resize:
                logger.warning(
                    f"Image too large for Cloudinary "
                    f"(compressed: {image_size / (1024 * 1024):.2f}MB, "
                    f"uncompressed: {uncompressed_size / (1024 * 1024):.2f}MB, "
                    f"max: {MAX_FILE_SIZE / (1024 * 1024):.0f}MB). Resizing..."
                )

                # OPTIMIZED: WebP compression with 1200px cap for best quality/size ratio
                # WebP achieves 25-35% better compression than JPEG

                # Convert to RGB for WebP (handles transparency)
                if image.mode in ('RGBA', 'LA'):
                    # Keep alpha channel for WebP (it supports transparency)
                    pass  # WebP handles RGBA natively
                elif image.mode == 'P':
                    image = image.convert('RGBA')
                elif image.mode not in ('RGB', 'RGBA', 'L'):
                    image = image.convert('RGB')

                file_size_mb = max(image_size, uncompressed_size) / (1024 * 1024)

                # Simple, effective strategy: 1200px max with WebP compression
                # WebP is much more efficient than JPEG, so fewer dimension steps needed
                max_dimensions = [1200, 1000, 800, 600, 400]  # Start at 1200px
                qualities = [90, 85, 80, 75, 70, 65]  # WebP quality range

                output = None
                final_quality = None
                final_dimension = None
                success = False

                # Try each dimension + quality combination until we succeed
                for max_dimension in max_dimensions:
                    # Resize if needed
                    test_image = image.copy()
                    if max(test_image.size) > max_dimension:
                        ratio = max_dimension / max(test_image.size)
                        new_size = tuple(int(dim * ratio) for dim in test_image.size)
                        test_image = test_image.resize(new_size, Image.Resampling.LANCZOS)

                    # Try each quality level with WebP format
                    for quality in qualities:
                        output = io.BytesIO()
                        # WebP format with quality setting (supports both lossy and lossless)
                        test_image.save(output, format='WEBP', quality=quality, method=6)
                        output_bytes = output.getvalue()
                        compressed_size = len(output_bytes)

                        # Calculate uncompressed size more accurately
                        # Use actual test save to measure what Cloudinary will see
                        test_output = io.BytesIO()
                        test_img = Image.open(io.BytesIO(output_bytes))
                        test_img.save(test_output, format='PNG', compress_level=0)
                        actual_uncompressed = len(test_output.getvalue())

                        # Check if both sizes are acceptable
                        if compressed_size <= MAX_FILE_SIZE and actual_uncompressed <= MAX_FILE_SIZE:
                            final_quality = quality
                            final_dimension = max_dimension
                            image_bytes = output_bytes
                            success = True
                            logger.info(
                                f"✓ WebP compression successful: {file_size_mb:.2f}MB -> {compressed_size / (1024 * 1024):.2f}MB "
                                f"(dimension: {max_dimension}px, quality: {quality}, "
                                f"uncompressed: {actual_uncompressed / (1024 * 1024):.2f}MB)"
                            )
                            break

                    if success:
                        break

                if not success:
                    # Final fallback: ultra-aggressive WebP compression
                    logger.warning("Standard compression failed, trying ultra-aggressive WebP fallback")
                    ultra_dimension = 400
                    ratio = ultra_dimension / max(image.size)
                    new_size = tuple(int(dim * ratio) for dim in image.size)
                    image = image.resize(new_size, Image.Resampling.LANCZOS)

                    output = io.BytesIO()
                    image.save(output, format='WEBP', quality=60, method=6)
                    image_bytes = output.getvalue()

                    if len(image_bytes) <= MAX_FILE_SIZE:
                        logger.warning(
                            f"✓ Ultra-aggressive WebP compression succeeded: {file_size_mb:.2f}MB -> "
                            f"{len(image_bytes) / (1024 * 1024):.2f}MB (400px WebP, quality: 60)"
                        )
                    else:
                        logger.error(
                            f"Image still too large even at 400px WebP quality:60: "
                            f"{len(image_bytes) / (1024 * 1024):.2f}MB. Cannot upload."
                        )
                        self._failed_uploads.add(url)
                        return None

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
            # Track this URL as failed
            self._failed_uploads.add(url)
            return None
        except cloudinary.exceptions.Error as e:
            # Cloudinary-specific errors (rate limits, file size, etc.)
            logger.error(f"Cloudinary API error: {e}")
            # Track this URL as failed
            self._failed_uploads.add(url)
            return None
        except Exception as e:
            logger.error(f"Failed to upload to Cloudinary: {e}")
            # Track this URL as failed
            self._failed_uploads.add(url)
            return None

    def generate_optimized_url(
        self,
        url: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        quality: str = "auto:best",
        format: str = "auto"
    ) -> str:
        """
        Pre-generate an optimized Cloudinary URL without uploading.
        Used for caching URLs in the database during game import.

        This assumes the image will be uploaded on first request via
        the image proxy endpoint, but we can pre-generate the URL
        deterministically based on the source URL hash.

        Args:
            url: Original image URL (from BGG)
            width: Target width for optimal display (optional)
            height: Target height for optimal display (optional)
            quality: Quality setting (default: auto:best)
            format: Output format (default: auto for WebP/AVIF)

        Returns:
            Pre-generated Cloudinary URL with transformations
        """
        if not self.enabled or not url:
            return url

        try:
            public_id = self._get_public_id(url)

            # Build transformation for optimal display
            # For game cards, we typically want medium-sized images
            transformation = {
                "quality": quality,
                "fetch_format": format,
                "crop": "limit",  # Maintain aspect ratio
            }

            # Add responsive sizing if specified
            if width:
                transformation["width"] = width
            if height:
                transformation["height"] = height

            # Generate URL deterministically
            cloudinary_url = CloudinaryImage(public_id).build_url(
                **transformation
            )

            logger.debug(f"Pre-generated Cloudinary URL: {cloudinary_url}")
            return cloudinary_url

        except Exception as e:
            logger.warning(f"Failed to pre-generate Cloudinary URL for {url}: {e}")
            return url  # Fallback to original URL

    def get_image_url(
        self,
        url: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        quality: str = "auto:best",
        format: str = "auto",
        crop: str = "limit",
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
            crop: Crop mode (default: limit - fit within dimensions without cropping)
            gravity: Crop gravity (default: auto)

        Returns:
            Cloudinary URL with transformations, or original URL if upload previously failed
        """
        if not self.enabled:
            return url

        # Check if this URL previously failed to upload
        if url in self._failed_uploads:
            logger.debug(f"URL previously failed to upload, using direct proxy: {url}")
            return url

        try:
            public_id = self._get_public_id(url)

            # PERFORMANCE FIX: Build URL directly without API calls
            # Cloudinary will return 404 if image doesn't exist, which is acceptable
            # This eliminates another 4-6 second API call per request

            # Build transformation parameters
            # Note: Cloudinary expects these exact parameter names
            transformation = {
                "quality": quality,
                "fetch_format": format,
            }

            # Add resize transformations if width/height specified
            if width or height:
                # Use 'limit' crop mode to fit within dimensions without cropping
                # This maintains aspect ratio and ensures the image isn't larger than specified
                transformation["crop"] = crop
                if width:
                    transformation["width"] = width
                if height:
                    transformation["height"] = height
                if crop == "fill":  # Only use gravity for fill mode
                    transformation["gravity"] = gravity

            # Generate URL with transformations
            # Use public_id directly - Cloudinary will handle format detection
            cloudinary_url = CloudinaryImage(public_id).build_url(
                **transformation
            )

            logger.debug(f"Generated Cloudinary URL: {cloudinary_url}")
            return cloudinary_url

        except Exception as e:
            logger.error(f"Failed to generate Cloudinary URL for {url}: {e}")
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
