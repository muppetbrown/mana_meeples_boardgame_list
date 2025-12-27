"""
Unit tests for database.py

Tests database initialization, connection pooling, and session management.
Migration tests are limited due to PostgreSQL-specific logic that skips in test mode.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from sqlalchemy.exc import OperationalError, DatabaseError
import database
from database import db_ping, init_db, get_db, get_read_db, run_migrations


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


class TestRunMigrations:
    """Test database migrations"""

    @patch('database.DATABASE_URL', 'sqlite:///test.db')
    @patch('database.engine')
    def test_run_migrations_skips_for_sqlite(self, mock_engine):
        """Test run_migrations skips for SQLite databases"""
        # Should not attempt any migrations for SQLite
        run_migrations()

        # Engine should not be used for SQLite
        mock_engine.connect.assert_not_called()

    @patch('database.logger')
    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    @patch('database.engine')
    def test_run_migrations_logs_execution(self, mock_engine, mock_logger):
        """Test migration execution is logged"""
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Simulate all migrations already complete
        mock_result = Mock()
        mock_result.fetchone.return_value = ('column',)  # Column exists
        mock_result.scalar.return_value = 0
        mock_result.rowcount = 0
        mock_conn.execute.return_value = mock_result

        run_migrations()

        # Should log migration start and completion
        assert any(
            'Running database migrations' in str(call)
            for call in mock_logger.info.call_args_list
        )
        assert any(
            'Database migrations completed' in str(call)
            for call in mock_logger.info.call_args_list
        )

    @patch('database.logger')
    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    @patch('database.engine')
    def test_run_migrations_commits_changes(self, mock_engine, mock_logger):
        """Test migrations commit changes"""
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Simulate all migrations already complete
        mock_result = Mock()
        mock_result.fetchone.return_value = ('column',)
        mock_result.scalar.return_value = 0
        mock_result.rowcount = 0
        mock_conn.execute.return_value = mock_result

        run_migrations()

        # Should commit changes
        assert mock_conn.commit.called

    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    @patch('database.engine')
    def test_run_migrations_rollback_on_error(self, mock_engine):
        """Test migrations rollback on error"""
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Simulate error during migration
        mock_conn.execute.side_effect = DatabaseError(
            "Migration failed", params=None, orig=None
        )

        with pytest.raises(DatabaseError):
            run_migrations()

        # Should rollback on error
        assert mock_conn.rollback.called



class TestDatabaseConfiguration:
    """Test database configuration"""

    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    def test_engine_configured_with_connection_pooling(self):
        """Test engine is configured with proper connection pooling"""
        import importlib
        importlib.reload(database)

        # Should have pool configuration
        assert database.engine_kwargs['pool_size'] == 15
        assert database.engine_kwargs['max_overflow'] == 20
        assert database.engine_kwargs['pool_timeout'] == 30
        assert database.engine_kwargs['pool_recycle'] == 3600
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


class TestDatabaseMigrations:
    """Test database migration scenarios"""

    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    @patch('database.engine')
    @patch('database.logger')
    def test_migration_adds_date_added_column(self, mock_logger, mock_engine):
        """Test migration adds date_added column when it doesn't exist"""
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        queries_executed = []

        def side_effect_func(*args, **kwargs):
            query = str(args[0])
            queries_executed.append(query)
            result = Mock()

            # date_added doesn't exist initially
            if 'date_added' in query and 'column_name' in query:
                result.fetchone.return_value = None
            # Other columns exist
            elif 'column_name' in query:
                result.fetchone.return_value = ('col',)
            # Tables exist
            elif 'table_name' in query:
                result.fetchone.return_value = ('table',)
            elif 'constraint_name' in query or 'indexname' in query:
                result.fetchone.return_value = ('exists',)
            else:
                result.fetchone.return_value = None

            result.scalar.return_value = 0
            result.rowcount = 0
            return result

        mock_conn.execute.side_effect = side_effect_func

        run_migrations()

        # Verify ALTER TABLE was called
        assert any('ADD COLUMN date_added' in q for q in queries_executed)

    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    @patch('database.engine')
    @patch('database.logger')
    def test_migration_updates_null_date_added(self, mock_logger, mock_engine):
        """Test migration updates NULL date_added values"""
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        queries_executed = []
        update_call_count = [0]

        def side_effect_func(*args, **kwargs):
            query = str(args[0])
            queries_executed.append(query)
            result = Mock()

            # All columns exist
            if 'column_name' in query:
                result.fetchone.return_value = ('col',)
            # Tables exist
            elif 'table_name' in query:
                result.fetchone.return_value = ('table',)
            # First UPDATE returns 5 rows updated
            elif 'UPDATE boardgames' in query and 'date_added' in query:
                update_call_count[0] += 1
                if update_call_count[0] == 1:
                    result.rowcount = 5
                else:
                    result.rowcount = 0
            elif 'constraint_name' in query or 'indexname' in query:
                result.fetchone.return_value = ('exists',)
            else:
                result.fetchone.return_value = None

            result.scalar.return_value = 0
            if 'rowcount' not in dir(result):
                result.rowcount = 0
            return result

        mock_conn.execute.side_effect = side_effect_func

        run_migrations()

        # Verify UPDATE was executed
        assert any('UPDATE boardgames' in q and 'date_added' in q for q in queries_executed)

    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    @patch('database.engine')
    @patch('database.logger')
    def test_migration_adds_status_column(self, mock_logger, mock_engine):
        """Test migration adds status column when it doesn't exist"""
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        queries_executed = []

        # Simulate date_added exists but status doesn't
        def side_effect_func(*args, **kwargs):
            query = str(args[0])
            queries_executed.append(query)
            result = Mock()

            # date_added, is_sleeved, aftergame exist
            if ('date_added' in query or 'is_sleeved' in query or 'aftergame' in query) and 'column_name' in query:
                result.fetchone.return_value = ('col',)
            # status doesn't exist
            elif 'status' in query and 'column_name' in query:
                result.fetchone.return_value = None
            # Tables exist
            elif 'table_name' in query:
                result.fetchone.return_value = ('table',)
            elif 'constraint_name' in query or 'indexname' in query:
                result.fetchone.return_value = ('exists',)
            else:
                result.fetchone.return_value = None

            result.rowcount = 0
            result.scalar.return_value = 0
            return result

        mock_conn.execute.side_effect = side_effect_func

        run_migrations()

        # Verify status column was added
        assert any('status' in q and 'ADD COLUMN' in q for q in queries_executed)

    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    @patch('database.engine')
    @patch('database.logger')
    def test_migration_creates_sleeves_table(self, mock_logger, mock_engine):
        """Test migration creates sleeves table when it doesn't exist"""
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Track queries
        queries_executed = []

        def side_effect_func(*args, **kwargs):
            query = str(args[0])
            queries_executed.append(query)
            result = Mock()

            # Columns exist
            if 'column_name' in query:
                result.fetchone.return_value = ('col',)
            # Tables don't exist
            elif 'table_name' in query and 'sleeves' in query:
                result.fetchone.return_value = None
            elif 'table_name' in query:
                result.fetchone.return_value = None
            # Constraints and indexes don't exist
            elif 'constraint_name' in query or 'indexname' in query:
                result.fetchone.return_value = None
            else:
                result.fetchone.return_value = None

            result.rowcount = 0
            result.scalar.return_value = 0
            return result

        mock_conn.execute.side_effect = side_effect_func

        run_migrations()

        # Verify sleeves table was created
        assert any('CREATE TABLE sleeves' in q for q in queries_executed)

    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    @patch('database.engine')
    @patch('database.logger')
    def test_migration_creates_buy_list_table(self, mock_logger, mock_engine):
        """Test migration creates buy_list_games table"""
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        queries_executed = []

        def side_effect_func(*args, **kwargs):
            query = str(args[0])
            queries_executed.append(query)
            result = Mock()

            if 'column_name' in query:
                result.fetchone.return_value = ('col',)
            elif 'table_name' in query:
                result.fetchone.return_value = None
            elif 'constraint_name' in query or 'indexname' in query:
                result.fetchone.return_value = None
            else:
                result.fetchone.return_value = None

            result.rowcount = 0
            result.scalar.return_value = 0
            return result

        mock_conn.execute.side_effect = side_effect_func

        run_migrations()

        # Verify buy_list_games table was created
        assert any('CREATE TABLE buy_list_games' in q for q in queries_executed)

    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    @patch('database.engine')
    @patch('database.logger')
    def test_migration_creates_price_snapshots_table(self, mock_logger, mock_engine):
        """Test migration creates price_snapshots table"""
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        queries_executed = []

        def side_effect_func(*args, **kwargs):
            query = str(args[0])
            queries_executed.append(query)
            result = Mock()

            if 'column_name' in query:
                result.fetchone.return_value = ('col',)
            elif 'table_name' in query:
                result.fetchone.return_value = None
            elif 'constraint_name' in query or 'indexname' in query:
                result.fetchone.return_value = None
            else:
                result.fetchone.return_value = None

            result.rowcount = 0
            result.scalar.return_value = 0
            return result

        mock_conn.execute.side_effect = side_effect_func

        run_migrations()

        # Verify price_snapshots table was created
        assert any('CREATE TABLE price_snapshots' in q for q in queries_executed)

    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    @patch('database.engine')
    @patch('database.logger')
    def test_migration_adds_expansion_columns(self, mock_logger, mock_engine):
        """Test migration adds expansion-related columns"""
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        queries_executed = []

        def side_effect_func(*args, **kwargs):
            query = str(args[0])
            queries_executed.append(query)
            result = Mock()

            # Standard columns exist
            if 'date_added' in query or 'status' in query or 'is_sleeved' in query:
                result.fetchone.return_value = ('col',)
            # Tables exist
            elif 'table_name' in query:
                result.fetchone.return_value = ('table',)
            # Expansion columns don't exist
            elif 'is_expansion' in query or 'base_game_id' in query:
                result.fetchone.return_value = None
            # Constraints and indexes don't exist
            elif 'constraint_name' in query or 'indexname' in query:
                result.fetchone.return_value = None
            else:
                result.fetchone.return_value = None

            result.rowcount = 0
            result.scalar.return_value = 0
            return result

        mock_conn.execute.side_effect = side_effect_func

        run_migrations()

        # Verify expansion columns were added
        assert any('is_expansion' in q for q in queries_executed)

    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    @patch('database.engine')
    @patch('database.logger')
    def test_migration_updates_null_status(self, mock_logger, mock_engine):
        """Test migration updates NULL status values"""
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        def side_effect_func(*args, **kwargs):
            query = str(args[0])
            result = Mock()

            # Columns exist
            if 'column_name' in query:
                result.fetchone.return_value = ('col',)
            # Tables exist
            elif 'table_name' in query:
                result.fetchone.return_value = ('table',)
            # NULL status count
            elif 'COUNT(*)' in query and 'status IS NULL' in query:
                result.scalar.return_value = 10
            # Constraints and indexes exist
            elif 'constraint_name' in query or 'indexname' in query:
                result.fetchone.return_value = ('exists',)
            else:
                result.fetchone.return_value = None

            result.rowcount = 0
            return result

        mock_conn.execute.side_effect = side_effect_func

        run_migrations()

        # Verify status update was logged
        assert any('NULL status' in str(call) for call in mock_logger.info.call_args_list)

    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    @patch('database.engine')
    @patch('database.logger')
    def test_migration_adds_is_sleeved_column(self, mock_logger, mock_engine):
        """Test migration adds is_sleeved column"""
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        queries_executed = []

        def side_effect_func(*args, **kwargs):
            query = str(args[0])
            queries_executed.append(query)
            result = Mock()

            # date_added and status exist
            if 'date_added' in query or 'status' in query:
                result.fetchone.return_value = ('col',)
            # is_sleeved doesn't exist
            elif 'is_sleeved' in query:
                result.fetchone.return_value = None
            # Tables exist
            elif 'table_name' in query:
                result.fetchone.return_value = ('table',)
            elif 'constraint_name' in query or 'indexname' in query:
                result.fetchone.return_value = ('exists',)
            else:
                result.fetchone.return_value = None

            result.rowcount = 0
            result.scalar.return_value = 0
            return result

        mock_conn.execute.side_effect = side_effect_func

        run_migrations()

        # Verify is_sleeved column was added
        assert any('is_sleeved' in q and 'ADD COLUMN' in q for q in queries_executed)

    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    @patch('database.engine')
    @patch('database.logger')
    def test_migration_adds_aftergame_game_id_column(self, mock_logger, mock_engine):
        """Test migration adds aftergame_game_id column"""
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        queries_executed = []

        def side_effect_func(*args, **kwargs):
            query = str(args[0])
            queries_executed.append(query)
            result = Mock()

            # Most columns exist
            if 'date_added' in query or 'status' in query or 'is_sleeved' in query:
                result.fetchone.return_value = ('col',)
            # aftergame_game_id doesn't exist
            elif 'aftergame_game_id' in query and 'column_name' in query:
                result.fetchone.return_value = None
            # Tables exist
            elif 'table_name' in query:
                result.fetchone.return_value = ('table',)
            elif 'constraint_name' in query or 'indexname' in query:
                result.fetchone.return_value = ('exists',)
            else:
                result.fetchone.return_value = None

            result.rowcount = 0
            result.scalar.return_value = 0
            return result

        mock_conn.execute.side_effect = side_effect_func

        run_migrations()

        # Verify aftergame_game_id column was added
        assert any('aftergame_game_id' in q and 'ADD COLUMN' in q for q in queries_executed)

    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    @patch('database.engine')
    @patch('database.logger')
    def test_migration_error_handling_expansion_fields(self, mock_logger, mock_engine):
        """Test migration handles errors in expansion fields section"""
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        call_count = [0]

        def side_effect_func(*args, **kwargs):
            query = str(args[0])
            call_count[0] += 1

            # First section succeeds, expansion section fails
            if call_count[0] < 10:
                result = Mock()
                result.fetchone.return_value = ('col',)
                result.scalar.return_value = 0
                result.rowcount = 0
                return result
            else:
                raise DatabaseError("Expansion migration failed", params=None, orig=None)

        mock_conn.execute.side_effect = side_effect_func

        with pytest.raises(DatabaseError):
            run_migrations()

        # Verify rollback was called
        assert mock_conn.rollback.called

    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    @patch('database.engine')
    @patch('database.logger')
    def test_migration_error_handling_is_sleeved(self, mock_logger, mock_engine):
        """Test migration handles errors in is_sleeved section"""
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        call_count = [0]

        def side_effect_func(*args, **kwargs):
            query = str(args[0])
            call_count[0] += 1

            # Fail on is_sleeved check
            if 'is_sleeved' in query:
                raise DatabaseError("is_sleeved migration failed", params=None, orig=None)

            result = Mock()
            result.fetchone.return_value = ('col',) if call_count[0] < 15 else ('table',)
            result.scalar.return_value = 0
            result.rowcount = 0
            return result

        mock_conn.execute.side_effect = side_effect_func

        with pytest.raises(DatabaseError):
            run_migrations()

        # Verify rollback and error logging
        assert mock_conn.rollback.called
        assert any('is_sleeved' in str(call) for call in mock_logger.error.call_args_list)

    @patch('database.DATABASE_URL', 'postgresql://user:pass@localhost/db')
    @patch('database.engine')
    @patch('database.logger')
    def test_migration_error_handling_aftergame(self, mock_logger, mock_engine):
        """Test migration handles errors in aftergame_game_id section"""
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        call_count = [0]

        def side_effect_func(*args, **kwargs):
            query = str(args[0])
            call_count[0] += 1

            # Fail on aftergame check
            if 'aftergame_game_id' in query:
                raise DatabaseError("aftergame migration failed", params=None, orig=None)

            result = Mock()
            result.fetchone.return_value = ('col',) if 'column_name' in query else ('table',)
            result.scalar.return_value = 0
            result.rowcount = 0
            return result

        mock_conn.execute.side_effect = side_effect_func

        with pytest.raises(DatabaseError):
            run_migrations()

        # Verify error handling
        assert mock_conn.rollback.called
        assert any('aftergame' in str(call) for call in mock_logger.error.call_args_list)
