#!/usr/bin/env python3
"""
Backfill Cloudinary URLs for Existing Games
============================================

This script populates the cloudinary_url column for games that are missing it.
Pre-generating these URLs eliminates 50-150ms redirect overhead per image request.

Usage:
    python -m backend.scripts.backfill_cloudinary_urls [--dry-run] [--limit N]

Options:
    --dry-run    Show what would be updated without making changes
    --limit N    Only process N games (useful for testing)
    --force      Re-generate URLs even if they already exist
"""

import sys
import os
import logging
import argparse
from typing import Optional

# Ensure we're running from the correct directory
# This script needs to be run from the backend/ directory for imports to work
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
project_root = os.path.dirname(backend_dir)

# Change to backend directory for relative imports to work
os.chdir(backend_dir)

# Add backend directory to path for imports
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import get_db
from models import Game
from services.cloudinary_service import cloudinary_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def backfill_cloudinary_urls(
    dry_run: bool = False,
    limit: Optional[int] = None,
    force: bool = False
) -> dict:
    """
    Backfill cloudinary_url for games that need it.

    Args:
        dry_run: If True, don't commit changes
        limit: Maximum number of games to process
        force: If True, regenerate URLs even if they exist

    Returns:
        Dictionary with statistics
    """
    db = next(get_db())
    stats = {
        'total_games': 0,
        'processed': 0,
        'updated': 0,
        'skipped': 0,
        'failed': 0,
        'errors': []
    }

    try:
        # Build query
        query = db.query(Game)

        # Filter: only games with image URLs
        query = query.filter(
            (Game.image != None) | (Game.thumbnail_url != None)
        )

        # Filter: only games missing cloudinary_url (unless force)
        if not force:
            query = query.filter(
                (Game.cloudinary_url == None) | (Game.cloudinary_url == '')
            )

        # Apply limit if specified
        if limit:
            query = query.limit(limit)

        games = query.all()
        stats['total_games'] = len(games)

        logger.info("=" * 70)
        logger.info(f"Cloudinary URL Backfill - {'DRY RUN' if dry_run else 'LIVE RUN'}")
        logger.info("=" * 70)
        logger.info(f"Found {stats['total_games']} games to process")
        logger.info(f"Force regenerate: {force}")

        if not cloudinary_service.enabled:
            logger.warning("⚠️  Cloudinary is NOT configured!")
            logger.warning("URLs will be generated but won't work without Cloudinary credentials.")
            logger.warning("Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET")

        logger.info("-" * 70)

        # Process each game
        for idx, game in enumerate(games, 1):
            stats['processed'] += 1

            try:
                # Determine which image URL to use (prefer image over thumbnail_url)
                source_url = game.image or game.thumbnail_url

                if not source_url:
                    logger.debug(f"[{idx}/{stats['total_games']}] Skipping game {game.id} ({game.title}) - no image URL")
                    stats['skipped'] += 1
                    continue

                # Generate optimized Cloudinary URL
                # Use same settings as in game_service.py:789-795
                cloudinary_url = cloudinary_service.generate_optimized_url(
                    source_url,
                    width=800,
                    height=800,
                    quality="auto:best",
                    format="auto"  # Auto WebP/AVIF
                )

                # Check if URL changed
                old_url = game.cloudinary_url
                if old_url == cloudinary_url and not force:
                    logger.debug(f"[{idx}/{stats['total_games']}] Skipping game {game.id} ({game.title}) - URL unchanged")
                    stats['skipped'] += 1
                    continue

                # Update the game
                game.cloudinary_url = cloudinary_url
                stats['updated'] += 1

                # Log progress every 10 games or on significant updates
                if idx % 10 == 0 or stats['updated'] <= 5:
                    logger.info(
                        f"[{idx}/{stats['total_games']}] ✓ Updated game {game.id}: {game.title[:50]}"
                    )
                    if cloudinary_service.enabled:
                        logger.debug(f"  URL: {cloudinary_url[:100]}...")
                    else:
                        logger.debug(f"  URL: (Cloudinary disabled, using fallback)")

            except Exception as e:
                stats['failed'] += 1
                error_msg = f"Failed to process game {game.id} ({game.title}): {e}"
                logger.error(f"[{idx}/{stats['total_games']}] ✗ {error_msg}")
                stats['errors'].append(error_msg)
                continue

        # Commit changes
        if not dry_run and stats['updated'] > 0:
            logger.info("-" * 70)
            logger.info(f"Committing {stats['updated']} updates to database...")
            db.commit()
            logger.info("✓ Commit successful")
        elif dry_run:
            logger.info("-" * 70)
            logger.info("DRY RUN - No changes committed")
            db.rollback()
        else:
            logger.info("-" * 70)
            logger.info("No updates needed")

    except Exception as e:
        logger.error(f"Fatal error during backfill: {e}")
        db.rollback()
        raise
    finally:
        db.close()

    return stats


def print_summary(stats: dict, dry_run: bool):
    """Print summary statistics"""
    logger.info("=" * 70)
    logger.info("BACKFILL SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total games found:     {stats['total_games']}")
    logger.info(f"Games processed:       {stats['processed']}")
    logger.info(f"Games updated:         {stats['updated']}")
    logger.info(f"Games skipped:         {stats['skipped']}")
    logger.info(f"Games failed:          {stats['failed']}")

    if stats['errors']:
        logger.info("")
        logger.info("ERRORS:")
        for error in stats['errors'][:10]:  # Show first 10 errors
            logger.info(f"  - {error}")
        if len(stats['errors']) > 10:
            logger.info(f"  ... and {len(stats['errors']) - 10} more errors")

    logger.info("=" * 70)

    if dry_run:
        logger.info("✓ Dry run completed - no changes made")
    elif stats['updated'] > 0:
        logger.info(f"✓ Successfully updated {stats['updated']} games")
    else:
        logger.info("✓ No updates needed")

    logger.info("")
    logger.info("Performance Impact:")
    logger.info(f"  - Image load time improvement: ~50-150ms per game")
    logger.info(f"  - Total time saved per page load: ~{stats['updated'] * 0.1:.1f}s (assuming 10 games/page)")
    logger.info("")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Backfill cloudinary_url column for existing games'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Only process N games (useful for testing)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Re-generate URLs even if they already exist'
    )

    args = parser.parse_args()

    # Confirm if not dry run
    if not args.dry_run:
        logger.warning("")
        logger.warning("⚠️  This will UPDATE the database!")
        logger.warning("Run with --dry-run first to see what will change.")
        logger.warning("")
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            logger.info("Cancelled by user")
            return
        logger.info("")

    # Run backfill
    stats = backfill_cloudinary_urls(
        dry_run=args.dry_run,
        limit=args.limit,
        force=args.force
    )

    # Print summary
    print_summary(stats, args.dry_run)


if __name__ == "__main__":
    main()
