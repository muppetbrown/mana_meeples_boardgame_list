#!/usr/bin/env python3
"""
Fix BGG __original Image URLs
==============================

BGG is now blocking __original size images with 400 Bad Request.
This script replaces __original with allowed sizes based on game popularity.

Usage:
    python -m backend.scripts.fix_bgg_original_urls [--dry-run]
"""

import sys
import os
import logging
import argparse

# Setup paths
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
os.chdir(backend_dir)

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


def get_optimal_image_size(game: Game) -> str:
    """
    Select optimal BGG image size based on game popularity.

    BGG blocks __original downloads with 400 Bad Request.
    Use smaller allowed sizes instead.

    Priority by popularity:
    - Very popular (rank <1000 or 10k+ ratings): __d (detail, ~600x600)
    - Popular (rank <5000 or 5k+ ratings): __d (detail)
    - Moderate (1k+ ratings): __md (medium, ~300x300)
    - Less popular/new: __mt (medium-thumb, ~150x150)
    """
    users_rated = getattr(game, 'users_rated', 0) or 0
    bgg_rank = getattr(game, 'bgg_rank', None)

    # Very popular games: detail size usually works
    if bgg_rank and bgg_rank < 1000:
        return "detail"
    elif users_rated >= 10000:
        return "detail"

    # Popular games: detail size
    elif bgg_rank and bgg_rank < 5000:
        return "detail"
    elif users_rated >= 5000:
        return "detail"

    # Moderate popularity: medium
    elif users_rated >= 1000:
        return "medium"

    # Less popular/new games: medium-thumb (most reliable)
    else:
        return "medium-thumb"


def replace_image_size(url: str, target_size: str) -> str:
    """
    Replace image size in BGG URL.

    __original → __d (detail)
    __original → __md (medium)
    __original → __mt (medium-thumb)
    __original → __t (thumbnail)
    """
    if not url or 'cf.geekdo-images.com' not in url:
        return url

    size_map = {
        'detail': '__d',
        'medium': '__md',
        'medium-thumb': '__mt',
        'thumbnail': '__t',
    }

    target_suffix = size_map.get(target_size, '__md')

    # Replace any existing size suffix with target
    for suffix in ['__original', '__d', '__md', '__mt', '__t']:
        url = url.replace(suffix, target_suffix)

    return url


def main():
    parser = argparse.ArgumentParser(
        description='Fix BGG __original URLs that are blocked with 400 Bad Request'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info(f"FIX BGG __ORIGINAL URLS - {'DRY RUN' if args.dry_run else 'LIVE RUN'}")
    logger.info("=" * 70)
    logger.info("")
    logger.info("PROBLEM: BGG now blocks __original image downloads with 400 Bad Request")
    logger.info("SOLUTION: Replace __original with allowed sizes based on popularity")
    logger.info("")

    db = next(get_db())

    try:
        # Find games with __original in their URLs
        games = db.query(Game).filter(
            (Game.image.like('%__original%')) |
            (Game.thumbnail_url.like('%__original%'))
        ).all()

        logger.info(f"Found {len(games)} games with __original URLs")
        logger.info("-" * 70)

        stats = {
            'total': len(games),
            'updated': 0,
            'failed': 0,
        }

        for idx, game in enumerate(games, 1):
            try:
                # Determine optimal size
                optimal_size = get_optimal_image_size(game)

                # Fix image URL
                old_image = game.image
                if old_image and '__original' in old_image:
                    new_image = replace_image_size(old_image, optimal_size)
                    if not args.dry_run:
                        game.image = new_image

                    logger.info(
                        f"[{idx}/{stats['total']}] Game {game.id}: {game.title[:40]}"
                    )
                    logger.info(f"  Size: {optimal_size} (users_rated: {getattr(game, 'users_rated', 0)}, rank: {getattr(game, 'bgg_rank', 'N/A')})")
                    logger.info(f"  OLD: {old_image[:80]}...")
                    logger.info(f"  NEW: {new_image[:80]}...")

                # Fix thumbnail_url
                old_thumb = game.thumbnail_url
                if old_thumb and '__original' in old_thumb:
                    new_thumb = replace_image_size(old_thumb, optimal_size)
                    if not args.dry_run:
                        game.thumbnail_url = new_thumb

                # Regenerate cloudinary_url with new URL
                if not args.dry_run and hasattr(game, 'cloudinary_url'):
                    source_url = game.image or game.thumbnail_url
                    if source_url:
                        cloudinary_url = cloudinary_service.generate_optimized_url(
                            source_url,
                            width=800,
                            height=800,
                            quality="auto:best",
                            format="auto"
                        )
                        game.cloudinary_url = cloudinary_url
                        logger.info(f"  Cloudinary URL regenerated")

                stats['updated'] += 1
                logger.info("")

            except Exception as e:
                stats['failed'] += 1
                logger.error(f"[{idx}/{stats['total']}] Failed: Game {game.id}: {e}")
                continue

        # Commit changes
        if not args.dry_run and stats['updated'] > 0:
            logger.info("=" * 70)
            logger.info(f"Committing {stats['updated']} updates...")
            db.commit()
            logger.info("✓ Changes committed")
        elif args.dry_run:
            logger.info("=" * 70)
            logger.info("DRY RUN - No changes committed")
            db.rollback()

        # Summary
        logger.info("=" * 70)
        logger.info("SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total games with __original: {stats['total']}")
        logger.info(f"Successfully updated:         {stats['updated']}")
        logger.info(f"Failed:                       {stats['failed']}")
        logger.info("")

        if not args.dry_run and stats['updated'] > 0:
            logger.info("✓ Database updated successfully")
            logger.info("")
            logger.info("NEXT STEPS:")
            logger.info("1. Restart your application to clear any caches")
            logger.info("2. Test image loading on frontend")
            logger.info("3. Images should now load via Cloudinary (no 400 errors)")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
