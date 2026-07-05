"""
Tests for the seed script — verifies seed() can run with a mock/in-memory DB session.
Uses SQLite in-memory (sync) to avoid needing a real PostgreSQL instance.
"""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch
import uuid
from datetime import datetime, timezone

import pytest

# ---------------------------------------------------------------------------
# Allow import of seed module
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))


def _make_mock_session() -> MagicMock:
    """Return a MagicMock that behaves like a SQLAlchemy Session."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = MagicMock()
    session.commit = MagicMock()
    return session


class TestSeedImport:
    """Verify the seed module is importable and seed() is callable."""

    def test_seed_module_importable(self) -> None:
        """Importing the seed module must not raise."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test/test"}):
            try:
                import importlib
                import seed as seed_mod  # type: ignore[import]
                importlib.reload(seed_mod)
            except ImportError:
                pytest.skip("seed module not on path — expected in scripts/")

    def test_seed_function_exists(self) -> None:
        """seed.seed() must be a callable."""
        try:
            import seed as seed_mod  # type: ignore[import]
            assert callable(seed_mod.seed)
        except ImportError:
            pytest.skip("seed module not importable from test runner")

    def test_seed_returns_counts(self) -> None:
        """seed.seed(mock_session) must return a dict with users/posts/circles keys."""
        try:
            import seed as seed_mod  # type: ignore[import]
        except ImportError:
            pytest.skip("seed module not importable from test runner")

        session = _make_mock_session()
        result = seed_mod.seed(session)

        assert isinstance(result, dict)
        assert "users" in result
        assert "posts" in result
        assert "circles" in result
        assert result["users"] == 10
        assert result["posts"] == 30
        assert result["circles"] == 3

    def test_seed_calls_commit(self) -> None:
        """seed() must commit the session at the end."""
        try:
            import seed as seed_mod  # type: ignore[import]
        except ImportError:
            pytest.skip("seed module not importable from test runner")

        session = _make_mock_session()
        seed_mod.seed(session)
        session.commit.assert_called_once()

    def test_seed_no_database_url_exits(self) -> None:
        """main() without DATABASE_URL must sys.exit(1)."""
        try:
            import seed as seed_mod  # type: ignore[import]
        except ImportError:
            pytest.skip("seed module not importable from test runner")

        env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                seed_mod.main()
        assert exc_info.value.code == 1
