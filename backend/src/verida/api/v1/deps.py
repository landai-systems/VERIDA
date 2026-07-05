"""FastAPI dependency injectors for M2.

Provides authenticated user extraction and repository/use-case factories
as FastAPI ``Depends()`` callables.

Design
------
- ``get_current_user`` validates the Bearer JWT and returns the domain User.
- Repository factories create a new instance bound to the request-scoped
  DB session; they are cheap to construct.
- Use-case factories compose repositories into application services.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Annotated, AsyncGenerator

import structlog
from fastapi import Cookie, Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from verida.config import Settings, get_settings
from verida.domain.entities import User
from verida.infrastructure.db.session import get_async_session

logger = structlog.get_logger(__name__)


# ── DB Session ─────────────────────────────────────────────────────────────────

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


# ── Repository factories ───────────────────────────────────────────────────────

def get_user_repo(session: AsyncSessionDep) -> "SqlUserRepository":  # type: ignore[name-defined]
    from verida.infrastructure.db.repositories import SqlUserRepository
    return SqlUserRepository(session)


def get_post_repo(session: AsyncSessionDep) -> "SqlPostRepository":  # type: ignore[name-defined]
    from verida.infrastructure.db.repositories import SqlPostRepository
    return SqlPostRepository(session)


def get_circle_repo(session: AsyncSessionDep) -> "SqlCircleRepository":  # type: ignore[name-defined]
    from verida.infrastructure.db.repositories import SqlCircleRepository
    return SqlCircleRepository(session)


def get_daily_moment_repo(session: AsyncSessionDep) -> "SqlDailyMomentRepository":  # type: ignore[name-defined]
    from verida.infrastructure.db.repositories import SqlDailyMomentRepository
    return SqlDailyMomentRepository(session)


def get_refresh_token_repo(session: AsyncSessionDep) -> "SqlRefreshTokenRepository":  # type: ignore[name-defined]
    from verida.infrastructure.db.repositories import SqlRefreshTokenRepository
    return SqlRefreshTokenRepository(session)


def get_email_verification_repo(session: AsyncSessionDep) -> "SqlEmailVerificationRepository":  # type: ignore[name-defined]
    from verida.infrastructure.db.repositories import SqlEmailVerificationRepository
    return SqlEmailVerificationRepository(session)


def get_attestation_repo(session: AsyncSessionDep) -> "SqlAttestationRepository":  # type: ignore[name-defined]
    from verida.infrastructure.db.repositories import SqlAttestationRepository
    return SqlAttestationRepository(session)


# ── Authentication ─────────────────────────────────────────────────────────────

def _decode_token(token: str, settings: Settings) -> uuid.UUID:
    """Decode JWT and return user_id, or raise 401."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        return uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Extract and validate the Bearer token; return the authenticated User."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ")
    user_id = _decode_token(token, settings)

    from verida.infrastructure.db.repositories import SqlUserRepository
    repo = SqlUserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
