"""database.py builds a separate, session-configured engine when READ_REPLICA_URL is set."""
import importlib.util
from pathlib import Path

import config


def test_read_replica_engine_is_separate(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "READ_REPLICA_URL", f"sqlite:///{tmp_path / 'replica.db'}")
    spec = importlib.util.spec_from_file_location(
        "database_with_replica", Path(__file__).parent.parent / "database.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.read_engine is not module.engine
    assert module.ReadSessionLocal is not module.SessionLocal
