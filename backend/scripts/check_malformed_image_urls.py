#!/usr/bin/env python3
"""
Check for Malformed Image URLs in Database
==========================================

This script checks the database for games with malformed image URLs.
Specifically looks for:
1. Cloudinary URLs in image/thumbnail_url columns (should only be in cloudinary_url)
2. URLs with Cloudinary transformation parameters embedded
3. Invalid or corrupted URLs

Usage:
    python -m backend.scripts.check_malformed_image_urls [--fix] [--dry-run]

Options:
    --fix        Attempt to fix malformed URLs by clearing them
    --dry-run    Show what would be fixed without making changes
"""

import sys
import os
import logging
import argparse

# Ensure we're running from the correct directory
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
os.chdir(backend_dir)

# Add backend directory to path for imports
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import get_db
from models import Game

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_url_malformed(url: str) -> tuple[bool, str]:
    """
    Check if a URL is malformed.

    Returns:
        Tuple of (is_malformed, reason)
    """
    if not url:
        return False, ""

    # Check for Cloudinary URLs (these should ONLY be in cloudinary_url column)
    if 'cloudinary.com' in url or 'res.cloudinary.com' in url:
        return True, "Contains Cloudinary domain (should be in cloudinary_url column)"

    # Check for Cloudinary transformation parameters embedded in URL
    if '/fit-in/' in url or '/filters:' in url or '/c_limit' in url or '/c_fill' in url:
        return True, "Contains Cloudinary transformation parameters"

    # Check for double-encoded URLs
    if '%252F' in url:  # Double-encoded slash
        return True, "Contains double-encoded characters"

    return False, ""


def check_malformed_urls(fix: bool = False, dry_run: bool = False):
    """
    Check database for malformed image URLs.

    Args:
        fix: If True, attempt to fix malformed URLs
        dry_run: If True, show what would be fixed without making changes
    """
    db = next(get_db())
    stats = {
        'total_games': 0,
        'malformed_image': 0,
        'malformed_thumbnail': 0,
        'fixed': 0,
        'errors': []
    }

    malformed_games = []

    try:
        # Get all games with image URLs
        games = db.query(Game).filter(
            (Game.image.isnot(None)) | (Game.thumbnail_url.isnot(None))
        ).all()

        stats['total_games'] = len(games)

        logger.info("=" * 80)
        logger.info(f"Malformed Image URL Check - {'DRY RUN' if dry_run else 'LIVE RUN' if fix else 'CHECK ONLY'}")
        logger.info("=" * 80)
        logger.info(f"Checking {stats['total_games']} games...")
        logger.info("-" * 80)

        for game in games:
            game_issues = []

            # Check image URL
            if game.image:
                is_malformed, reason = check_url_malformed(game.image)
                if is_malformed:
                    stats['malformed_image'] += 1
                    game_issues.append(f"image: {reason}")
                    logger.warning(
                        f"Game {game.id} ({game.title[:50]}): "
                        f"Malformed image URL - {reason}"
                    )
                    logger.warning(f"  URL: {game.image[:150]}...")

            # Check thumbnail_url
            if game.thumbnail_url:
                is_malformed, reason = check_url_malformed(game.thumbnail_url)
                if is_malformed:
                    stats['malformed_thumbnail'] += 1
                    game_issues.append(f"thumbnail_url: {reason}")
                    logger.warning(
                        f"Game {game.id} ({game.title[:50]}): "
                        f"Malformed thumbnail_url - {reason}"
                    )
                    logger.warning(f"  URL: {game.thumbnail_url[:150]}...")

            if game_issues:
                malformed_games.append({
                    'game': game,
                    'issues': game_issues
                })

        # Fix malformed URLs if requested
        if fix and malformed_games:
            logger.info("-" * 80)
            logger.info(f"{'Would fix' if dry_run else 'Fixing'} {len(malformed_games)} games...")
            logger.info("-" * 80)

            for item in malformed_games:
                game = item['game']
                issues = item['issues']

                try:
                    # Clear malformed URLs
                    # Note: This will trigger re-fetch from BGG or use cloudinary_url
                    if any('image:' in issue for issue in issues):
                        logger.info(
                            f"{'Would clear' if dry_run else 'Clearing'} image for game {game.id} ({game.title[:50]})"
                        )
                        if not dry_run:
                            game.image = None

                    if any('thumbnail_url:' in issue for issue in issues):
                        logger.info(
                            f"{'Would clear' if dry_run else 'Clearing'} thumbnail_url for game {game.id} ({game.title[:50]})"
                        )
                        if not dry_run:
                            game.thumbnail_url = None

                    stats['fixed'] += 1

                except Exception as e:
                    error_msg = f"Failed to fix game {game.id}: {e}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)

            # Commit changes
            if not dry_run:
                logger.info("-" * 80)
                logger.info("Committing changes...")
                db.commit()
                logger.info("✓ Changes committed")
            else:
                logger.info("-" * 80)
                logger.info("DRY RUN - No changes committed")
                db.rollback()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

    # Print summary
    logger.info("=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total games checked:          {stats['total_games']}")
    logger.info(f"Games with malformed image:   {stats['malformed_image']}")
    logger.info(f"Games with malformed thumbnail: {stats['malformed_thumbnail']}")

    if fix:
        logger.info(f"Games fixed:                  {stats['fixed']}")

    if stats['errors']:
        logger.info(f"Errors encountered:           {len(stats['errors'])}")
        for error in stats['errors'][:5]:
            logger.info(f"  - {error}")

    logger.info("=" * 80)

    if stats['malformed_image'] > 0 or stats['malformed_thumbnail'] > 0:
        logger.warning("")
        logger.warning("⚠️  MALFORMED URLS DETECTED!")
        logger.warning("")
        logger.warning("These URLs contain Cloudinary transformation parameters or Cloudinary domains")
        logger.warning("in the image/thumbnail_url columns, which should only contain BGG URLs.")
        logger.warning("")
        if not fix:
            logger.warning("Run with --fix to clear these malformed URLs.")
            logger.warning("The system will then use cloudinary_url if available, or re-fetch from BGG.")
        logger.warning("")
    else:
        logger.info("")
        logger.info("✓ No malformed URLs found")
        logger.info("")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Check for malformed image URLs in database'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Attempt to fix malformed URLs by clearing them'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be fixed without making changes (implies --fix)'
    )

    args = parser.parse_args()

    # Dry run implies fix
    if args.dry_run:
        args.fix = True

    # Confirm if fixing
    if args.fix and not args.dry_run:
        logger.warning("")
        logger.warning("⚠️  This will MODIFY the database!")
        logger.warning("Malformed URLs will be cleared (set to NULL).")
        logger.warning("")
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            logger.info("Cancelled by user")
            return
        logger.info("")

    check_malformed_urls(fix=args.fix, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
