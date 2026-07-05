"""Alembic environment configuration for async SQLAlchemy.

Reads the DATABASE_URL from the application settings (environment variables / .env).
Runs migrations in online mode using asyncpg.
"""

from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ── Path setup ─────────────────────────────────────────────────────────────────
# Allow ``from verida...`` imports when running alembic from backend/
_src = Path(__file__).parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

# ── Load ORM models so autogenerate can detect them ───────────────────────────
from verida.infrastructure.db.models import Base  # noqa: E402

# ── Alembic config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Pull DATABASE_URL from the environment (overriding alembic.ini stub)."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        # Fallback: load via pydantic-settings
        from verida.config import get_settings
        url = get_settings().database_url
    return url


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in online mode (with a live DB connection)."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


asyncio.run(run_migrations_online())
