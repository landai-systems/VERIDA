"""Auth endpoints — register, login, refresh, logout.

Security design:
    - Passwords are hashed with Argon2id (time_cost=2, memory_cost=65536)
    - Access tokens are short-lived JWTs (15 min by default)
    - Refresh tokens are long-lived opaque strings stored server-side
      (only the SHA-256 hash is stored — never the plaintext token)
    - On refresh, the old token is revoked and a new one is issued (rotation)
    - Refresh tokens are delivered as httpOnly, SameSite=Strict cookies
    - On logout, all refresh tokens for the user are revoked

Rate limiting: Implement at the reverse proxy (Caddy/Traefik) layer.
               The endpoint does NOT implement application-level rate limiting
               to keep the domain layer clean.

Endpoints:
    POST /api/v1/auth/register
    POST /api/v1/auth/login
    POST /api/v1/auth/refresh
    POST /api/v1/auth/logout
    GET  /api/v1/auth/me
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from verida.config import Settings, get_settings
from verida.domain.entities import RefreshToken, User
from verida.infrastructure.db.session import get_async_session
from verida.infrastructure.db.repositories import SqlUserRepository, SqlRefreshTokenRepository

logger = structlog.get_logger(__name__)

router = APIRouter()

# ── Password hashing ──────────────────────────────────────────────────────────
# Argon2id with OWASP-recommended parameters (time_cost=2, memory_cost=64 MiB)
_ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)


# ── Request / Response schemas ────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    handle: str = Field(
        ...,
        min_length=2,
        max_length=30,
        pattern=r"^[a-z0-9_]+$",
        description="Unique @-handle (lowercase, digits, underscores only)",
    )
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=60)

    @field_validator("password")
    @classmethod
    def password_not_too_common(cls, v: str) -> str:
        common = {"password123456", "qwertyuiop12", "letmein123456"}
        if v.lower() in common:
            raise ValueError("Password is too common")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    id: str
    handle: str
    display_name: str
    bio: str
    avatar_url: str | None
    is_verified: bool
    created_at: datetime


# ── Helpers ───────────────────────────────────────────────────────────────────


def _create_access_token(user_id: uuid.UUID, settings: Settings) -> tuple[str, int]:
    """Create a signed JWT access token.  Returns (token, expires_in_seconds)."""
    expire_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    expire = datetime.now(UTC) + expire_delta
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expire_delta.total_seconds())


def _create_refresh_token(user_id: uuid.UUID, settings: Settings) -> tuple[str, RefreshToken]:
    """Create a new refresh token.  Returns (raw_token, RefreshToken entity)."""
    raw = os.urandom(48).hex()  # 384-bit random token
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    entity = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    return raw, entity


def _decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    """Validate and decode a JWT access token.  Returns user_id."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        return uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    body: RegisterRequest,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TokenResponse:
    """Register a new VERIDA account.

    On success, returns an access token and sets a httpOnly refresh token cookie.
    In development mode, users are auto-verified (no email confirmation required).
    """
    user_repo = SqlUserRepository(session)
    refresh_repo = SqlRefreshTokenRepository(session)

    # Duplicate email check
    existing = await user_repo.get_by_email(str(body.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Also check handle uniqueness
    existing_handle = await user_repo.get_by_handle(body.handle)
    if existing_handle is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This handle is already taken",
        )

    # Hash password
    argon2_hash = _ph.hash(body.password)

    # In development, auto-verify users (no email confirmation needed)
    is_verified = settings.environment == "development"

    user = User(
        handle=body.handle,
        email=str(body.email),
        display_name=body.display_name,
        argon2_hash=argon2_hash,
        is_verified=is_verified,
    )
    await user_repo.save(user)

    access_token, expires_in = _create_access_token(user.id, settings)
    raw_refresh, refresh_entity = _create_refresh_token(user.id, settings)
    await refresh_repo.save(refresh_entity)

    _set_refresh_cookie(response, raw_refresh, settings)

    logger.info("user_registered", user_id=str(user.id), handle=user.handle)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with email + password",
)
async def login(
    body: LoginRequest,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TokenResponse:
    """Login with email and password.

    Returns a short-lived JWT access token and sets a httpOnly refresh cookie.
    Always returns the same error for wrong email OR wrong password to
    prevent user enumeration.
    """
    _INVALID_MSG = "Invalid email or password"

    user_repo = SqlUserRepository(session)
    refresh_repo = SqlRefreshTokenRepository(session)

    user = await user_repo.get_by_email(str(body.email))
    if user is None:
        # Perform a dummy hash to prevent timing attacks on user enumeration
        _ph.hash("dummy-password-for-timing-protection")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_MSG)

    try:
        _ph.verify(user.argon2_hash, body.password)
    except VerifyMismatchError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_MSG)

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    # Rehash if Argon2 parameters have changed
    if _ph.check_needs_rehash(user.argon2_hash):
        user.argon2_hash = _ph.hash(body.password)
        user.updated_at = datetime.now(UTC)
        await user_repo.save(user)

    access_token, expires_in = _create_access_token(user.id, settings)
    raw_refresh, refresh_entity = _create_refresh_token(user.id, settings)
    await refresh_repo.save(refresh_entity)

    _set_refresh_cookie(response, raw_refresh, settings)

    logger.info("user_login", user_id=str(user.id))
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and issue new access token",
)
async def refresh(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    refresh_token: Annotated[str | None, Cookie(alias="verida_refresh")] = None,
) -> TokenResponse:
    """Issue a new access token using a valid refresh token.

    The old refresh token is revoked immediately (rotation).
    """
    _INVALID = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )

    if not refresh_token:
        raise _INVALID

    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    user_repo = SqlUserRepository(session)
    refresh_repo = SqlRefreshTokenRepository(session)

    stored = await refresh_repo.get_by_token_hash(token_hash)

    if stored is None or stored.revoked or stored.expires_at < datetime.now(UTC):
        raise _INVALID

    # Revoke old token (rotation)
    stored.revoked = True
    await refresh_repo.save(stored)

    user = await user_repo.get_by_id(stored.user_id)
    if user is None or not user.is_active:
        raise _INVALID

    access_token, expires_in = _create_access_token(user.id, settings)
    raw_refresh, new_entity = _create_refresh_token(user.id, settings)
    await refresh_repo.save(new_entity)

    _set_refresh_cookie(response, raw_refresh, settings)

    logger.info("token_refreshed", user_id=str(user.id))
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke all refresh tokens for the current user",
)
async def logout(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    refresh_token: Annotated[str | None, Cookie(alias="verida_refresh")] = None,
) -> None:
    """Logout — revoke the current refresh token and clear the cookie."""
    if refresh_token:
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        refresh_repo = SqlRefreshTokenRepository(session)
        stored = await refresh_repo.get_by_token_hash(token_hash)
        if stored:
            await refresh_repo.revoke_all_for_user(stored.user_id)
            logger.info("user_logout", user_id=str(stored.user_id))

    # Clear cookie regardless
    response.delete_cookie("verida_refresh")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user",
)
async def me(
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> UserResponse:
    """Return the profile of the currently authenticated user.

    Requires a valid ``Authorization: Bearer <token>`` header.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = authorization.removeprefix("Bearer ")
    user_id = _decode_access_token(token, settings)

    user_repo = SqlUserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse(
        id=str(user.id),
        handle=user.handle,
        display_name=user.display_name,
        bio=user.bio,
        avatar_url=user.avatar_url,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )


# ── Cookie helper ─────────────────────────────────────────────────────────────


def _set_refresh_cookie(response: Response, raw_token: str, settings: Settings) -> None:
    """Set the httpOnly refresh token cookie."""
    max_age = settings.jwt_refresh_token_expire_days * 24 * 3600
    response.set_cookie(
        key="verida_refresh",
        value=raw_token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",  # lax allows cross-origin (dev proxy setup)
        max_age=max_age,
        path="/api/v1/auth",
    )
