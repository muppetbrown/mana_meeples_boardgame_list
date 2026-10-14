"""Tests for scripts/seed_e2e_data.py (seeds the DB used by the Playwright E2E job)."""
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
import seed_e2e_data as module  # noqa: E402


def _count(url):
    with create_engine(url).connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM boardgames")).scalar()


def test_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(SystemExit) as exc:
        module.seed_test_data()
    assert exc.value.code == 1


def test_seeds_once_and_skips_when_populated(tmp_path, monkeypatch, capsys):
    url = f"sqlite:///{tmp_path / 'seed.db'}"
    monkeypatch.setenv("DATABASE_URL", url)

    module.seed_test_data()
    seeded = _count(url)
    assert seeded > 0

    module.seed_test_data()  # second run must not duplicate
    assert _count(url) == seeded
    assert "Skipping seed" in capsys.readouterr().out
