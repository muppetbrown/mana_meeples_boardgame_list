#!/usr/bin/env python3
# run_migrations.py
# Standalone script to run Alembic database migrations

import os
import sys
import subprocess
from pathlib import Path

# Add parent directory to path so we can import from backend
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from database import db_ping, SessionLocal
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_table_exists(table_name: str) -> bool:
    """Check if a table exists in the database"""
    try:
        db = SessionLocal()
        result = db.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :table_name)"
            ),
            {"table_name": table_name}
        )
        exists = result.scalar()
        db.close()
        return exists
    except Exception as e:
        logger.warning(f"Error checking if table exists: {e}")
        return False

def main():
    """
    Run Alembic database migrations.

    This script intelligently handles migrations:
    - If tables already exist, uses `alembic stamp head` to mark them
    - Otherwise, runs `alembic upgrade head` to create tables

    Database migrations are now managed by Alembic instead of in-code migrations.

    See: backend/alembic/ for migration files
    """
    try:
        logger.info("Checking database connection...")

        # Verify database connection first
        if not db_ping():
            logger.error("Cannot connect to database!")
            logger.error("Please check DATABASE_URL environment variable")
            sys.exit(1)

        logger.info("Database connection verified")

        # Change to backend directory where alembic.ini is located
        backend_dir = Path(__file__).parent.parent
        os.chdir(backend_dir)

        # Check if main table already exists
        tables_exist = check_table_exists("boardgames")

        if tables_exist:
            logger.info("Database tables already exist - stamping Alembic version...")
            # Use stamp to mark the current version without running migrations
            result = subprocess.run(
                ["alembic", "stamp", "head"],
                capture_output=True,
                text=True,
                check=False
            )
        else:
            logger.info("Running Alembic migrations...")
            # Run normal upgrade to create tables
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                check=False
            )

        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if result.returncode != 0:
            # Check if error is due to duplicate table (handle gracefully)
            if "already exists" in (result.stderr or ""):
                logger.warning("Tables already exist - attempting to stamp version...")
                # Try stamping as fallback
                stamp_result = subprocess.run(
                    ["alembic", "stamp", "head"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if stamp_result.returncode == 0:
                    logger.info("Successfully stamped Alembic version")
                    return

            logger.error("Alembic migration failed!")
            sys.exit(1)

        logger.info("Migrations completed successfully")

    except FileNotFoundError:
        logger.error("Alembic is not installed!")
        logger.error("Install with: pip install alembic")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
