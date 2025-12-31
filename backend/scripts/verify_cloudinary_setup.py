#!/usr/bin/env python3
"""
Verify Cloudinary Setup and Detect Fallback Issues
==================================================

This script checks your Cloudinary configuration and identifies why
images might be falling back to direct BGG proxy instead of using Cloudinary.

Usage:
    python -m backend.scripts.verify_cloudinary_setup
"""

import sys
import os
import logging
from typing import Dict, List

# Setup paths
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
os.chdir(backend_dir)

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import get_db
from models import Game
from services.cloudinary_service import cloudinary_service
from config import (
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_ENABLED,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_environment_variables() -> Dict[str, bool]:
    """Check if Cloudinary environment variables are set"""
    logger.info("=" * 70)
    logger.info("1. CLOUDINARY ENVIRONMENT VARIABLES")
    logger.info("=" * 70)

    checks = {
        'CLOUDINARY_CLOUD_NAME': bool(CLOUDINARY_CLOUD_NAME),
        'CLOUDINARY_API_KEY': bool(CLOUDINARY_API_KEY),
        'CLOUDINARY_API_SECRET': bool(CLOUDINARY_API_SECRET),
        'CLOUDINARY_ENABLED': CLOUDINARY_ENABLED,
    }

    for key, value in checks.items():
        if key == 'CLOUDINARY_ENABLED':
            status = "✓ ENABLED" if value else "✗ DISABLED"
            logger.info(f"  {key}: {status}")
        else:
            status = "✓ SET" if value else "✗ NOT SET"
            logger.info(f"  {key}: {status}")
            if value and key == 'CLOUDINARY_CLOUD_NAME':
                logger.info(f"    Value: {CLOUDINARY_CLOUD_NAME}")

    logger.info("")

    if not CLOUDINARY_ENABLED:
        logger.error("⚠️  CLOUDINARY IS DISABLED!")
        logger.error("Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET")
        logger.error("in your environment variables (Render dashboard)")
        return checks

    logger.info("✓ Cloudinary environment variables are configured")
    logger.info("")
    return checks


def check_database_cloudinary_urls() -> Dict[str, any]:
    """Check how many games have cloudinary_url populated"""
    logger.info("=" * 70)
    logger.info("2. DATABASE CLOUDINARY_URL COLUMN")
    logger.info("=" * 70)

    db = next(get_db())

    try:
        # Count games with images
        games_with_images = db.query(Game).filter(
            (Game.image != None) | (Game.thumbnail_url != None)
        ).count()

        # Count games with cloudinary_url
        games_with_cloudinary = db.query(Game).filter(
            Game.cloudinary_url != None,
            Game.cloudinary_url != ''
        ).count()

        # Count games missing cloudinary_url
        games_missing_cloudinary = db.query(Game).filter(
            (Game.image != None) | (Game.thumbnail_url != None),
            (Game.cloudinary_url == None) | (Game.cloudinary_url == '')
        ).count()

        logger.info(f"  Total games with images:     {games_with_images}")
        logger.info(f"  Games WITH cloudinary_url:   {games_with_cloudinary} ({games_with_cloudinary/games_with_images*100 if games_with_images else 0:.1f}%)")
        logger.info(f"  Games MISSING cloudinary_url: {games_missing_cloudinary} ({games_missing_cloudinary/games_with_images*100 if games_with_images else 0:.1f}%)")
        logger.info("")

        if games_missing_cloudinary > 0:
            logger.warning(f"⚠️  {games_missing_cloudinary} games are missing cloudinary_url!")
            logger.warning("This causes slower image loading (no fast path cache)")
            logger.warning("")
            logger.warning("FIX: Run backfill script:")
            logger.warning("  python -m backend.scripts.backfill_cloudinary_urls --dry-run")
            logger.warning("  python -m backend.scripts.backfill_cloudinary_urls")
        else:
            logger.info("✓ All games have cloudinary_url populated")

        logger.info("")

        return {
            'total': games_with_images,
            'with_cloudinary': games_with_cloudinary,
            'missing_cloudinary': games_missing_cloudinary,
        }

    finally:
        db.close()


def check_malformed_urls() -> Dict[str, List[str]]:
    """Check for malformed URLs that might cause issues"""
    logger.info("=" * 70)
    logger.info("3. MALFORMED URL DETECTION")
    logger.info("=" * 70)

    db = next(get_db())

    try:
        # Find games with malformed URLs
        games = db.query(Game).filter(
            (Game.image != None) | (Game.thumbnail_url != None)
        ).all()

        malformed = {
            'cloudinary_params': [],  # BGG URLs with Cloudinary params
            'cloudinary_in_bgg_url': [],  # cloudinary.com in image/thumbnail_url
            'missing_image': [],  # No image URL at all
        }

        for game in games:
            # Check image field
            if game.image:
                if '/fit-in/' in game.image or '/filters:' in game.image or '/c_limit' in game.image:
                    malformed['cloudinary_params'].append(f"Game {game.id} ({game.title}): {game.image[:100]}")
                if 'cloudinary.com' in game.image:
                    malformed['cloudinary_in_bgg_url'].append(f"Game {game.id} ({game.title}): image field")

            # Check thumbnail_url field
            if game.thumbnail_url:
                if '/fit-in/' in game.thumbnail_url or '/filters:' in game.thumbnail_url or '/c_limit' in game.thumbnail_url:
                    malformed['cloudinary_params'].append(f"Game {game.id} ({game.title}): {game.thumbnail_url[:100]}")
                if 'cloudinary.com' in game.thumbnail_url:
                    malformed['cloudinary_in_bgg_url'].append(f"Game {game.id} ({game.title}): thumbnail_url field")

            # Check if both are missing
            if not game.image and not game.thumbnail_url:
                malformed['missing_image'].append(f"Game {game.id} ({game.title})")

        total_issues = sum(len(v) for v in malformed.values())

        if total_issues > 0:
            logger.warning(f"⚠️  Found {total_issues} malformed URL issues")

            if malformed['cloudinary_params']:
                logger.warning(f"\n  BGG URLs with Cloudinary transformation params ({len(malformed['cloudinary_params'])}):")
                for issue in malformed['cloudinary_params'][:5]:
                    logger.warning(f"    - {issue}")
                if len(malformed['cloudinary_params']) > 5:
                    logger.warning(f"    ... and {len(malformed['cloudinary_params']) - 5} more")

            if malformed['cloudinary_in_bgg_url']:
                logger.warning(f"\n  Cloudinary URLs in image/thumbnail_url fields ({len(malformed['cloudinary_in_bgg_url'])}):")
                for issue in malformed['cloudinary_in_bgg_url'][:5]:
                    logger.warning(f"    - {issue}")
                if len(malformed['cloudinary_in_bgg_url']) > 5:
                    logger.warning(f"    ... and {len(malformed['cloudinary_in_bgg_url']) - 5} more")

            if malformed['missing_image']:
                logger.warning(f"\n  Games missing both image and thumbnail_url ({len(malformed['missing_image'])}):")
                for issue in malformed['missing_image'][:5]:
                    logger.warning(f"    - {issue}")
                if len(malformed['missing_image']) > 5:
                    logger.warning(f"    ... and {len(malformed['missing_image']) - 5} more")

            logger.warning("\nFIX: Run fix_malformed_image_urls.py script:")
            logger.warning("  python -m backend.scripts.fix_malformed_image_urls")
        else:
            logger.info("✓ No malformed URLs detected")

        logger.info("")
        return malformed

    finally:
        db.close()


def check_cloudinary_service() -> bool:
    """Test if Cloudinary service is working"""
    logger.info("=" * 70)
    logger.info("4. CLOUDINARY SERVICE TEST")
    logger.info("=" * 70)

    if not cloudinary_service.enabled:
        logger.error("✗ Cloudinary service is DISABLED")
        logger.error("Cannot test Cloudinary functionality")
        logger.info("")
        return False

    try:
        # Test URL generation
        test_url = "https://cf.geekdo-images.com/camo/abc123def456__original/pic123456.jpg"
        generated_url = cloudinary_service.generate_optimized_url(
            test_url,
            width=800,
            height=800,
            quality="auto:best",
            format="auto"
        )

        logger.info(f"  Test URL: {test_url[:60]}...")
        logger.info(f"  Generated Cloudinary URL: {generated_url[:60]}...")

        if 'cloudinary.com' in generated_url:
            logger.info("✓ Cloudinary URL generation working")
        else:
            logger.warning("⚠️  Generated URL does not contain cloudinary.com")

        logger.info("")
        return True

    except Exception as e:
        logger.error(f"✗ Cloudinary service test failed: {e}")
        logger.info("")
        return False


def print_recommendations():
    """Print actionable recommendations"""
    logger.info("=" * 70)
    logger.info("RECOMMENDATIONS")
    logger.info("=" * 70)
    logger.info("")
    logger.info("To ensure Cloudinary is used correctly:")
    logger.info("")
    logger.info("1. SET ENVIRONMENT VARIABLES (if not set):")
    logger.info("   - Go to Render Dashboard → Your Service → Environment")
    logger.info("   - Add: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET")
    logger.info("   - Values from: https://console.cloudinary.com/console")
    logger.info("")
    logger.info("2. POPULATE DATABASE cloudinary_url (if missing):")
    logger.info("   python -m backend.scripts.backfill_cloudinary_urls --dry-run")
    logger.info("   python -m backend.scripts.backfill_cloudinary_urls")
    logger.info("")
    logger.info("3. FIX MALFORMED URLS (if detected):")
    logger.info("   python -m backend.scripts.fix_malformed_image_urls")
    logger.info("")
    logger.info("4. VERIFY IN PRODUCTION:")
    logger.info("   - Check logs for: 'Cloudinary CDN enabled'")
    logger.info("   - Test image URL: /api/public/image-proxy?url=BGG_URL")
    logger.info("   - Should redirect (302) to res.cloudinary.com")
    logger.info("")
    logger.info("5. MONITOR USAGE:")
    logger.info("   - Dashboard: https://console.cloudinary.com/console")
    logger.info("   - Check transformations, bandwidth, storage")
    logger.info("   - Free tier: 25GB bandwidth/month, 25,000 transformations/month")
    logger.info("")


def main():
    """Main verification flow"""
    logger.info("")
    logger.info("╔" + "═" * 68 + "╗")
    logger.info("║" + " " * 10 + "CLOUDINARY SETUP VERIFICATION" + " " * 28 + "║")
    logger.info("╚" + "═" * 68 + "╝")
    logger.info("")

    # Run checks
    env_checks = check_environment_variables()
    db_stats = check_database_cloudinary_urls()
    malformed = check_malformed_urls()
    service_ok = check_cloudinary_service()

    # Print recommendations
    print_recommendations()

    # Summary
    logger.info("=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)

    issues = []

    if not env_checks['CLOUDINARY_ENABLED']:
        issues.append("❌ Cloudinary environment variables not set")
    else:
        logger.info("✓ Cloudinary environment variables configured")

    if db_stats.get('missing_cloudinary', 0) > 0:
        issues.append(f"⚠️  {db_stats['missing_cloudinary']} games missing cloudinary_url")
    else:
        logger.info("✓ All games have cloudinary_url populated")

    total_malformed = sum(len(v) for v in malformed.values())
    if total_malformed > 0:
        issues.append(f"⚠️  {total_malformed} malformed URLs detected")
    else:
        logger.info("✓ No malformed URLs detected")

    if not service_ok and env_checks['CLOUDINARY_ENABLED']:
        issues.append("❌ Cloudinary service test failed")
    elif service_ok:
        logger.info("✓ Cloudinary service working")

    logger.info("")

    if issues:
        logger.warning("ISSUES FOUND:")
        for issue in issues:
            logger.warning(f"  {issue}")
        logger.info("")
        logger.info("See RECOMMENDATIONS above for fixes")
        sys.exit(1)
    else:
        logger.info("✓ All checks passed! Cloudinary is configured correctly.")
        logger.info("")
        logger.info("Images should now:")
        logger.info("  - Load faster (cached cloudinary_url eliminates redirect)")
        logger.info("  - Use less bandwidth (WebP/AVIF compression)")
        logger.info("  - Be globally cached (Cloudinary CDN)")
        sys.exit(0)


if __name__ == "__main__":
    main()
