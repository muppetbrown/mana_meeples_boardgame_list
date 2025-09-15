from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from config import DATABASE_URL
from models import Base

# SQLite tuning for FastAPI
connect_args = {}
engine_kwargs = {}

if DATABASE_URL.startswith("sqlite:"):
    connect_args["check_same_thread"] = False
    # StaticPool only for in-memory SQLite, not needed for file-based
    if DATABASE_URL in ("sqlite://", "sqlite:///:memory:"):
        engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True, **engine_kwargs)
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
