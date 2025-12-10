from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    JSON,
    Float,
    Boolean,
    Index,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref

Base = declarative_base()


class Game(Base):
    __tablename__ = "boardgames"

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
    date_added = Column(
        DateTime, default=datetime.utcnow, nullable=True, index=True
    )  # Date game was added to physical collection
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
    nz_designer = Column(Boolean, nullable=True, default=False, index=True)
    game_type = Column(String(255), nullable=True, index=True)

    # Expansion relationship fields
    is_expansion = Column(Boolean, default=False, nullable=False, index=True)
    base_game_id = Column(
        Integer, ForeignKey("boardgames.id"), nullable=True, index=True
    )
    expansion_type = Column(
        String(50), nullable=True
    )  # 'requires_base', 'standalone', 'both'

    # Player count modifications (for expansions that change player counts)
    modifies_players_min = Column(Integer, nullable=True)
    modifies_players_max = Column(Integer, nullable=True)

    # Relationships
    expansions = relationship(
        "Game",
        backref=backref("base_game", remote_side=[id]),
        foreign_keys=[base_game_id],
    )

    # Performance indexes for common queries
    __table_args__ = (
        Index("idx_year_category", "year", "mana_meeple_category"),
        Index(
            "idx_players_playtime",
            "players_min",
            "players_max",
            "playtime_min",
            "playtime_max",
        ),
        Index("idx_rating_rank", "average_rating", "bgg_rank"),
        Index("idx_created_category", "created_at", "mana_meeple_category"),
        Index("idx_expansion_lookup", "is_expansion", "base_game_id"),
    )
