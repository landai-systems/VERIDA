"""API v1 root router — aggregates all sub-routers.

Each sub-module (auth, capture, posts, circles, feed, health, consent, gdpr,
reactions, comments, streaks) registers its own APIRouter.  This module
includes them all under a single ``api_v1_router`` mounted at ``/api/v1``.
"""

from __future__ import annotations

from fastapi import APIRouter

from verida.api.v1.auth import router as auth_router
from verida.api.v1.capture import router as capture_router
from verida.api.v1.circles import router as circles_router
from verida.api.v1.comments import router as comments_router
from verida.api.v1.consent import router as consent_router
from verida.api.v1.feed import router as feed_router
from verida.api.v1.gdpr import router as gdpr_router
from verida.api.v1.posts import router as posts_router
from verida.api.v1.reactions import router as reactions_router
from verida.api.v1.streaks import router as streaks_router

api_v1_router = APIRouter()

# ── Auth ───────────────────────────────────────────────────────────────────────
api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# ── Capture flow ───────────────────────────────────────────────────────────────
api_v1_router.include_router(capture_router, prefix="/capture", tags=["capture"])

# ── Posts ──────────────────────────────────────────────────────────────────────
api_v1_router.include_router(posts_router, prefix="/posts", tags=["posts"])

# ── Circles ────────────────────────────────────────────────────────────────────
api_v1_router.include_router(circles_router, prefix="/circles", tags=["circles"])

# ── Feed ───────────────────────────────────────────────────────────────────────
api_v1_router.include_router(feed_router, prefix="/feed", tags=["feed"])

# ── M3: Reactions ─────────────────────────────────────────────────────────────
api_v1_router.include_router(reactions_router, prefix="/posts", tags=["reactions"])

# ── M3: Comments ──────────────────────────────────────────────────────────────
api_v1_router.include_router(comments_router, prefix="/posts", tags=["comments"])

# ── M3: Consent management ────────────────────────────────────────────────────
api_v1_router.include_router(consent_router, prefix="/consent", tags=["consent"])

# ── M3: GDPR (export + erasure) ───────────────────────────────────────────────
api_v1_router.include_router(gdpr_router, prefix="/gdpr", tags=["gdpr"])

# ── M3: Streaks ───────────────────────────────────────────────────────────────
api_v1_router.include_router(streaks_router, prefix="/me/streak", tags=["streaks"])

# ── Observability ──────────────────────────────────────────────────────────────
health_router = APIRouter()


@health_router.get("/ping", summary="Lightweight ping")
async def ping() -> dict[str, str]:
    return {"pong": "ok"}


api_v1_router.include_router(health_router, prefix="/health", tags=["observability"])
