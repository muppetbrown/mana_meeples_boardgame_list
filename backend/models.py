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
    Numeric,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

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
    )

    # Relationships
    buy_list_entry = relationship(
        "BuyListGame", back_populates="game", uselist=False, cascade="all, delete-orphan"
    )
    price_snapshots = relationship(
        "PriceSnapshot", back_populates="game", cascade="all, delete-orphan"
    )
    price_offers = relationship(
        "PriceOffer", back_populates="game", cascade="all, delete-orphan"
    )


class BuyListGame(Base):
    """
    Tracks games on the buy list with manual management fields.
    Links to the main Game table via game_id.
    """

    __tablename__ = "buy_list_games"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("boardgames.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    rank = Column(Integer, nullable=True, index=True)  # Determines order in buy list
    bgo_link = Column(Text, nullable=True)  # BoardGameOracle product page URL
    lpg_rrp = Column(Numeric(10, 2), nullable=True)  # Lets Play Games RRP
    lpg_status = Column(String(50), nullable=True, index=True)  # AVAILABLE, BACK_ORDER, NOT_FOUND, BACK_ORDER_OOS
    on_buy_list = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship
    game = relationship("Game", back_populates="buy_list_entry")

    __table_args__ = (
        Index("idx_buy_list_rank", "on_buy_list", "rank"),
        Index("idx_buy_list_status", "lpg_status", "on_buy_list"),
    )


class PriceSnapshot(Base):
    """
    Stores aggregated price data from BoardGameOracle scraping.
    One record per game per scraping run.
    """

    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("boardgames.id", ondelete="CASCADE"), nullable=False, index=True)
    checked_at = Column(DateTime, nullable=False, index=True)  # When prices were scraped
    low_price = Column(Numeric(10, 2), nullable=True)  # Lowest price found
    mean_price = Column(Numeric(10, 2), nullable=True)  # Mean price across offers
    best_price = Column(Numeric(10, 2), nullable=True)  # Best in-stock price
    best_store = Column(Text, nullable=True)  # Store with best price
    discount_pct = Column(Numeric(5, 2), nullable=True)  # Discount percentage vs mean
    delta = Column(Numeric(5, 2), nullable=True)  # Delta vs site disc-mean
    source_file = Column(Text, nullable=True)  # Which JSON/CSV file this came from
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    game = relationship("Game", back_populates="price_snapshots")

    __table_args__ = (
        Index("idx_price_snapshot_game_date", "game_id", "checked_at"),
        Index("idx_price_snapshot_best", "best_price", "discount_pct"),
    )


class PriceOffer(Base):
    """
    Stores individual price offers from different retailers.
    Multiple records per game per scraping run.
    """

    __tablename__ = "price_offers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("boardgames.id", ondelete="CASCADE"), nullable=False, index=True)
    checked_at = Column(DateTime, nullable=False, index=True)  # When this offer was scraped
    store = Column(Text, nullable=True)  # Retailer name
    price_nzd = Column(Numeric(10, 2), nullable=True)  # Price in NZD
    availability = Column(Text, nullable=True)  # Stock status text
    store_link = Column(Text, nullable=True)  # Direct link to product at retailer
    in_stock = Column(Boolean, nullable=True)  # Parsed stock status
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    game = relationship("Game", back_populates="price_offers")

    __table_args__ = (
        Index("idx_price_offer_game_date", "game_id", "checked_at"),
        Index("idx_price_offer_store", "store", "in_stock"),
    )
