from datetime import datetime
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text

Base = declarative_base()

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), index=True, nullable=False)
    # For v1 keep it simple: comma-separated categories
    categories = Column(Text, default="", nullable=False)
    year = Column(Integer, nullable=True)
    players_min = Column(Integer, nullable=True)
    players_max = Column(Integer, nullable=True)
    playtime_min = Column(Integer, nullable=True)
    playtime_max = Column(Integer, nullable=True)
    thumbnail_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    bgg_id = Column(Integer, unique=True, nullable=True, index=True)
    thumbnail_file = Column(String(256), nullable=True)
