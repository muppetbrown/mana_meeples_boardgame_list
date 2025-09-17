#!/usr/bin/env python3
"""
Migration script to add the missing 'image' column to the games table.
This addresses the SQLAlchemy error: "no such column: games.image"

Run this script once to update the existing database schema.
"""

from sqlalchemy import create_engine, text
from config import DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_image_column():
    """Add the image column to the games table if it doesn't exist."""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if the column already exists
            result = conn.execute(text("PRAGMA table_info(games)"))
            columns = [row[1] for row in result]
            
            if 'image' not in columns:
                logger.info("Adding 'image' column to games table...")
                # Add the image column
                conn.execute(text("ALTER TABLE games ADD COLUMN image VARCHAR(512)"))
                conn.commit()
                logger.info("Successfully added 'image' column to games table")
            else:
                logger.info("'image' column already exists in games table")
                
    except Exception as e:
        logger.error(f"Error adding image column: {e}")
        raise

if __name__ == "__main__":
    add_image_column()