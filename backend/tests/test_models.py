"""
Comprehensive test suite for models module

Tests cover:
- Model creation and field assignments
- Relationships between models
- Database constraints and validation
- Indexes and table structure
- Check constraints
- Cascade deletion behavior
- Model repr methods
- Default values and auto-generated fields
"""
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from decimal import Decimal

from models import (
    Base,
    Game,
    BuyListGame,
    PriceSnapshot,
    PriceOffer,
    Sleeve,
    BackgroundTaskFailure,
)


@pytest.fixture
def engine():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a database session for testing"""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestGameModel:
    """Test Game model (boardgames table)"""

    def test_game_creation_minimal(self, session):
        """Test creating a game with minimal required fields"""
        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        assert game.id is not None
        assert game.title == "Test Game"
        assert game.created_at is not None

    def test_game_creation_all_fields(self, session):
        """Test creating a game with all fields"""
        game = Game(
            title="Gloomhaven",
            categories="Strategy, Fantasy",
            year=2017,
            players_min=1,
            players_max=4,
            playtime_min=60,
            playtime_max=120,
            image="https://example.com/image.jpg",
            bgg_id=174430,
            mana_meeple_category="CORE_STRATEGY",
            description="A tactical combat game",
            designers=["Isaac Childres"],
            publishers=["Cephalofair Games"],
            mechanics=["Hand Management", "Cooperative"],
            artists=["Isaac Childres"],
            average_rating=8.7,
            complexity=3.8,
            bgg_rank=1,
            users_rated=50000,
            min_age=14,
            is_cooperative=True,
            nz_designer=False,
            game_type="board_game",
            status="OWNED",
            has_sleeves="found",
            is_sleeved=True,
            is_expansion=False,
        )
        session.add(game)
        session.commit()

        assert game.id is not None
        assert game.title == "Gloomhaven"
        assert game.year == 2017
        assert game.bgg_id == 174430
        assert game.average_rating == 8.7
        assert game.complexity == 3.8
        assert game.designers == ["Isaac Childres"]

    def test_game_bgg_id_unique(self, session):
        """Test BGG ID must be unique"""
        game1 = Game(title="Game 1", bgg_id=12345)
        game2 = Game(title="Game 2", bgg_id=12345)

        session.add(game1)
        session.commit()

        session.add(game2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_game_defaults(self, session):
        """Test default values for Game model"""
        game = Game(title="Test")
        session.add(game)
        session.commit()

        assert game.categories == ""
        assert game.status == "OWNED"
        assert game.nz_designer is None or game.nz_designer is False
        assert game.is_expansion is False
        assert game.created_at is not None

    def test_game_expansion_relationship(self, session):
        """Test expansion relationship between games"""
        base_game = Game(title="Base Game", bgg_id=1000)
        session.add(base_game)
        session.commit()

        expansion = Game(
            title="Expansion",
            bgg_id=2000,
            is_expansion=True,
            base_game_id=base_game.id,
            expansion_type="requires_base",
        )
        session.add(expansion)
        session.commit()

        # Test relationship
        assert expansion.base_game_id == base_game.id
        assert expansion.base_game == base_game
        assert expansion in base_game.expansions

    def test_game_json_fields(self, session):
        """Test JSON fields store arrays correctly"""
        game = Game(
            title="Test",
            designers=["Designer 1", "Designer 2"],
            publishers=["Publisher A", "Publisher B"],
            mechanics=["Deck Building", "Worker Placement"],
            artists=["Artist X"],
        )
        session.add(game)
        session.commit()

        # Reload from database
        loaded_game = session.query(Game).filter_by(id=game.id).first()
        assert loaded_game.designers == ["Designer 1", "Designer 2"]
        assert loaded_game.publishers == ["Publisher A", "Publisher B"]
        assert loaded_game.mechanics == ["Deck Building", "Worker Placement"]
        assert loaded_game.artists == ["Artist X"]


class TestBuyListGameModel:
    """Test BuyListGame model"""

    def test_buy_list_game_creation(self, session):
        """Test creating a buy list entry"""
        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        buy_list_entry = BuyListGame(
            game_id=game.id,
            rank=1,
            bgo_link="https://boardgameoracle.com/game/123",
            lpg_rrp=Decimal("150.00"),
            lpg_status="AVAILABLE",
            on_buy_list=True,
        )
        session.add(buy_list_entry)
        session.commit()

        assert buy_list_entry.id is not None
        assert buy_list_entry.game_id == game.id
        assert buy_list_entry.rank == 1
        assert buy_list_entry.lpg_rrp == Decimal("150.00")
        assert buy_list_entry.on_buy_list is True

    def test_buy_list_game_relationship(self, session):
        """Test relationship between Game and BuyListGame"""
        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        buy_list_entry = BuyListGame(game_id=game.id, on_buy_list=True)
        session.add(buy_list_entry)
        session.commit()

        # Test bidirectional relationship
        assert game.buy_list_entry == buy_list_entry
        assert buy_list_entry.game == game

    def test_buy_list_game_unique_constraint(self, session):
        """Test game_id must be unique in buy list"""
        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        buy_list1 = BuyListGame(game_id=game.id, on_buy_list=True)
        session.add(buy_list1)
        session.commit()

        buy_list2 = BuyListGame(game_id=game.id, on_buy_list=True)
        session.add(buy_list2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_buy_list_game_defaults(self, session):
        """Test default values for BuyListGame"""
        game = Game(title="Test")
        session.add(game)
        session.commit()

        buy_list_entry = BuyListGame(game_id=game.id)
        session.add(buy_list_entry)
        session.commit()

        assert buy_list_entry.on_buy_list is True
        assert buy_list_entry.created_at is not None
        assert buy_list_entry.updated_at is not None

    def test_buy_list_cascade_delete(self, session):
        """Test cascade deletion from Game to BuyListGame"""
        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        buy_list_entry = BuyListGame(game_id=game.id, on_buy_list=True)
        session.add(buy_list_entry)
        session.commit()

        # Delete the game
        session.delete(game)
        session.commit()

        # BuyListGame should be deleted too
        assert session.query(BuyListGame).filter_by(id=buy_list_entry.id).first() is None


class TestPriceSnapshotModel:
    """Test PriceSnapshot model"""

    def test_price_snapshot_creation(self, session):
        """Test creating a price snapshot"""
        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        snapshot = PriceSnapshot(
            game_id=game.id,
            checked_at=datetime.now(timezone.utc),
            low_price=Decimal("89.99"),
            mean_price=Decimal("95.00"),
            best_price=Decimal("85.00"),
            best_store="Game Store",
            discount_pct=Decimal("10.53"),
            delta=Decimal("2.5"),
        )
        session.add(snapshot)
        session.commit()

        assert snapshot.id is not None
        assert snapshot.game_id == game.id
        assert snapshot.low_price == Decimal("89.99")
        assert snapshot.best_store == "Game Store"

    def test_price_snapshot_relationship(self, session):
        """Test relationship between Game and PriceSnapshot"""
        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        snapshot1 = PriceSnapshot(game_id=game.id, checked_at=datetime.now(timezone.utc))
        snapshot2 = PriceSnapshot(game_id=game.id, checked_at=datetime.now(timezone.utc))
        session.add_all([snapshot1, snapshot2])
        session.commit()

        # Test one-to-many relationship
        assert len(game.price_snapshots) == 2
        assert snapshot1 in game.price_snapshots
        assert snapshot2 in game.price_snapshots

    def test_price_snapshot_cascade_delete(self, session):
        """Test cascade deletion from Game to PriceSnapshot"""
        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        snapshot = PriceSnapshot(game_id=game.id, checked_at=datetime.now(timezone.utc))
        session.add(snapshot)
        session.commit()

        snapshot_id = snapshot.id

        # Delete the game
        session.delete(game)
        session.commit()

        # Snapshot should be deleted too
        assert session.query(PriceSnapshot).filter_by(id=snapshot_id).first() is None


class TestPriceOfferModel:
    """Test PriceOffer model"""

    def test_price_offer_creation(self, session):
        """Test creating a price offer"""
        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        offer = PriceOffer(
            game_id=game.id,
            checked_at=datetime.now(timezone.utc),
            store="Game Store",
            price_nzd=Decimal("99.99"),
            availability="In Stock",
            store_link="https://store.com/game",
            in_stock=True,
        )
        session.add(offer)
        session.commit()

        assert offer.id is not None
        assert offer.game_id == game.id
        assert offer.store == "Game Store"
        assert offer.price_nzd == Decimal("99.99")
        assert offer.in_stock is True

    def test_price_offer_relationship(self, session):
        """Test relationship between Game and PriceOffer"""
        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        offer1 = PriceOffer(
            game_id=game.id, checked_at=datetime.now(timezone.utc), store="Store A"
        )
        offer2 = PriceOffer(
            game_id=game.id, checked_at=datetime.now(timezone.utc), store="Store B"
        )
        session.add_all([offer1, offer2])
        session.commit()

        # Test one-to-many relationship
        assert len(game.price_offers) == 2
        assert offer1 in game.price_offers
        assert offer2 in game.price_offers

    def test_price_offer_cascade_delete(self, session):
        """Test cascade deletion from Game to PriceOffer"""
        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        offer = PriceOffer(game_id=game.id, checked_at=datetime.now(timezone.utc))
        session.add(offer)
        session.commit()

        offer_id = offer.id

        # Delete the game
        session.delete(game)
        session.commit()

        # Offer should be deleted too
        assert session.query(PriceOffer).filter_by(id=offer_id).first() is None


class TestSleeveModel:
    """Test Sleeve model"""

    def test_sleeve_creation(self, session):
        """Test creating a sleeve entry"""
        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        sleeve = Sleeve(
            game_id=game.id,
            card_name="Player Cards",
            width_mm=63,
            height_mm=88,
            quantity=100,
            notes="Standard card size",
        )
        session.add(sleeve)
        session.commit()

        assert sleeve.id is not None
        assert sleeve.game_id == game.id
        assert sleeve.card_name == "Player Cards"
        assert sleeve.width_mm == 63
        assert sleeve.height_mm == 88
        assert sleeve.quantity == 100

    def test_sleeve_repr(self, session):
        """Test Sleeve __repr__ method"""
        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        sleeve = Sleeve(
            game_id=game.id, width_mm=63, height_mm=88, quantity=100
        )
        session.add(sleeve)
        session.commit()

        repr_str = repr(sleeve)
        assert "63x88" in repr_str
        assert "qty=100" in repr_str
        assert f"game_id={game.id}" in repr_str

    def test_sleeve_relationship(self, session):
        """Test relationship between Game and Sleeve"""
        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        sleeve1 = Sleeve(game_id=game.id, width_mm=63, height_mm=88, quantity=50)
        sleeve2 = Sleeve(game_id=game.id, width_mm=70, height_mm=120, quantity=30)
        session.add_all([sleeve1, sleeve2])
        session.commit()

        # Test one-to-many relationship
        assert len(game.sleeves) == 2
        assert sleeve1 in game.sleeves
        assert sleeve2 in game.sleeves

    def test_sleeve_cascade_delete(self, session):
        """Test cascade deletion from Game to Sleeve"""
        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        sleeve = Sleeve(game_id=game.id, width_mm=63, height_mm=88, quantity=100)
        session.add(sleeve)
        session.commit()

        sleeve_id = sleeve.id

        # Delete the game
        session.delete(game)
        session.commit()

        # Sleeve should be deleted too
        assert session.query(Sleeve).filter_by(id=sleeve_id).first() is None


class TestBackgroundTaskFailureModel:
    """Test BackgroundTaskFailure model"""

    def test_task_failure_creation(self, session):
        """Test creating a background task failure"""
        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        failure = BackgroundTaskFailure(
            task_type="thumbnail_download",
            game_id=game.id,
            error_message="Failed to download thumbnail",
            error_type="HTTPError",
            stack_trace="Traceback...",
            retry_count=2,
            url="https://example.com/thumb.jpg",
            resolved=False,
        )
        session.add(failure)
        session.commit()

        assert failure.id is not None
        assert failure.task_type == "thumbnail_download"
        assert failure.game_id == game.id
        assert failure.error_message == "Failed to download thumbnail"
        assert failure.retry_count == 2
        assert failure.resolved is False

    def test_task_failure_defaults(self, session):
        """Test default values for BackgroundTaskFailure"""
        failure = BackgroundTaskFailure(
            task_type="test_task", error_message="Test error"
        )
        session.add(failure)
        session.commit()

        assert failure.retry_count == 0
        assert failure.resolved is False
        assert failure.created_at is not None

    def test_task_failure_game_nullable(self, session):
        """Test game_id can be null for task failures"""
        failure = BackgroundTaskFailure(
            task_type="general_task",
            game_id=None,
            error_message="General error",
        )
        session.add(failure)
        session.commit()

        assert failure.game_id is None

    def test_task_failure_game_set_null_on_delete(self, session):
        """Test game_id is set to NULL when game is deleted (PostgreSQL only)"""
        # Skip this test for SQLite as it requires pragma foreign_keys=on
        # and additional configuration. This behavior is properly enforced in PostgreSQL.
        import sqlite3
        if isinstance(session.bind.dialect.dbapi, type(sqlite3)):
            pytest.skip("SQLite in-memory db doesn't enforce ON DELETE SET NULL properly")

        game = Game(title="Test Game")
        session.add(game)
        session.commit()

        failure = BackgroundTaskFailure(
            task_type="test_task",
            game_id=game.id,
            error_message="Test error",
        )
        session.add(failure)
        session.commit()

        # Delete the game
        session.delete(game)
        session.commit()

        # Failure should still exist but game_id should be NULL
        loaded_failure = session.query(BackgroundTaskFailure).filter_by(
            id=failure.id
        ).first()
        assert loaded_failure is not None
        assert loaded_failure.game_id is None

    def test_task_failure_resolved_tracking(self, session):
        """Test tracking resolved task failures"""
        failure = BackgroundTaskFailure(
            task_type="test_task",
            error_message="Test error",
            resolved=False,
        )
        session.add(failure)
        session.commit()

        # Mark as resolved
        failure.resolved = True
        failure.resolved_at = datetime.now(timezone.utc)
        session.commit()

        loaded = session.query(BackgroundTaskFailure).filter_by(id=failure.id).first()
        assert loaded.resolved is True
        assert loaded.resolved_at is not None


class TestModelConstraints:
    """Test database constraints on models"""

    def test_game_title_not_null(self, session):
        """Test title is required for Game"""
        game = Game()  # Missing required title
        session.add(game)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_buy_list_game_id_not_null(self, session):
        """Test game_id is required for BuyListGame"""
        buy_list = BuyListGame(on_buy_list=True)  # Missing required game_id
        session.add(buy_list)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_price_snapshot_game_id_not_null(self, session):
        """Test game_id is required for PriceSnapshot"""
        snapshot = PriceSnapshot(checked_at=datetime.now(timezone.utc))  # Missing game_id
        session.add(snapshot)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_sleeve_required_fields(self, session):
        """Test required fields for Sleeve model"""
        game = Game(title="Test")
        session.add(game)
        session.commit()

        # Missing width_mm
        sleeve = Sleeve(game_id=game.id, height_mm=88, quantity=100)
        session.add(sleeve)

        with pytest.raises(IntegrityError):
            session.commit()


class TestModelIndexes:
    """Test that indexes are properly defined"""

    def test_game_indexes_exist(self):
        """Test Game model has expected indexes"""
        indexes = {idx.name for idx in Game.__table__.indexes}

        # Check for some key indexes
        assert "idx_year_category" in indexes
        assert "idx_players_playtime" in indexes
        assert "idx_rating_rank" in indexes

    def test_buy_list_indexes_exist(self):
        """Test BuyListGame model has expected indexes"""
        indexes = {idx.name for idx in BuyListGame.__table__.indexes}

        assert "idx_buy_list_rank" in indexes
        assert "idx_buy_list_status" in indexes

    def test_price_snapshot_indexes_exist(self):
        """Test PriceSnapshot model has expected indexes"""
        indexes = {idx.name for idx in PriceSnapshot.__table__.indexes}

        assert "idx_price_snapshot_game_date" in indexes
        assert "idx_price_snapshot_best" in indexes

    def test_sleeve_indexes_exist(self):
        """Test Sleeve model has expected indexes"""
        indexes = {idx.name for idx in Sleeve.__table__.indexes}

        assert "idx_sleeve_game" in indexes
        assert "idx_sleeve_size" in indexes


class TestModelTableNames:
    """Test that table names are correctly defined"""

    def test_table_names(self):
        """Test all models have correct table names"""
        assert Game.__tablename__ == "boardgames"
        assert BuyListGame.__tablename__ == "buy_list_games"
        assert PriceSnapshot.__tablename__ == "price_snapshots"
        assert PriceOffer.__tablename__ == "price_offers"
        assert Sleeve.__tablename__ == "sleeves"
        assert BackgroundTaskFailure.__tablename__ == "background_task_failures"
