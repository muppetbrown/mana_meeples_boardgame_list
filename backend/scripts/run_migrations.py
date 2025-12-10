#!/usr/bin/env python3
# run_migrations.py
# Standalone script to run database migrations without starting the FastAPI app

import os
import sys
from pathlib import Path

# Add parent directory to path so we can import from backend
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from database import run_migrations, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Run database migrations"""
    try:
        logger.info("Running database migrations...")

        # Create tables from models
        init_db()
        logger.info("Created tables from models")

        # Run migrations (will skip if already applied)
        run_migrations()
        logger.info("Migrations completed successfully")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
