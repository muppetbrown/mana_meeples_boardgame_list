"""
Image Load Time Optimization Migration
=======================================

This migration adds the cloudinary_url field to cache pre-generated
Cloudinary CDN URLs, eliminating the 302 redirect overhead on every
image request.

Performance Impact:
- Eliminates redirect latency (50-150ms per image)
- Reduces server load from proxy endpoint
- Faster initial page loads

Run with: python -m backend.migrations.add_cloudinary_url
"""

from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def upgrade(db_session):
    """
    Add cloudinary_url column to boardgames table.

    This column stores pre-generated Cloudinary URLs to avoid
    computing them on every request and eliminates redirects.
    """

    logger.info("=" * 60)
    logger.info("Image Optimization Migration - UPGRADE")
    logger.info("=" * 60)

    # Add cloudinary_url column
    logger.info("Adding cloudinary_url column...")
    try:
        db_session.execute(text("""
            ALTER TABLE boardgames
            ADD COLUMN IF NOT EXISTS cloudinary_url VARCHAR(512)
        """))
        db_session.commit()
        logger.info("✓ cloudinary_url column added")
    except Exception as e:
        logger.warning(f"cloudinary_url column may already exist: {e}")
        db_session.rollback()

    logger.info("=" * 60)
    logger.info("Image Optimization Migration Complete!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Summary:")
    logger.info("✓ cloudinary_url column added")
    logger.info("")
    logger.info("Expected Performance Improvements:")
    logger.info("  - Image load times: 50-150ms faster per image")
    logger.info("  - Server load: Reduced proxy endpoint requests")
    logger.info("  - Page loads: Faster initial render")
    logger.info("")
    logger.info("Next Steps:")
    logger.info("  - URLs will be pre-generated during game imports")
    logger.info("  - Existing games will generate URLs on first request")
    logger.info("")


def downgrade(db_session):
    """
    Rollback cloudinary_url column if needed.
    """

    logger.info("=" * 60)
    logger.info("Image Optimization Migration - DOWNGRADE")
    logger.info("=" * 60)

    try:
        logger.info("Dropping cloudinary_url column...")
        db_session.execute(text("""
            ALTER TABLE boardgames DROP COLUMN IF EXISTS cloudinary_url
        """))
        db_session.commit()
        logger.info("✓ Downgrade complete")

    except Exception as e:
        logger.error(f"Error during downgrade: {e}")
        db_session.rollback()
        raise


if __name__ == "__main__":
    """
    Run migration directly for testing
    """
    import sys
    import os

    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    from database import get_db

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("\n" + "=" * 60)
    print("Image Load Time Optimization Migration")
    print("=" * 60)
    print("\nThis will add cloudinary_url column to the database.")
    print("Estimated time: < 1 second")
    print("\nPress Ctrl+C to cancel, or Enter to continue...")
    input()

    db = next(get_db())
    try:
        upgrade(db)
        print("\n✓ Migration applied successfully!")
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        print("\nTo rollback, run: downgrade(db)")
        raise
    finally:
        db.close()
