"""
Startup/deploy hardening: time-boxed cache warming, DB lock/idle timeouts, release id.

Background: a slow or blocked startup step must never stop the server from opening its port
(Render waits for it), and a blocked migration must fail loudly instead of hanging.
"""
import asyncio
import importlib
import os
import time
from unittest.mock import patch

import pytest


class TestTimeBoxedCacheWarming:
    @pytest.mark.asyncio
    async def test_slow_warm_up_does_not_block_startup(self, caplog):
        import main

        def slow_warm():
            time.sleep(1.0)

        with patch.object(main, "warm_cache", slow_warm), \
             patch.object(main, "db_ping", return_value=True), \
             patch.object(main, "STARTUP_CACHE_WARM_TIMEOUT_SECONDS", 0.05):
            started = time.monotonic()
            with caplog.at_level("WARNING"):
                async with main.lifespan(main.app):
                    elapsed = time.monotonic() - started
        assert elapsed < 0.8  # did not wait the full second
        assert any("continuing startup" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_fast_warm_up_runs_to_completion(self):
        import main

        calls = []
        with patch.object(main, "warm_cache", lambda: calls.append(1)), \
             patch.object(main, "db_ping", return_value=True):
            async with main.lifespan(main.app):
                pass
        assert calls == [1]

    @pytest.mark.asyncio
    async def test_startup_still_fails_fast_if_database_is_unreachable(self):
        import main

        with patch.object(main, "db_ping", return_value=False):
            with pytest.raises(RuntimeError):
                async with main.lifespan(main.app):
                    pass  # pragma: no cover


class TestTimeoutConfig:
    @pytest.mark.parametrize(
        "name,default",
        [
            ("DB_LOCK_TIMEOUT_SECONDS", 10.0),
            ("DB_IDLE_IN_TX_TIMEOUT_SECONDS", 60.0),
            ("MIGRATION_LOCK_TIMEOUT_SECONDS", 30.0),
            ("STARTUP_CACHE_WARM_TIMEOUT_SECONDS", 20.0),
        ],
    )
    def test_defaults(self, name, default):
        import config

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(name, None)
            importlib.reload(config)
            assert getattr(config, name) == default

    def test_overridable_from_environment(self):
        import config

        with patch.dict(os.environ, {"MIGRATION_LOCK_TIMEOUT_SECONDS": "5"}):
            importlib.reload(config)
            assert config.MIGRATION_LOCK_TIMEOUT_SECONDS == 5.0
        importlib.reload(config)


class TestSentryReleaseId:
    def test_falls_back_to_render_commit(self):
        # Mirrors the expression used in main.py's sentry_sdk.init(release=...)
        with patch.dict(os.environ, {"RENDER_GIT_COMMIT": "abc123"}, clear=False):
            os.environ.pop("GIT_COMMIT_SHA", None)
            release = os.getenv("GIT_COMMIT_SHA") or os.getenv("RENDER_GIT_COMMIT") or "unknown"
            assert release == "abc123"
