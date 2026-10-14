"""
Tests for scripts/run_migrations.py.

Regression focus: the script must NEVER `alembic stamp head` a database that already has
migration history - that would mark pending migrations as applied without running them.
"""
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from scripts import run_migrations


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def _tables(existing):
    return lambda name: name in existing


@pytest.fixture(autouse=True)
def _no_chdir():
    with patch("scripts.run_migrations.os.chdir"):
        yield


def _commands(run_mock):
    return [call.args[0][1:] for call in run_mock.call_args_list]


class TestMain:
    def test_fresh_database_runs_upgrade(self):
        with patch.object(run_migrations, "db_ping", return_value=True), \
             patch.object(run_migrations, "check_table_exists", _tables(set())), \
             patch.object(run_migrations.subprocess, "run", return_value=_completed()) as run:
            run_migrations.main()
        assert _commands(run) == [["upgrade", "head"]]

    def test_database_with_migration_history_runs_upgrade_never_stamp(self):
        """The data-loss regression: production has tables AND alembic_version."""
        with patch.object(run_migrations, "db_ping", return_value=True), \
             patch.object(run_migrations, "check_table_exists", _tables({"boardgames", "alembic_version"})), \
             patch.object(run_migrations.subprocess, "run", return_value=_completed()) as run:
            run_migrations.main()
        assert _commands(run) == [["upgrade", "head"]]
        assert ["stamp", "head"] not in _commands(run)

    def test_legacy_schema_without_history_is_stamped_once(self):
        with patch.object(run_migrations, "db_ping", return_value=True), \
             patch.object(run_migrations, "check_table_exists", _tables({"boardgames"})), \
             patch.object(run_migrations.subprocess, "run", return_value=_completed()) as run:
            run_migrations.main()
        assert _commands(run) == [["stamp", "head"]]

    def test_failed_migration_exits_nonzero_without_stamping_over_it(self):
        failing = _completed(returncode=1, stderr='relation "x" already exists')
        with patch.object(run_migrations, "db_ping", return_value=True), \
             patch.object(run_migrations, "check_table_exists", _tables({"boardgames", "alembic_version"})), \
             patch.object(run_migrations.subprocess, "run", return_value=failing) as run:
            with pytest.raises(SystemExit) as exc:
                run_migrations.main()
        assert exc.value.code == 1
        assert _commands(run) == [["upgrade", "head"]]  # no "already exists -> stamp" fallback

    def test_unreachable_database_exits_before_running_alembic(self):
        with patch.object(run_migrations, "db_ping", return_value=False), \
             patch.object(run_migrations.subprocess, "run") as run:
            with pytest.raises(SystemExit) as exc:
                run_migrations.main()
        assert exc.value.code == 1
        run.assert_not_called()

    def test_missing_alembic_binary_exits(self):
        with patch.object(run_migrations, "db_ping", return_value=True), \
             patch.object(run_migrations, "check_table_exists", _tables(set())), \
             patch.object(run_migrations.subprocess, "run", side_effect=FileNotFoundError):
            with pytest.raises(SystemExit) as exc:
                run_migrations.main()
        assert exc.value.code == 1

    def test_unexpected_error_exits(self):
        with patch.object(run_migrations, "db_ping", side_effect=RuntimeError("boom")):
            with pytest.raises(SystemExit) as exc:
                run_migrations.main()
        assert exc.value.code == 1

    def test_alembic_output_is_printed(self, capsys):
        with patch.object(run_migrations, "db_ping", return_value=True), \
             patch.object(run_migrations, "check_table_exists", _tables(set())), \
             patch.object(run_migrations.subprocess, "run",
                          return_value=_completed(stdout="Running upgrade", stderr="a warning")):
            run_migrations.main()
        out = capsys.readouterr()
        assert "Running upgrade" in out.out
        assert "a warning" in out.err


class TestCheckTableExists:
    def test_returns_scalar_result_and_closes_session(self):
        session = MagicMock()
        session.execute.return_value.scalar.return_value = True
        with patch.object(run_migrations.database, "SessionLocal", return_value=session):
            assert run_migrations.check_table_exists("boardgames") is True
        session.close.assert_called_once()

    def test_returns_false_on_error(self):
        with patch.object(run_migrations.database, "SessionLocal", side_effect=RuntimeError("down")):
            assert run_migrations.check_table_exists("boardgames") is False
