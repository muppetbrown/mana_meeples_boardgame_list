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
import database
db_ping = database.db_ping
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_table_exists(table_name: str) -> bool:
    """Check if a table exists in the database"""
    try:
        db = database.SessionLocal()
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

def _alembic(*args):
    """Run an alembic command and capture its output."""
    return subprocess.run(
        ["alembic", *args], capture_output=True, text=True, check=False
    )


def main():
    """
    Bring the database schema up to date with Alembic.

    - Normal case (the database has an ``alembic_version`` table, or is empty):
      ``alembic upgrade head`` - applies any pending migrations and is a no-op when
      already current.
    - Legacy case (application tables exist but there is NO migration history):
      ``alembic stamp head`` once, so the existing schema is adopted.

    IMPORTANT: a database that already has migration history must NEVER be stamped. Stamping
    marks every pending migration as applied *without running it*, which would silently skip
    schema changes (e.g. a column type change) while the application code expects them.
    A failing migration is reported as a failure - it is not papered over.

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

        has_app_tables = check_table_exists("boardgames")
        has_migration_history = check_table_exists("alembic_version")

        if has_app_tables and not has_migration_history:
            logger.warning(
                "Existing schema without migration history - stamping Alembic head (one-time adoption)..."
            )
            result = _alembic("stamp", "head")
        else:
            logger.info("Running Alembic migrations (alembic upgrade head)...")
            result = _alembic("upgrade", "head")

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
