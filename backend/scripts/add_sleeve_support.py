"""
Migration: Add sleeve support to the database

This script adds:
1. has_sleeves column to boardgames table
2. sleeves table for storing sleeve data

Run with: python -m backend.scripts.add_sleeve_support
"""
import sys
import os

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from database import DATABASE_URL
from models import Base, Sleeve
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Run the migration to add sleeve support"""
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)

    logger.info("Starting sleeve support migration...")

    with engine.connect() as conn:
        # 1. Add has_sleeves column to boardgames table
        try:
            # Check if column already exists
            columns = [col['name'] for col in inspector.get_columns('boardgames')]
            if 'has_sleeves' not in columns:
                logger.info("Adding has_sleeves column to boardgames table...")
                conn.execute(text(
                    "ALTER TABLE boardgames ADD COLUMN has_sleeves VARCHAR(20)"
                ))
                conn.commit()
                logger.info("✓ Added has_sleeves column")
            else:
                logger.info("ℹ has_sleeves column already exists")
        except Exception as e:
            logger.error(f"Error adding has_sleeves column: {e}")
            conn.rollback()
            raise

    # 2. Create sleeves table
    try:
        # Check if table already exists
        if 'sleeves' not in inspector.get_table_names():
            logger.info("Creating sleeves table...")
            Base.metadata.create_all(
                bind=engine,
                tables=[Base.metadata.tables['sleeves']]
            )
            logger.info("✓ Created sleeves table")
        else:
            logger.info("ℹ sleeves table already exists")
    except Exception as e:
        logger.error(f"Error creating sleeves table: {e}")
        raise

    logger.info("✅ Sleeve support migration completed successfully!")


if __name__ == "__main__":
    migrate()
