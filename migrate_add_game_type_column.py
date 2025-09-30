#!/usr/bin/env python3
"""
Migration script to add the 'game_type' column to the games table.
This adds support for BGG-based game type classification.

Run this script once to update the existing database schema.
"""

from sqlalchemy import create_engine, text
from config import DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_game_type_column():
    """Add the game_type column to the games table if it doesn't exist."""
    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as conn:
            # Check if the column already exists
            result = conn.execute(text("PRAGMA table_info(games)"))
            columns = [row[1] for row in result]

            if 'game_type' not in columns:
                logger.info("Adding 'game_type' column to games table...")
                # Add the game_type column
                conn.execute(text("ALTER TABLE games ADD COLUMN game_type VARCHAR(255)"))

                # Create index on the new column for performance
                conn.execute(text("CREATE INDEX idx_game_type ON games (game_type)"))

                conn.commit()
                logger.info("Successfully added 'game_type' column and index to games table")
            else:
                logger.info("'game_type' column already exists in games table")

    except Exception as e:
        logger.error(f"Error adding game_type column: {e}")
        raise

if __name__ == "__main__":
    add_game_type_column()