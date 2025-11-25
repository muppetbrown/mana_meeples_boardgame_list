from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from config import DATABASE_URL
from models import Base
import logging

logger = logging.getLogger(__name__)

# PostgreSQL connection pooling configuration
engine_kwargs = {
    "poolclass": QueuePool,
    "pool_size": 5,          # Number of permanent connections
    "max_overflow": 10,      # Additional connections when pool is full
    "pool_timeout": 30,      # Seconds to wait for connection from pool
    "pool_recycle": 3600,    # Recycle connections after 1 hour
    "pool_pre_ping": True,   # Test connections before using them
    "echo": False,           # Set to True for SQL debugging
}

logger.info(f"Configuring database engine for: {DATABASE_URL.split('@')[0]}@...")
engine = create_engine(DATABASE_URL, future=True, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

def db_ping() -> bool:
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1;")
        return True
    except Exception:
        return False

def init_db():
    Base.metadata.create_all(bind=engine)
