"""pytest configuration and shared fixtures.

Test categories:
    unit        — pure domain/application tests, no I/O
    integration — tests against real DB/Redis (via testcontainers)
    e2e         — full HTTP round-trips via httpx.AsyncClient

Run only unit tests in CI fast path:
    pytest -m unit

Run all tests (integration requires Docker):
    pytest
"""

from __future__ import annotations

import os
from typing import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from verida.infrastructure.db.models import Base
from verida.infrastructure.db.session import get_async_session


# ── Environment isolation ─────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    """Clear the lru_cache on Settings between tests.

    This allows tests to set different env vars without interfering.
    """
    from verida.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ── SQLite in-memory DB fixture ───────────────────────────────────────────────

@pytest_asyncio.fixture()
async def test_db_session() -> AsyncIterator[AsyncSession]:
    """Create an in-memory SQLite database and yield a session.

    Uses StaticPool so that the same connection is used across the session,
    preserving in-memory state between queries.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ── Application fixture ───────────────────────────────────────────────────────

@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """Return a FastAPI test app with safe development settings."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-that-is-at-least-32-chars-long!")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("EMAIL_FROM", "noreply@verida.example.com")

    from verida.main import create_app
    return create_app()


@pytest_asyncio.fixture()
async def client(app: FastAPI, test_db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Async HTTP test client bound to the test app with in-memory DB."""

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        yield test_db_session

    app.dependency_overrides[get_async_session] = _override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
