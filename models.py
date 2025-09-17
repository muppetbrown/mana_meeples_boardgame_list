from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), index=True, nullable=False)
    categories = Column(Text, default="", nullable=False)
    year = Column(Integer, nullable=True)
    players_min = Column(Integer, nullable=True)
    players_max = Column(Integer, nullable=True)
    playtime_min = Column(Integer, nullable=True)
    playtime_max = Column(Integer, nullable=True)
    thumbnail_url = Column(String(512), nullable=True)
    image = Column(String(512), nullable=True)  # Full-size image URL from BGG
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    bgg_id = Column(Integer, unique=True, nullable=True, index=True)
    thumbnail_file = Column(String(256), nullable=True)
    mana_meeple_category = Column(String(50), nullable=True, index=True) 
    description = Column(Text, nullable=True)
    designers = Column(JSON, nullable=True)  # Store as JSON array
    publishers = Column(JSON, nullable=True)  # Store as JSON array
    mechanics = Column(JSON, nullable=True)  # Store as JSON array
    artists = Column(JSON, nullable=True)  # Store as JSON array
    average_rating = Column(Float, nullable=True)
    complexity = Column(Float, nullable=True)
    bgg_rank = Column(Integer, nullable=True)
    users_rated = Column(Integer, nullable=True)
    min_age = Column(Integer, nullable=True)
    is_cooperative = Column(Boolean, nullable=True)
