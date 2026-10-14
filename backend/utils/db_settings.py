# utils/db_settings.py
"""
PostgreSQL per-connection safety settings.

Why this exists: by default PostgreSQL waits *forever* for a table lock, silently. A
migration (``ALTER TABLE``) that queues behind another session therefore hangs the deploy
with no error, and every query that arrives afterwards queues up behind the waiting
``ALTER``. These settings make that failure loud and bounded:

* ``lock_timeout``                       - give up waiting for a lock after N seconds
* ``idle_in_transaction_session_timeout`` - the database closes a session that opened a
                                            transaction and then went quiet (a leaked
                                            connection), instead of blocking DDL forever
* ``application_name``                    - makes sessions identifiable in pg_stat_activity

A value of 0 disables the corresponding timeout.
"""
from typing import Callable

from sqlalchemy import event
from sqlalchemy.engine import Engine


def apply_postgres_session_settings(
    dbapi_connection,
    *,
    lock_timeout_s: float,
    idle_in_tx_timeout_s: float,
    application_name: str,
) -> None:
    """Apply the safety settings to a freshly opened psycopg2 connection."""
    settings = {
        "application_name": application_name,
        "lock_timeout": str(int(lock_timeout_s * 1000)),
        "idle_in_transaction_session_timeout": str(int(idle_in_tx_timeout_s * 1000)),
    }
    # Run outside a transaction so SQLAlchemy's later rollback can't undo the settings.
    previous_autocommit = dbapi_connection.autocommit
    dbapi_connection.autocommit = True
    try:
        cursor = dbapi_connection.cursor()
        try:
            for name, value in settings.items():
                cursor.execute("SELECT set_config(%s, %s, false)", (name, value))
        finally:
            cursor.close()
    finally:
        dbapi_connection.autocommit = previous_autocommit


def install_session_settings(
    engine: Engine,
    *,
    lock_timeout_s: float,
    idle_in_tx_timeout_s: float,
    application_name: str,
) -> Callable | None:
    """
    Register a ``connect`` listener on ``engine`` applying the settings to every new
    connection. No-op (returns None) for non-PostgreSQL engines such as the SQLite test DB.
    """
    if engine.dialect.name != "postgresql":
        return None

    def _on_connect(dbapi_connection, _connection_record):
        apply_postgres_session_settings(
            dbapi_connection,
            lock_timeout_s=lock_timeout_s,
            idle_in_tx_timeout_s=idle_in_tx_timeout_s,
            application_name=application_name,
        )

    event.listen(engine, "connect", _on_connect)
    return _on_connect
