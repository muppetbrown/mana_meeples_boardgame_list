# services/image_service.py
"""
Image service layer - handles thumbnail downloads, caching, and image proxying.
Manages background image processing tasks.
"""
import os
import logging
import httpx
from typing import Optional
from sqlalchemy.orm import Session

from models import Game
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

    def _ensure_thumbs_dir(self):
        """Ensure thumbnails directory exists"""
        os.makedirs(THUMBS_DIR, exist_ok=True)

    async def download_thumbnail(
        self, url: str, filename_prefix: str
    ) -> Optional[str]:
        """
        Download thumbnail from URL and save to local storage.

        Args:
            url: URL of the image to download
            filename_prefix: Prefix for the saved filename

        Returns:
            Filename of saved thumbnail, or None if download failed
        """
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
            return None

    async def download_and_update_game_thumbnail(
        self, game_id: int, thumbnail_url: str, max_retries: int = 3
    ) -> bool:
        """
        Background task to download and update game thumbnail with retry logic.

        Args:
            game_id: ID of the game to update
            thumbnail_url: URL of the thumbnail to download
            max_retries: Maximum number of retry attempts

        Returns:
            True if successful, False otherwise
        """
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
                    f"Attempt {attempt + 1}/{max_retries} failed for game {game_id}: {e}"
                )
                if attempt == max_retries - 1:
                    logger.error(
                        f"All retry attempts exhausted for game {game_id}"
                    )
                    return False

        return False

    async def proxy_image(
        self, url: str, cache_max_age: int = 300
    ) -> tuple[bytes, str, str]:
        """
        Proxy an external image with caching headers.

        Args:
            url: URL of the image to proxy
            cache_max_age: Cache max age in seconds (default 5 minutes)

        Returns:
            Tuple of (content bytes, content_type, cache_control header)

        Raises:
            httpx.HTTPError: If image fetch fails
        """
        response = await self.http_client.get(url)
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

        Args:
            game_id: ID of the game to reimport
            bgg_id: BoardGameGeek ID

        Returns:
            True if successful, False otherwise
        """
        from bgg_service import fetch_bgg_thing

        try:
            game = self.db.get(Game, game_id)
            if not game:
                logger.warning(f"Game {game_id} not found for reimport")
                return False

            # Fetch enhanced data from BGG
            bgg_data = await fetch_bgg_thing(bgg_id)

            # Update game with enhanced data (using GameService would be better,
            # but avoiding circular import)
            game.title = bgg_data.get("title", game.title)
            game.categories = ", ".join(bgg_data.get("categories", []))
            game.year = bgg_data.get("year", game.year)
            game.players_min = bgg_data.get("players_min", game.players_min)
            game.players_max = bgg_data.get("players_max", game.players_max)
            game.playtime_min = bgg_data.get("playtime_min", game.playtime_min)
            game.playtime_max = bgg_data.get("playtime_max", game.playtime_max)

            # Update enhanced fields if they exist
            enhanced_fields = [
                "description",
                "designers",
                "publishers",
                "mechanics",
                "artists",
                "average_rating",
                "complexity",
                "bgg_rank",
                "users_rated",
                "min_age",
                "is_cooperative",
                "game_type",
                "image",
                "thumbnail_url",
            ]
            for field in enhanced_fields:
                if hasattr(game, field):
                    setattr(game, field, bgg_data.get(field))

            self.db.add(game)
            self.db.commit()

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
