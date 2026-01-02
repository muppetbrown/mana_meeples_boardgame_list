#!/usr/bin/env python
"""
Clear cached Cloudinary URLs from database.

Since we disabled pre-generation (which was causing 404s), this script
clears all cloudinary_url values to force fresh uploads on next view.

Usage:
    python backend/scripts/clear_cloudinary_cache.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import SessionLocal
from models import Game
from sqlalchemy import update


def clear_cloudinary_urls():
    """Clear all cached cloudinary_url values"""
    db = SessionLocal()

    try:
        # Count games with cloudinary_url set
        games_with_cloudinary = db.query(Game).filter(
            Game.cloudinary_url.isnot(None)
        ).count()

        if games_with_cloudinary == 0:
            print("✓ No cloudinary_url values to clear")
            return

        print(f"Found {games_with_cloudinary} games with cached Cloudinary URLs")

        # Ask for confirmation
        response = input("Clear all cloudinary_url values? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled")
            return

        # Clear cloudinary_url for all games
        result = db.execute(
            update(Game).values(cloudinary_url=None)
        )
        db.commit()

        print(f"✓ Cleared cloudinary_url for {games_with_cloudinary} games")
        print("Images will be uploaded to Cloudinary on next view")

    except Exception as e:
        print(f"✗ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    clear_cloudinary_urls()
