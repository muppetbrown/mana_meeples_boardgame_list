from datetime import datetime, timezone
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
    CheckConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship, backref


def utc_now():
    """
    Return current UTC time using timezone-aware datetime.
    Replaces deprecated datetime.utcnow() for Python 3.12+ compatibility.
    """
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


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
    image = Column(String(512), nullable=True)  # Full-size image URL from BGG (main image field)
    cloudinary_url = Column(String(512), nullable=True)  # Pre-generated Cloudinary CDN URL (cached)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    date_added = Column(
        DateTime, default=utc_now, nullable=True, index=True
    )  # Date game was added to physical collection
    bgg_id = Column(Integer, unique=True, nullable=True, index=True)
    mana_meeple_category = Column(String(50), nullable=True, index=True)
    description = Column(Text, nullable=True)
    designers = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)  # Store as JSONB on PostgreSQL, JSON on SQLite
    publishers = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)  # Store as JSONB on PostgreSQL, JSON on SQLite
    mechanics = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)  # Store as JSONB on PostgreSQL, JSON on SQLite
    artists = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)  # Store as JSONB on PostgreSQL, JSON on SQLite
    average_rating = Column(Float, nullable=True)
    complexity = Column(Float, nullable=True)
    bgg_rank = Column(Integer, nullable=True)
    users_rated = Column(Integer, nullable=True)
    min_age = Column(Integer, nullable=True)
    is_cooperative = Column(Boolean, nullable=True)
    nz_designer = Column(Boolean, nullable=True, default=False, index=True)
    # Admin-curated exclusions from the mobile library's quick-pick shortlists
    # (e.g. ["first", "kids"]). Auto-selection logic still runs; this only
    # removes specific games staff have flagged as a bad fit (e.g. mature
    # content the BGG data can't signal). Keys: first, kids, group, coop.
    excluded_quick_picks = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    game_type = Column(String(255), nullable=True, index=True)
    # Ownership status: OWNED (in physical collection), BUY_LIST (want to buy), WISHLIST (maybe buy)
    status = Column(String(20), nullable=True, default="OWNED", index=True)

    # Sleeve information
    has_sleeves = Column(String(20), nullable=True)  # Values: 'found' (sleeve data exists), 'none' (no sleeves required), 'not_found'/'check'/NULL (needs investigation), 'error', 'manual'
    is_sleeved = Column(Boolean, nullable=True, default=False, index=True)  # Whether the entire game is already sleeved

    # AfterGame integration
    aftergame_game_id = Column(String(36), nullable=True, index=True)  # UUID for AfterGame platform game ID

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
        # Existing indexes
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

        # Sprint 4 Performance Indexes - for filtered queries
        # Recently added filter (date_added DESC with status)
        Index("idx_date_added_status", "date_added", "status", postgresql_where=text("status = 'OWNED'")),

        # NZ designer + category combination filter
        Index("idx_nz_designer_category", "nz_designer", "mana_meeple_category",
              postgresql_where=text("nz_designer = true")),

        # Player count range queries (for filtering by player count)
        Index("idx_player_range", "players_min", "players_max",
              postgresql_where=text("status = 'OWNED'")),

        # Complex filtering (category + year + rating for sorting)
        Index("idx_category_year_rating", "mana_meeple_category", "year", "average_rating",
              postgresql_where=text("status = 'OWNED'")),

        # Phase 1 Performance Indexes - for query optimization
        # Category filter with rating sort (most common query pattern)
        Index("idx_category_rating_date",
              "mana_meeple_category", "average_rating", "date_added",
              postgresql_where=text("status = 'OWNED'")),

        # Status + date + NZ designer composite index
        Index("idx_status_date_nz", "status", "date_added", "nz_designer"),

        # GIN index for JSON designer searches (enables fast containment queries)
        Index("idx_designers_gin",
              "designers",
              postgresql_using='gin',
              postgresql_ops={'designers': 'jsonb_path_ops'}),

        # GIN index for JSON mechanics searches
        Index("idx_mechanics_gin",
              "mechanics",
              postgresql_using='gin',
              postgresql_ops={'mechanics': 'jsonb_path_ops'}),

        # Covering index for public queries (reduces table lookups)
        Index("idx_public_games_covering",
              "status", "is_expansion", "expansion_type", "mana_meeple_category",
              postgresql_include=["title", "year", "players_min", "players_max",
                                 "average_rating", "image"]),

        # Sprint 4 Data Integrity Constraints
        # NOTE: All constraints must allow NULL values since fields are nullable
        CheckConstraint("year IS NULL OR (year >= 1900 AND year <= 2100)", name="valid_year"),
        CheckConstraint("players_min IS NULL OR players_min >= 1", name="valid_min_players"),
        CheckConstraint("players_max IS NULL OR players_min IS NULL OR players_max >= players_min", name="players_max_gte_min"),
        CheckConstraint("average_rating IS NULL OR (average_rating >= 0 AND average_rating <= 10)", name="valid_rating"),
        CheckConstraint("complexity IS NULL OR (complexity >= 1 AND complexity <= 5)", name="valid_complexity"),
        CheckConstraint(
            "status IS NULL OR status IN ('OWNED', 'BUY_LIST', 'WISHLIST')",
            name="valid_status"
        ),
        CheckConstraint("playtime_min IS NULL OR playtime_min > 0", name="valid_playtime_min"),
        CheckConstraint("playtime_max IS NULL OR playtime_min IS NULL OR playtime_max >= playtime_min", name="playtime_max_gte_min"),
        CheckConstraint("min_age IS NULL OR (min_age >= 0 AND min_age <= 100)", name="valid_min_age"),
    )

    # Relationships
    buy_list_entry = relationship(
        "BuyListGame", back_populates="game", uselist=False, cascade="all, delete-orphan"
    )
    sleeves = relationship(
        "Sleeve", back_populates="game", cascade="all, delete-orphan"
    )


