from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from config import DATABASE_URL, READ_REPLICA_URL
from models import Base
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

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
