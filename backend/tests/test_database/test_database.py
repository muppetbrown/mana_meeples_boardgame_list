"""
Unit tests for database.py

Tests database initialization, connection pooling, and session management.
Migration tests are limited due to PostgreSQL-specific logic that skips in test mode.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from sqlalchemy.exc import OperationalError, DatabaseError
import database
from database import db_ping, init_db, get_db, get_read_db


class TestDbPing:
    """Test database ping functionality"""

    @patch('database.engine')
    def test_db_ping_success(self, mock_engine):
        """Test successful database ping"""
        mock_connection = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        mock_connection.exec_driver_sql.return_value = True

        result = db_ping()

        assert result is True
        mock_connection.exec_driver_sql.assert_called_once_with("SELECT 1;")

    @patch('database.engine')
    def test_db_ping_connection_failure(self, mock_engine):
        """Test database ping with connection failure"""
        mock_engine.connect.side_effect = OperationalError(
            "Connection failed", params=None, orig=None
        )

        result = db_ping()

        assert result is False

    @patch('database.engine')
    def test_db_ping_execution_failure(self, mock_engine):
        """Test database ping with SQL execution failure"""
        mock_connection = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        mock_connection.exec_driver_sql.side_effect = DatabaseError(
            "Query failed", params=None, orig=None
        )

        result = db_ping()

        assert result is False

    @patch('database.engine')
    def test_db_ping_generic_exception(self, mock_engine):
        """Test database ping with generic exception"""
        mock_engine.connect.side_effect = Exception("Unexpected error")

        result = db_ping()

        assert result is False


class TestInitDb:
    """Test database initialization"""

    @patch('database.Base')
    @patch('database.engine')
    def test_init_db_creates_tables(self, mock_engine, mock_base):
        """Test init_db creates all tables"""
        mock_metadata = Mock()
        mock_base.metadata = mock_metadata

        init_db()

        mock_metadata.create_all.assert_called_once_with(bind=mock_engine)

    @patch('database.Base')
    @patch('database.engine')
    def test_init_db_propagates_errors(self, mock_engine, mock_base):
        """Test init_db propagates database errors"""
        mock_metadata = Mock()
        mock_base.metadata = mock_metadata
        mock_metadata.create_all.side_effect = OperationalError(
            "Cannot create tables", params=None, orig=None
        )

        with pytest.raises(OperationalError):
            init_db()


class TestGetDb:
    """Test get_db dependency"""

    @patch('database.SessionLocal')
    def test_get_db_yields_session(self, mock_session_local):
        """Test get_db yields database session"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        # Use the generator
        gen = get_db()
        session = next(gen)

        assert session == mock_session
        mock_session_local.assert_called_once()

    @patch('database.SessionLocal')
    def test_get_db_closes_session(self, mock_session_local):
        """Test get_db closes session after use"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        # Consume the generator
        gen = get_db()
        next(gen)
        try:
            next(gen)
        except StopIteration:
            pass

        mock_session.close.assert_called_once()

    @patch('database.SessionLocal')
    def test_get_db_closes_session_on_exception(self, mock_session_local):
        """Test get_db closes session even if exception occurs"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        gen = get_db()
        next(gen)

        # Simulate exception by calling close on generator
        try:
            gen.close()
        except:
            pass

        # Session should be closed
        mock_session.close.assert_called()


class TestGetReadDb:
    """Test get_read_db dependency"""

    @patch('database.ReadSessionLocal')
    def test_get_read_db_yields_session(self, mock_read_session_local):
        """Test get_read_db yields read session"""
        mock_session = Mock()
        mock_read_session_local.return_value = mock_session

        gen = get_read_db()
        session = next(gen)

        assert session == mock_session
        mock_read_session_local.assert_called_once()

    @patch('database.ReadSessionLocal')
    def test_get_read_db_closes_session(self, mock_read_session_local):
        """Test get_read_db closes session after use"""
        mock_session = Mock()
        mock_read_session_local.return_value = mock_session

        gen = get_read_db()
        next(gen)
        try:
            next(gen)
        except StopIteration:
            pass

        mock_session.close.assert_called_once()

    @patch('database.ReadSessionLocal')
    def test_get_read_db_closes_session_on_exception(self, mock_read_session_local):
        """Test get_read_db closes session even if exception occurs"""
        mock_session = Mock()
        mock_read_session_local.return_value = mock_session

        gen = get_read_db()
        next(gen)

        try:
            gen.close()
        except:
            pass

        mock_session.close.assert_called()


# NOTE: Migration tests removed - now using Alembic for database migrations
# The run_migrations() function has been removed from database.py
# Migration testing is now handled by Alembic's built-in testing tools
# See: backend/alembic/ for migration files
# Run migrations with: alembic upgrade head


class TestDatabaseConfiguration:
    """Test database configuration"""

    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    def test_engine_configured_with_connection_pooling(self):
        """Test engine is configured with proper connection pooling"""
        import importlib
        importlib.reload(database)

        # Should have pool configuration (updated values from performance tuning)
        assert database.engine_kwargs['pool_size'] == 15
        assert database.engine_kwargs['max_overflow'] == 20
        assert database.engine_kwargs['pool_timeout'] == 30
        assert database.engine_kwargs['pool_recycle'] == 1800  # Changed from 3600 to 1800 (30min) for better connection hygiene
        assert database.engine_kwargs['pool_pre_ping'] is True

    @patch.dict('os.environ', {'READ_REPLICA_URL': 'postgresql://read:pass@replica/db'})
    def test_read_replica_configuration(self):
        """Test read replica is configured when URL is provided"""
        import importlib
        importlib.reload(database)

        # Read replica should be configured
        assert database.read_engine is not None
        assert database.ReadSessionLocal is not None


class TestDatabaseIntegration:
    """Integration tests for database module"""

    @patch('database.SessionLocal')
    def test_db_session_context_manager(self, mock_session_local):
        """Test database session works as context manager"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        # Simulate using get_db in context
        gen = get_db()
        with pytest.raises(StopIteration):
            session = next(gen)
            assert session == mock_session
            next(gen)  # Should raise StopIteration

        # Session should be closed
        mock_session.close.assert_called()

    @patch('database.engine')
    def test_ping_and_init_workflow(self, mock_engine):
        """Test typical ping and init workflow"""
        mock_connection = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        mock_connection.exec_driver_sql.return_value = True

        # Ping database
        assert db_ping() is True

        # Initialize database
        with patch('database.Base') as mock_base:
            mock_metadata = Mock()
            mock_base.metadata = mock_metadata
            init_db()
            mock_metadata.create_all.assert_called_once()
