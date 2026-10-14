"""Tests for PostgreSQL per-connection safety settings (utils/db_settings.py)."""
from unittest.mock import MagicMock

from sqlalchemy import create_engine, event

from utils.db_settings import apply_postgres_session_settings, install_session_settings


def _fake_connection(autocommit=False):
    conn = MagicMock()
    conn.autocommit = autocommit
    return conn


class TestApplyPostgresSessionSettings:
    def test_sets_all_three_settings_with_millisecond_values(self):
        conn = _fake_connection()
        apply_postgres_session_settings(
            conn, lock_timeout_s=10, idle_in_tx_timeout_s=60, application_name="svc"
        )
        calls = [c.args[1] for c in conn.cursor.return_value.execute.call_args_list]
        assert calls == [
            ("application_name", "svc"),
            ("lock_timeout", "10000"),
            ("idle_in_transaction_session_timeout", "60000"),
        ]

    def test_uses_parameterised_set_config(self):
        conn = _fake_connection()
        apply_postgres_session_settings(
            conn, lock_timeout_s=1, idle_in_tx_timeout_s=1, application_name="x'; DROP TABLE y;--"
        )
        for call in conn.cursor.return_value.execute.call_args_list:
            assert call.args[0] == "SELECT set_config(%s, %s, false)"

    def test_runs_in_autocommit_and_restores_previous_mode(self):
        modes = []
        conn = MagicMock()
        conn.autocommit = False

        def record(*_a, **_k):
            modes.append(conn.autocommit)

        conn.cursor.return_value.execute.side_effect = record
        apply_postgres_session_settings(
            conn, lock_timeout_s=1, idle_in_tx_timeout_s=1, application_name="x"
        )
        assert modes == [True, True, True]  # executed with autocommit on
        assert conn.autocommit is False  # restored

    def test_restores_autocommit_and_closes_cursor_even_when_a_statement_fails(self):
        conn = _fake_connection(autocommit=True)
        conn.cursor.return_value.execute.side_effect = RuntimeError("boom")
        try:
            apply_postgres_session_settings(
                conn, lock_timeout_s=1, idle_in_tx_timeout_s=1, application_name="x"
            )
        except RuntimeError:
            pass
        else:  # pragma: no cover
            raise AssertionError("expected RuntimeError")
        assert conn.autocommit is True
        conn.cursor.return_value.close.assert_called_once()

    def test_zero_disables_timeouts(self):
        conn = _fake_connection()
        apply_postgres_session_settings(
            conn, lock_timeout_s=0, idle_in_tx_timeout_s=0, application_name="x"
        )
        values = [c.args[1][1] for c in conn.cursor.return_value.execute.call_args_list]
        assert values[1:] == ["0", "0"]


class TestInstallSessionSettings:
    def test_is_a_noop_for_sqlite(self):
        engine = create_engine("sqlite://")
        assert (
            install_session_settings(
                engine, lock_timeout_s=1, idle_in_tx_timeout_s=1, application_name="x"
            )
            is None
        )

    def test_registers_connect_listener_for_postgres(self):
        engine = create_engine("postgresql+psycopg2://user:pw@localhost/db")
        listener = install_session_settings(
            engine, lock_timeout_s=10, idle_in_tx_timeout_s=60, application_name="svc"
        )
        assert listener is not None
        assert event.contains(engine, "connect", listener)

    def test_listener_applies_settings_to_the_new_connection(self):
        engine = create_engine("postgresql+psycopg2://user:pw@localhost/db")
        listener = install_session_settings(
            engine, lock_timeout_s=5, idle_in_tx_timeout_s=30, application_name="svc"
        )
        conn = _fake_connection()
        listener(conn, None)
        values = [c.args[1] for c in conn.cursor.return_value.execute.call_args_list]
        assert ("lock_timeout", "5000") in values
        assert ("idle_in_transaction_session_timeout", "30000") in values
