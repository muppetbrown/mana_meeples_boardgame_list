from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from config import (
    DATABASE_URL,
    READ_REPLICA_URL,
    DB_POOL_SIZE,
    DB_MAX_OVERFLOW,
    DB_POOL_TIMEOUT,
    DB_POOL_RECYCLE,
    SLOW_QUERY_THRESHOLD_SECONDS,
)
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
# Performance Tuning: Now configurable via environment variables
# Optimized defaults for high concurrency (400+ games, multiple concurrent users)
engine_kwargs = {
    "poolclass": QueuePool,
    "pool_size": DB_POOL_SIZE,  # Permanent connections (configurable, default 15)
    "max_overflow": DB_MAX_OVERFLOW,  # Burst capacity (configurable, default 20)
    "pool_timeout": DB_POOL_TIMEOUT,  # Connection wait timeout (configurable, default 30s)
    "pool_recycle": DB_POOL_RECYCLE,  # Recycle connections (configurable, default 30min)
    "pool_pre_ping": True,  # Test connections before using them (prevents stale connections)
    "echo": False,  # Set to True for SQL debugging
}

logger.info(
    f"Database pool configuration: size={DB_POOL_SIZE}, overflow={DB_MAX_OVERFLOW}, "
    f"timeout={DB_POOL_TIMEOUT}s, recycle={DB_POOL_RECYCLE}s"
)

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

    # Log slow queries (configurable threshold, default 1 second)
    if total > SLOW_QUERY_THRESHOLD_SECONDS:
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


def get_pool_stats():
    """
    Get database connection pool statistics for monitoring.
    
    Performance Tuning: Use this endpoint to monitor pool health and adjust
    DB_POOL_SIZE/DB_MAX_OVERFLOW if you see pool exhaustion warnings.
    
    Returns:
        Dictionary with pool statistics for primary and read replica (if configured)
    """
    stats = {
        "primary": {
            "size": engine.pool.size(),
            "checked_in": engine.pool.checkedin(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "total_connections": engine.pool.size() + engine.pool.overflow(),
            "config": {
                "pool_size": DB_POOL_SIZE,
                "max_overflow": DB_MAX_OVERFLOW,
                "pool_timeout": DB_POOL_TIMEOUT,
                "pool_recycle": DB_POOL_RECYCLE,
            }
        }
    }
    
    # Add read replica stats if configured
    if READ_REPLICA_URL and read_engine != engine:
        stats["read_replica"] = {
            "size": read_engine.pool.size(),
            "checked_in": read_engine.pool.checkedin(),
            "checked_out": read_engine.pool.checkedout(),
            "overflow": read_engine.pool.overflow(),
            "total_connections": read_engine.pool.size() + read_engine.pool.overflow(),
        }
    
    return stats
