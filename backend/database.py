from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from config import DATABASE_URL, READ_REPLICA_URL
from models import Base
from datetime import datetime
import logging
import time
import os

logger = logging.getLogger(__name__)

# Phase 1 Performance: Slow query logger
# Separate logger for database queries to enable fine-grained control
query_logger = logging.getLogger('sqlalchemy.queries')
query_logger.setLevel(logging.WARNING)  # Only log slow queries

# PostgreSQL connection pooling configuration
# Optimized for high concurrency load (Sprint 12: Performance)
engine_kwargs = {
    "poolclass": QueuePool,
    "pool_size": 15,  # Number of permanent connections (increased for load tests)
    "max_overflow": 20,  # Additional connections when pool is full
    "pool_timeout": 30,  # Seconds to wait for connection from pool
    "pool_recycle": 3600,  # Recycle connections after 1 hour
    "pool_pre_ping": True,  # Test connections before using them
    "echo": False,  # Set to True for SQL debugging
}

# Primary database engine (write operations)
logger.info(
    f"Configuring primary database engine for: {DATABASE_URL.split('@')[0] if '@' in DATABASE_URL else DATABASE_URL}@..."
)
engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)

# Read replica engine (read-only operations for better performance)
# Falls back to primary database if READ_REPLICA_URL is not configured
if READ_REPLICA_URL:
    logger.info(
        f"Configuring read replica engine for: {READ_REPLICA_URL.split('@')[0] if '@' in READ_REPLICA_URL else 'configured'}@..."
    )
    read_engine = create_engine(READ_REPLICA_URL, **engine_kwargs)
    ReadSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=read_engine
    )
else:
    logger.info("Read replica not configured - using primary database for reads")
    read_engine = engine
    ReadSessionLocal = SessionLocal


# ------------------------------------------------------------------------------
# Phase 1 Performance: SQLAlchemy Query Monitoring
# ------------------------------------------------------------------------------
# Tracks slow database queries and optionally sends alerts to Sentry
# This helps identify performance bottlenecks at the SQL level


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Record query start time for duration tracking"""
    conn.info.setdefault('query_start_time', []).append(time.time())


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries (>1 second) with optional Sentry integration"""
    total = time.time() - conn.info['query_start_time'].pop(-1)

    # Log slow queries (>1 second)
    if total > 1.0:
        # Truncate query for readability in logs
        query_preview = statement[:200] + "..." if len(statement) > 200 else statement

        query_logger.warning(
            f"SLOW QUERY ({total:.2f}s): {query_preview}",
            extra={
                "duration_seconds": total,
                "query_full": statement,
                "parameters": str(parameters)[:100]  # Truncate params too
            }
        )

        # Optional: Send to Sentry for alerting
        # Only if SENTRY_DSN is configured
        if os.getenv("SENTRY_DSN"):
            try:
                import sentry_sdk
                sentry_sdk.capture_message(
                    f"Slow database query: {total:.2f}s",
                    level="warning",
                    extras={
                        "query": statement,
                        "duration_seconds": total,
                        "parameters": str(parameters)
                    }
                )
            except ImportError:
                # Sentry not installed, skip
                pass


def db_ping() -> bool:
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1;")
        return True
    except Exception:
        return False


def init_db():
    Base.metadata.create_all(bind=engine)


# Legacy migration function removed - now using Alembic for all database migrations
# See: backend/alembic/ for migration files
# To run migrations: alembic upgrade head


def get_db():
    """Database session dependency for FastAPI endpoints (write operations)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_read_db():
    """
    Database session dependency for read-only operations.
    Uses read replica if configured, otherwise falls back to primary database.

    Usage:
        @router.get("/api/public/games")
        async def get_games(db: Session = Depends(get_read_db)):
            # This will use the read replica if available
            ...
    """
    db = ReadSessionLocal()
    try:
        yield db
    finally:
        db.close()
