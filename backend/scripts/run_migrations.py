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
from database import db_ping

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """
    Run Alembic database migrations.

    This script runs `alembic upgrade head` to apply all pending migrations.
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
        logger.info("Running Alembic migrations...")

        # Change to backend directory where alembic.ini is located
        backend_dir = Path(__file__).parent.parent
        os.chdir(backend_dir)

        # Run alembic upgrade head
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
