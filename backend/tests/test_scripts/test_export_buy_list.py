"""Tests for scripts/export_buy_list.py (writes the CSV the price-scraper workflow reads)."""
import csv
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
import export_buy_list as module  # noqa: E402


@pytest.fixture
def export_env(tmp_path, monkeypatch):
    db_file = tmp_path / "export.db"
    url = f"sqlite:///{db_file}"
    engine = create_engine(url)
    models.Base.metadata.create_all(engine)
    monkeypatch.setattr(module, "DATABASE_URL", url)
    # Output goes to <__file__>/../../price_data -> keep it inside tmp_path
    fake_script = tmp_path / "scripts" / "export_buy_list.py"
    fake_script.parent.mkdir()
    monkeypatch.setattr(module, "__file__", str(fake_script))
    session = sessionmaker(bind=engine)()
    yield session, tmp_path / "price_data" / "buy_list_export.csv"
    session.close()


def _read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def test_empty_buy_list_writes_header_only_csv(export_env):
    _, out = export_env
    module.export_buy_list()
    assert out.exists()
    assert _read(out) == []
    assert out.read_text().splitlines()[0] == "game_id,bgo_link,rank,name,bgg_id"


def test_exports_only_listed_games_with_links_in_rank_order(export_env):
    session, out = export_env
    g1 = models.Game(title="Beta", bgg_id=2)
    g2 = models.Game(title="Alpha", bgg_id=1)
    g3 = models.Game(title="NoLink", bgg_id=3)
    g4 = models.Game(title="NotListed", bgg_id=4)
    session.add_all([g1, g2, g3, g4])
    session.flush()
    session.add_all([
        models.BuyListGame(game_id=g1.id, on_buy_list=True, bgo_link="http://x/b", rank=2),
        models.BuyListGame(game_id=g2.id, on_buy_list=True, bgo_link="http://x/a", rank=1),
        models.BuyListGame(game_id=g3.id, on_buy_list=True, bgo_link=None, rank=3),
        models.BuyListGame(game_id=g4.id, on_buy_list=False, bgo_link="http://x/n", rank=4),
    ])
    session.commit()

    module.export_buy_list()

    rows = _read(out)
    assert [r["name"] for r in rows] == ["Alpha", "Beta"]
    assert rows[0]["bgo_link"] == "http://x/a"
