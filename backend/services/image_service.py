# services/image_service.py
"""
Image service layer - handles thumbnail downloads, caching, and image proxying.
Manages background image processing tasks.
Sprint 5: Enhanced with retry logic, error reporting, and failure tracking
"""
import os
import logging
import httpx
import traceback
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

import sentry_sdk

from models import Game, BackgroundTaskFailure
from config import HTTP_TIMEOUT

logger = logging.getLogger(__name__)

# Thumbnail storage directory (ephemeral on Render free tier)
THUMBS_DIR = os.getenv("THUMBS_DIR", "/tmp/thumbs")


class ImageService:
    """Service for image-related operations"""

    def __init__(
        self, db: Session, http_client: Optional[httpx.AsyncClient] = None
    ):
        """
        Initialize image service.

        Args:
            db: Database session
            http_client: Optional httpx client for downloads
        """
        self.db = db
        self.http_client = http_client or httpx.AsyncClient(
            follow_redirects=True, timeout=HTTP_TIMEOUT
        )
        self._ensure_thumbs_dir()

    def _ensure_thumbs_dir(self) -> None:
        """Ensure thumbnails directory exists"""
        os.makedirs(THUMBS_DIR, exist_ok=True)

    async def _record_background_task_failure(
        self,
        task_type: str,
        game_id: Optional[int],
        error: Exception,
        url: Optional[str] = None,
        retry_count: int = 0,
    ) -> None:
        """
        Record background task failure in database for monitoring.
        Sprint 5: Error Handling & Monitoring

        Args:
            task_type: Type of task that failed (e.g., "thumbnail_download")
            game_id: ID of the game related to the failure
            error: The exception that occurred
            url: Associated URL if applicable
            retry_count: Number of retry attempts made
        """
        try:
            failure = BackgroundTaskFailure(
                task_type=task_type,
                game_id=game_id,
                error_message=str(error),
                error_type=type(error).__name__,
                stack_trace=traceback.format_exc(),
                retry_count=retry_count,
                url=url,
                resolved=False,
            )
            self.db.add(failure)
            self.db.commit()

            logger.info(
                f"Recorded background task failure: {task_type} for game {game_id}"
            )

        except Exception as e:
            # Don't let failure tracking break the application
            logger.error(f"Failed to record background task failure: {e}")
            # Still capture the original error in Sentry
            sentry_sdk.capture_exception(error)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def download_thumbnail(
        self, url: str, filename_prefix: str
    ) -> Optional[str]:
        """
        DEPRECATED: Download thumbnail from URL and save to local storage.
        
        This method is deprecated. Cloudinary handles all image resizing on-demand.
        Local thumbnail caching is no longer needed.
        
        Uses exponential backoff retry for network errors.

        Args:
            url: URL of the image to download
            filename_prefix: Prefix for the saved filename

        Returns:
            Filename of saved thumbnail, or None if download failed
        """
        logger.warning(
            "download_thumbnail is deprecated. "
            "Cloudinary handles all image resizing on-demand."
        )
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()

            # Generate filename
            ext = url.split(".")[-1].split("?")[0]  # Handle query params
            if ext not in ["jpg", "jpeg", "png", "webp"]:
                ext = "jpg"
            filename = f"{filename_prefix}.{ext}"
            filepath = os.path.join(THUMBS_DIR, filename)

            # Save file
            with open(filepath, "wb") as f:
                f.write(response.content)

            logger.info(f"Downloaded thumbnail: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Failed to download thumbnail from {url}: {e}")
            # Capture exception in Sentry
            sentry_sdk.capture_exception(e)
            return None

    async def download_and_update_game_thumbnail(
        self, game_id: int, thumbnail_url: str, max_retries: int = 3
    ) -> bool:
        """
        DEPRECATED: Background task to download and update game thumbnail with retry logic.
        
        This method is deprecated. Cloudinary handles all image resizing on-demand.
        Local thumbnail caching is no longer needed.
        
        Sprint 5: Enhanced with Sentry reporting and failure tracking

        Args:
            game_id: ID of the game to update
            thumbnail_url: URL of the thumbnail to download
            max_retries: Maximum number of retry attempts

        Returns:
            True if successful, False otherwise
        """
        logger.warning(
            f"download_and_update_game_thumbnail is deprecated for game {game_id}. "
            "Cloudinary handles all image resizing on-demand."
        )
        game = self.db.get(Game, game_id)
        if not game:
            logger.warning(f"Game {game_id} not found for thumbnail update")
            return False

        # Try download with retries
        for attempt in range(max_retries):
            try:
                filename = await self.download_thumbnail(
                    thumbnail_url, f"{game_id}-{game.title}"
                )

                if filename:
                    # Update game record
                    if hasattr(game, "thumbnail_file"):
                        game.thumbnail_file = filename
                    if hasattr(game, "thumbnail_url"):
                        game.thumbnail_url = f"/thumbs/{filename}"

                    self.db.add(game)
                    self.db.commit()

                    logger.info(
                        f"✓ Thumbnail updated for game {game_id}: {filename}"
                    )
                    return True

            except Exception as e:
                logger.error(
                    f"Attempt {attempt + 1}/{max_retries} failed for game {game_id}: {e}",
                    extra={"game_id": game_id, "url": thumbnail_url},
                )

                # On final retry failure, record in database and Sentry
                if attempt == max_retries - 1:
                    logger.error(
                        f"All retry attempts exhausted for game {game_id}",
                        extra={"game_id": game_id, "url": thumbnail_url},
                    )

                    # Capture in Sentry with context
                    with sentry_sdk.push_scope() as scope:
                        scope.set_tag("task_type", "thumbnail_download")
                        scope.set_context(
                            "game",
                            {"game_id": game_id, "title": game.title},
                        )
                        scope.set_context("download", {"url": thumbnail_url})
                        sentry_sdk.capture_exception(e)

                    # Record failure in database
                    await self._record_background_task_failure(
                        task_type="thumbnail_download",
                        game_id=game_id,
                        error=e,
                        url=thumbnail_url,
                        retry_count=max_retries,
                    )

                    return False

        return False

    async def proxy_image(
        self, url: str, cache_max_age: int = 300
    ) -> tuple[bytes, str, str]:
        """
        Proxy an external image with caching headers.
        Requests modern image formats (WebP/AVIF) for better compression.

        Args:
            url: URL of the image to proxy
            cache_max_age: Cache max age in seconds (default 5 minutes)

        Returns:
            Tuple of (content bytes, content_type, cache_control header)

        Raises:
            httpx.HTTPError: If image fetch fails
        """
        # Request modern image formats for better compression and performance
        # Priority: AVIF (best compression) > WebP (good compression) > any image format
        # CRITICAL: BGG requires proper browser headers to allow image downloads
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://boardgamegeek.com/",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }

        response = await self.http_client.get(url, headers=headers)
        response.raise_for_status()

        content_type = response.headers.get(
            "content-type", "application/octet-stream"
        )
        cache_control = f"public, max-age={cache_max_age}"

        return response.content, content_type, cache_control

    async def reimport_game_thumbnail(self, game_id: int, bgg_id: int) -> bool:
        """
        Re-import game data and thumbnail from BGG.
        Used by bulk reimport operations.
        Uses consolidated GameService.update_game_from_bgg_data method.

        Args:
            game_id: ID of the game to reimport
            bgg_id: BoardGameGeek ID

        Returns:
            True if successful, False otherwise
        """
        from bgg_service import fetch_bgg_thing
        from services.game_service import GameService

        try:
            game = self.db.get(Game, game_id)
            if not game:
                logger.warning(f"Game {game_id} not found for reimport")
                return False

            # Fetch enhanced data from BGG (including sleeve data)
            bgg_data = await fetch_bgg_thing(bgg_id)

            # Use consolidated GameService method for all BGG data mapping
            game_service = GameService(self.db)
            game_service.update_game_from_bgg_data(game, bgg_data, commit=True)

            logger.info(f"Re-imported game {game_id}: {game.title}")
            return True

        except Exception as e:
            logger.error(f"Failed to reimport game {game_id}: {e}")
            return False

    def cleanup_old_thumbnails(self, days: int = 30) -> int:
        """
        Clean up thumbnail files older than specified days.
        Useful for managing storage on ephemeral file systems.

        Args:
            days: Remove files older than this many days

        Returns:
            Number of files removed
        """
        import time
        from pathlib import Path

        count = 0
        cutoff_time = time.time() - (days * 24 * 60 * 60)

        try:
            thumbs_path = Path(THUMBS_DIR)
            for file_path in thumbs_path.glob("*"):
                if file_path.is_file():
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        count += 1
                        logger.debug(
                            f"Removed old thumbnail: {file_path.name}"
                        )

            logger.info(f"Cleaned up {count} old thumbnail files")
            return count

        except Exception as e:
            logger.error(f"Failed to cleanup thumbnails: {e}")
            return count