class BuyListGame(Base):
    """
    Tracks games flagged as candidates to add to the collection, with a
    priority rank and freeform curation notes (e.g. why it fills a gap).
    Links to the main Game table via game_id.
    """

    __tablename__ = "buy_list_games"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("boardgames.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    rank = Column(Integer, nullable=True, index=True)  # Determines order in the recommendations list
    notes = Column(Text, nullable=True)  # Admin curation notes (e.g. why this fills a gap)
    on_buy_list = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationship
    game = relationship("Game", back_populates="buy_list_entry")

    __table_args__ = (
        Index("idx_buy_list_rank", "on_buy_list", "rank"),
    )


class SleeveProduct(Base):
    """
    Sleeve product inventory - tracks available sleeve products from distributors.
    Used for matching game sleeve requirements to purchasable products.
    """

    __tablename__ = "sleeve_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    distributor = Column(String(200), nullable=False)
    item_id = Column(String(100), nullable=True)  # Distributor SKU
    name = Column(String(300), nullable=False)  # Product name
    width_mm = Column(Numeric(6, 2), nullable=False)  # Sleeve inner width
    height_mm = Column(Numeric(6, 2), nullable=False)  # Sleeve inner height
    sleeves_per_pack = Column(Integer, nullable=False)  # Sleeves in one pack
    price = Column(Numeric(10, 2), nullable=False)  # Price per pack
    in_stock = Column(Integer, nullable=False, default=0)  # Individual sleeves in stock
    ordered = Column(Integer, nullable=False, default=0)  # Packs on order

    # Relationships
    matched_sleeves = relationship("Sleeve", back_populates="matched_product")

    __table_args__ = (
        Index("idx_sleeve_product_size", "width_mm", "height_mm"),
        Index("idx_sleeve_product_distributor", "distributor"),
        CheckConstraint("in_stock >= 0", name="valid_product_stock"),
        CheckConstraint("ordered >= 0", name="valid_product_ordered"),
        CheckConstraint("sleeves_per_pack > 0", name="valid_pack_size"),
        CheckConstraint("price > 0", name="valid_product_price"),
    )

    def __repr__(self):
        return f"<SleeveProduct {self.name} {self.width_mm}x{self.height_mm}>"


class Sleeve(Base):
    """
    Stores sleeve/card protector requirements for games.
    Multiple records per game for different card types/sizes.
    """

    __tablename__ = "sleeves"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    game_id = Column(Integer, ForeignKey("boardgames.id", ondelete="CASCADE"), nullable=False, index=True)
    card_name = Column(String(200), nullable=True)  # e.g., "Age Cards", "Player Cards"
    width_mm = Column(Numeric(6, 2), nullable=False)  # Card width, decimals allowed (e.g. 63.5)
    height_mm = Column(Numeric(6, 2), nullable=False)  # Card height, decimals allowed (e.g. 88.9)
    quantity = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)  # Special notes about this card type
    is_sleeved = Column(Boolean, nullable=False, default=False)  # Whether this specific sleeve type is already sleeved
    matched_product_id = Column(Integer, ForeignKey("sleeve_products.id", ondelete="SET NULL"), nullable=True, index=True)

    # Relationships
    game = relationship("Game", back_populates="sleeves")
    matched_product = relationship("SleeveProduct", back_populates="matched_sleeves")

    __table_args__ = (
        Index("idx_sleeve_game", "game_id"),
        Index("idx_sleeve_size", "width_mm", "height_mm"),
        Index("idx_sleeve_sleeved", "is_sleeved"),
    )

    def __repr__(self):
        return f"<Sleeve {self.width_mm}x{self.height_mm} qty={self.quantity} for game_id={self.game_id}>"


class BackgroundTaskFailure(Base):
    """
    Tracks background task failures for monitoring and debugging.
    Helps identify systematic issues with async operations.
    Sprint 5: Error Handling & Monitoring
    """

    __tablename__ = "background_task_failures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(String(100), nullable=False, index=True)  # e.g., "thumbnail_download", "bgg_import"
    game_id = Column(Integer, ForeignKey("boardgames.id", ondelete="SET NULL"), nullable=True, index=True)
    error_message = Column(Text, nullable=False)
    error_type = Column(String(200), nullable=True)  # Exception class name
    stack_trace = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    url = Column(String(512), nullable=True)  # Associated URL if applicable
    resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    __table_args__ = (
        Index("idx_task_failure_type_date", "task_type", "created_at"),
        Index("idx_task_failure_resolved", "resolved", "created_at"),
        Index("idx_task_failure_game", "game_id", "task_type"),
    )
