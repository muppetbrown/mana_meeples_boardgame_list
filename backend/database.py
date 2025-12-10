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
        try:
            # Migration 1: Add date_added column if it doesn't exist
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

            # Migration 1.5: Add status column if it doesn't exist
            result = conn.execute(
                text(
                    """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='boardgames' AND column_name='status'
            """
                )
            )
            column_exists = result.fetchone() is not None

            if not column_exists:
                logger.info("Adding status column to boardgames table...")
                conn.execute(
                    text(
                        """
                    ALTER TABLE boardgames
                    ADD COLUMN status VARCHAR(20) DEFAULT 'OWNED'
                """
                    )
                )
                conn.commit()
                logger.info("status column added successfully")

                # Create index on status
                conn.execute(
                    text(
                        """
                    CREATE INDEX idx_boardgames_status ON boardgames(status)
                """
                    )
                )
                conn.commit()
                logger.info("Created index on status column")

            # Migration 2: Create buy_list_games table
            result = conn.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public' AND table_name='buy_list_games'
            """
                )
            )
            table_exists = result.fetchone() is not None

            if not table_exists:
                logger.info("Creating buy_list_games table...")
                conn.execute(
                    text(
                        """
                    CREATE TABLE buy_list_games (
                        id SERIAL PRIMARY KEY,
                        game_id INTEGER NOT NULL UNIQUE REFERENCES boardgames(id) ON DELETE CASCADE,
                        rank INTEGER,
                        bgo_link TEXT,
                        lpg_rrp NUMERIC(10, 2),
                        lpg_status VARCHAR(50),
                        on_buy_list BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX idx_buy_list_game_id ON buy_list_games(game_id)
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX idx_buy_list_rank ON buy_list_games(on_buy_list, rank)
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX idx_buy_list_status ON buy_list_games(lpg_status, on_buy_list)
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX idx_buy_list_rank_only ON buy_list_games(rank)
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX idx_buy_list_on_buy_list ON buy_list_games(on_buy_list)
                """
                    )
                )
                conn.commit()
                logger.info("buy_list_games table created successfully")

            # Migration 3: Create price_snapshots table
            result = conn.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public' AND table_name='price_snapshots'
            """
                )
            )
            table_exists = result.fetchone() is not None

            if not table_exists:
                logger.info("Creating price_snapshots table...")
                conn.execute(
                    text(
                        """
                    CREATE TABLE price_snapshots (
                        id SERIAL PRIMARY KEY,
                        game_id INTEGER NOT NULL REFERENCES boardgames(id) ON DELETE CASCADE,
                        checked_at TIMESTAMP NOT NULL,
                        low_price NUMERIC(10, 2),
                        mean_price NUMERIC(10, 2),
                        best_price NUMERIC(10, 2),
                        best_store TEXT,
                        discount_pct NUMERIC(5, 2),
                        delta NUMERIC(5, 2),
                        source_file TEXT,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX idx_price_snapshot_game_id ON price_snapshots(game_id)
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX idx_price_snapshot_checked_at ON price_snapshots(checked_at)
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX idx_price_snapshot_game_date ON price_snapshots(game_id, checked_at)
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX idx_price_snapshot_best ON price_snapshots(best_price, discount_pct)
                """
                    )
                )
                conn.commit()
                logger.info("price_snapshots table created successfully")

            # Migration 4: Create price_offers table
            result = conn.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public' AND table_name='price_offers'
            """
                )
            )
            table_exists = result.fetchone() is not None

            if not table_exists:
                logger.info("Creating price_offers table...")
                conn.execute(
                    text(
                        """
                    CREATE TABLE price_offers (
                        id SERIAL PRIMARY KEY,
                        game_id INTEGER NOT NULL REFERENCES boardgames(id) ON DELETE CASCADE,
                        checked_at TIMESTAMP NOT NULL,
                        store TEXT,
                        price_nzd NUMERIC(10, 2),
                        availability TEXT,
                        store_link TEXT,
                        in_stock BOOLEAN,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX idx_price_offer_game_id ON price_offers(game_id)
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX idx_price_offer_checked_at ON price_offers(checked_at)
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX idx_price_offer_game_date ON price_offers(game_id, checked_at)
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE INDEX idx_price_offer_store ON price_offers(store, in_stock)
                """
                    )
                )
                conn.commit()
                logger.info("price_offers table created successfully")

        except Exception as e:
            logger.error(f"Migration error: {e}")
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
