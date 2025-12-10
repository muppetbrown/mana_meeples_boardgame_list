from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from config import DATABASE_URL
from models import Base
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# PostgreSQL connection pooling configuration
engine_kwargs = {
    "poolclass": QueuePool,
    "pool_size": 5,  # Number of permanent connections
    "max_overflow": 10,  # Additional connections when pool is full
    "pool_timeout": 30,  # Seconds to wait for connection from pool
    "pool_recycle": 3600,  # Recycle connections after 1 hour
    "pool_pre_ping": True,  # Test connections before using them
    "echo": False,  # Set to True for SQL debugging
}

logger.info(
    f"Configuring database engine for: {DATABASE_URL.split('@')[0]}@..."
)
engine = create_engine(DATABASE_URL, future=True, **engine_kwargs)
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, future=True
)


def db_ping() -> bool:
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1;")
        return True
    except Exception:
        return False


def init_db():
    Base.metadata.create_all(bind=engine)


def run_migrations():
    """
    Run database migrations for schema updates.
    This handles adding new columns and updating existing data.

    Note: Skipped for SQLite (test databases) as they don't support
    PostgreSQL-specific information_schema queries.
    """
    # Skip migrations for SQLite (used in tests)
    if "sqlite" in DATABASE_URL.lower():
        logger.info("SQLite detected - skipping migrations (test mode)")
        return

    logger.info("Running database migrations...")

    with engine.connect() as conn:
        # Migration: Add date_added column if it doesn't exist
        try:
            # Check if column exists (PostgreSQL-specific)
            result = conn.execute(
                text(
                    """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='boardgames' AND column_name='date_added'
            """
                )
            )
            column_exists = result.fetchone() is not None

            if not column_exists:
                logger.info("Adding date_added column to boardgames table...")
                conn.execute(
                    text(
                        """
                    ALTER TABLE boardgames
                    ADD COLUMN date_added TIMESTAMP
                """
                    )
                )
                conn.commit()
                logger.info("date_added column added successfully")

            # Set default date for existing games with NULL date_added
            # July 1, 2025
            default_date = datetime(2025, 7, 1)
            result = conn.execute(
                text(
                    """
                UPDATE boardgames
                SET date_added = :default_date
                WHERE date_added IS NULL
            """
                ),
                {"default_date": default_date},
            )
            conn.commit()

            rows_updated = result.rowcount
            if rows_updated > 0:
                logger.info(
                    f"Set date_added to July 1, 2025 for {rows_updated} existing games"
                )

        except Exception as e:
            logger.error(f"Migration error (date_added): {e}")
            conn.rollback()
            raise

        # Migration: Add expansion-related columns if they don't exist
        try:
            expansion_columns = [
                ("is_expansion", "BOOLEAN DEFAULT FALSE NOT NULL"),
                ("base_game_id", "INTEGER"),
                ("expansion_type", "VARCHAR(50)"),
                ("modifies_players_min", "INTEGER"),
                ("modifies_players_max", "INTEGER"),
            ]

            for col_name, col_type in expansion_columns:
                # Check if column exists
                result = conn.execute(
                    text(
                        """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name='boardgames' AND column_name=:col_name
                """
                    ),
                    {"col_name": col_name},
                )
                column_exists = result.fetchone() is not None

                if not column_exists:
                    logger.info(
                        f"Adding {col_name} column to boardgames table..."
                    )
                    conn.execute(
                        text(
                            f"""
                        ALTER TABLE boardgames
                        ADD COLUMN {col_name} {col_type}
                    """
                        )
                    )
                    conn.commit()
                    logger.info(f"{col_name} column added successfully")

            # Add foreign key constraint if it doesn't exist
            result = conn.execute(
                text(
                    """
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name='boardgames' AND constraint_name='fk_base_game'
            """
                )
            )
            fk_exists = result.fetchone() is not None

            if not fk_exists:
                logger.info(
                    "Adding foreign key constraint for base_game_id..."
                )
                conn.execute(
                    text(
                        """
                    ALTER TABLE boardgames
                    ADD CONSTRAINT fk_base_game
                    FOREIGN KEY (base_game_id) REFERENCES boardgames(id)
                """
                    )
                )
                conn.commit()
                logger.info("Foreign key constraint added successfully")

            # Add index for expansion lookups if it doesn't exist
            result = conn.execute(
                text(
                    """
                SELECT indexname
                FROM pg_indexes
                WHERE tablename='boardgames' AND indexname='idx_expansion_lookup'
            """
                )
            )
            index_exists = result.fetchone() is not None

            if not index_exists:
                logger.info(
                    "Adding index for expansion lookups..."
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX idx_expansion_lookup
                    ON boardgames(is_expansion, base_game_id)
                """
                    )
                )
                conn.commit()
                logger.info("Expansion lookup index added successfully")

        except Exception as e:
            logger.error(f"Migration error (expansion fields): {e}")
            conn.rollback()
            raise

    logger.info("Database migrations completed")


def get_db():
    """Database session dependency for FastAPI endpoints"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
