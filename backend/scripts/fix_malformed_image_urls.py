#!/usr/bin/env python3
"""
Fix Malformed Image URLs in Database
=====================================

This script fixes malformed image URLs that contain Cloudinary transformation
parameters. These malformed URLs should be cleaned to proper BGG URLs, and
the cloudinary_url should be re-generated for optimal performance.

Problem:
    Some games have URLs like:
    https://cf.geekdo-images.com/HASH__original/img/JUNK=/0x0/filters:format(jpeg)/pic123.jpg

Solution:
    Clean to:
    https://cf.geekdo-images.com/HASH__original/pic123.jpg

    Then re-generate cloudinary_url for Cloudinary CDN delivery.

Usage:
    python -m backend.scripts.fix_malformed_image_urls [--dry-run] [--limit N]

Options:
    --dry-run    Show what would be fixed without making changes
    --limit N    Only process N games (useful for testing)
"""

import sys
import os
import logging
import argparse
import re
from typing import Optional

# Ensure we're running from the correct directory
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
os.chdir(backend_dir)

# Add backend directory to path for imports
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import get_db
from models import Game
from services.cloudinary_service import cloudinary_service
from sqlalchemy import or_

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clean_bgg_url(url: str) -> Optional[str]:
    """
    Clean a malformed BGG URL by removing Cloudinary transformation parameters.

    Pattern:
        https://cf.geekdo-images.com/HASH__SIZE/img/JUNK=/0x0/filters:format(ext)/picID.ext

    Clean Result:
        https://cf.geekdo-images.com/HASH__SIZE/picID.ext

    Args:
        url: Potentially malformed BGG URL

    Returns:
        Cleaned URL, or None if cleaning fails
    """
    if not url:
        return None

    # If URL doesn't have transformation params, return as-is
    if '/filters:' not in url and '/fit-in/' not in url and '/c_limit' not in url:
        return url

    try:
        # Extract the pic filename (e.g., pic8894992.jpg)
        pic_match = re.search(r'/(pic\d+\.[a-z]+)$', url)
        if not pic_match:
            logger.warning(f"Could not extract pic filename from: {url[:100]}")
            return None

        pic_filename = pic_match.group(1)

        # Extract the base URL with hash and size (e.g., https://cf.geekdo-images.com/HASH__original)
        base_match = re.match(r'(https://cf\.geekdo-images\.com/[^/]+__[^/]+)', url)
        if not base_match:
            logger.warning(f"Could not extract base URL from: {url[:100]}")
            return None

        base_url = base_match.group(1)

        # Reconstruct clean URL
        cleaned_url = f"{base_url}/{pic_filename}"
        return cleaned_url

    except Exception as e:
        logger.error(f"Failed to clean URL {url[:100]}: {e}")
        return None


def fix_malformed_urls(
    dry_run: bool = False,
    limit: Optional[int] = None
) -> dict:
    """
    Fix malformed image URLs in the database.

    Args:
        dry_run: If True, don't commit changes
        limit: Maximum number of games to process

    Returns:
        Dictionary with statistics
    """
    db = next(get_db())
    stats = {
        'total_checked': 0,
        'malformed_found': 0,
        'image_cleaned': 0,
        'thumbnail_cleaned': 0,
        'cloudinary_regenerated': 0,
        'failed': 0,
        'errors': []
    }

    try:
        # Find all games with potential malformed URLs
        query = db.query(Game).filter(
            or_(
                Game.image.contains('/filters:'),
                Game.thumbnail_url.contains('/filters:'),
                Game.image.contains('/fit-in/'),
                Game.thumbnail_url.contains('/fit-in/'),
                Game.image.contains('/c_limit'),
                Game.thumbnail_url.contains('/c_limit')
            )
        )

        # Apply limit if specified
        if limit:
            query = query.limit(limit)

        games = query.all()
        stats['total_checked'] = len(games)
        stats['malformed_found'] = len(games)

        logger.info("=" * 80)
        logger.info(f"Malformed URL Fix - {'DRY RUN' if dry_run else 'LIVE RUN'}")
        logger.info("=" * 80)
        logger.info(f"Found {stats['malformed_found']} games with malformed URLs")

        if not cloudinary_service.enabled:
            logger.warning("⚠️  Cloudinary is NOT configured!")
            logger.warning("Will clean URLs but cannot regenerate cloudinary_url")
            logger.warning("Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET")

        logger.info("-" * 80)

        # Process each game
        for idx, game in enumerate(games, 1):
            try:
                changes_made = False

                # Clean image URL if malformed
                if game.image and ('/filters:' in game.image or '/fit-in/' in game.image or '/c_limit' in game.image):
                    cleaned_image = clean_bgg_url(game.image)
                    if cleaned_image:
                        logger.info(
                            f"[{idx}/{stats['malformed_found']}] Game {game.id} ({game.title[:40]})"
                        )
                        logger.info(f"  OLD image: {game.image[:100]}...")
                        logger.info(f"  NEW image: {cleaned_image}")
                        if not dry_run:
                            game.image = cleaned_image
                        stats['image_cleaned'] += 1
                        changes_made = True
                    else:
                        logger.error(f"Failed to clean image URL for game {game.id}")
                        stats['failed'] += 1

                # Clean thumbnail_url if malformed
                if game.thumbnail_url and ('/filters:' in game.thumbnail_url or '/fit-in/' in game.thumbnail_url or '/c_limit' in game.thumbnail_url):
                    cleaned_thumbnail = clean_bgg_url(game.thumbnail_url)
                    if cleaned_thumbnail:
                        if not changes_made:
                            logger.info(
                                f"[{idx}/{stats['malformed_found']}] Game {game.id} ({game.title[:40]})"
                            )
                        logger.info(f"  OLD thumbnail: {game.thumbnail_url[:100]}...")
                        logger.info(f"  NEW thumbnail: {cleaned_thumbnail}")
                        if not dry_run:
                            game.thumbnail_url = cleaned_thumbnail
                        stats['thumbnail_cleaned'] += 1
                        changes_made = True
                    else:
                        logger.error(f"Failed to clean thumbnail URL for game {game.id}")
                        stats['failed'] += 1

                # Re-generate cloudinary_url if Cloudinary is enabled
                if changes_made and cloudinary_service.enabled:
                    source_url = game.image or game.thumbnail_url
                    if source_url:
                        cloudinary_url = cloudinary_service.generate_optimized_url(
                            source_url,
                            width=800,
                            height=800,
                            quality="auto:best",
                            format="auto"
                        )
                        logger.info(f"  NEW cloudinary_url: {cloudinary_url[:100]}...")
                        if not dry_run:
                            game.cloudinary_url = cloudinary_url
                        stats['cloudinary_regenerated'] += 1

            except Exception as e:
                error_msg = f"Failed to process game {game.id} ({game.title}): {e}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
                stats['failed'] += 1
                continue

        # Commit changes
        if not dry_run and (stats['image_cleaned'] > 0 or stats['thumbnail_cleaned'] > 0):
            logger.info("-" * 80)
            logger.info(f"Committing changes to database...")
            db.commit()
            logger.info("✓ Changes committed successfully")
        elif dry_run:
            logger.info("-" * 80)
            logger.info("DRY RUN - No changes committed")
            db.rollback()
        else:
            logger.info("-" * 80)
            logger.info("No changes needed")

    except Exception as e:
        logger.error(f"Fatal error during fix: {e}")
        db.rollback()
        raise
    finally:
        db.close()

    return stats


def print_summary(stats: dict, dry_run: bool):
    """Print summary statistics"""
    logger.info("=" * 80)
    logger.info("FIX SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Games checked:             {stats['total_checked']}")
    logger.info(f"Malformed URLs found:      {stats['malformed_found']}")
    logger.info(f"Image URLs cleaned:        {stats['image_cleaned']}")
    logger.info(f"Thumbnail URLs cleaned:    {stats['thumbnail_cleaned']}")
    logger.info(f"Cloudinary URLs regenerated: {stats['cloudinary_regenerated']}")
    logger.info(f"Failed:                    {stats['failed']}")

    if stats['errors']:
        logger.info("")
        logger.info("ERRORS:")
        for error in stats['errors'][:10]:
            logger.info(f"  - {error}")
        if len(stats['errors']) > 10:
            logger.info(f"  ... and {len(stats['errors']) - 10} more errors")

    logger.info("=" * 80)

    if dry_run:
        logger.info("✓ Dry run completed - no changes made")
    elif stats['image_cleaned'] > 0 or stats['thumbnail_cleaned'] > 0:
        logger.info(f"✓ Successfully fixed {stats['malformed_found']} games")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Verify images load correctly on the frontend")
        logger.info("  2. Monitor logs for any remaining malformed URL warnings")
        logger.info("  3. Ensure Cloudinary is properly configured for optimal performance")
    else:
        logger.info("✓ No malformed URLs found")

    logger.info("")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Fix malformed image URLs in database'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be fixed without making changes'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Only process N games (useful for testing)'
    )

    args = parser.parse_args()

    # Confirm if not dry run
    if not args.dry_run:
        logger.warning("")
        logger.warning("⚠️  This will MODIFY the database!")
        logger.warning("Malformed URLs will be cleaned to proper BGG URLs.")
        logger.warning("Cloudinary URLs will be re-generated.")
        logger.warning("")
        logger.warning("Run with --dry-run first to see what will change.")
        logger.warning("")
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            logger.info("Cancelled by user")
            return
        logger.info("")

    # Run fix
    stats = fix_malformed_urls(
        dry_run=args.dry_run,
        limit=args.limit
    )

    # Print summary
    print_summary(stats, args.dry_run)


if __name__ == "__main__":
    main()
