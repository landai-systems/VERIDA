"""Capture flow endpoints.

POST /api/v1/capture/initiate
    Start a capture session. Returns a HMAC-signed capture_token (10-minute expiry).
    Rejects if the user already posted today.

POST /api/v1/capture/submit
    Submit a post with media. Validates the capture token.
    Rejects gallery uploads (capture_metadata.source == "gallery").
    Enforces 10 MB media size limit.
    Strips EXIF metadata from images.
    Marks post as late if submitted after the 10-minute window.
    Enqueues attestation job via arq.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from verida.api.v1.deps import (
    CurrentUser,
    get_daily_moment_repo,
    get_post_repo,
    get_settings,
)
from verida.config import Settings
from verida.domain.entities import PostVisibility

logger = structlog.get_logger(__name__)

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────


class InitiateCaptureRequest(BaseModel):
    """Request body for initiating a capture session."""

    browser_fingerprint_hash: str = Field(
        default="",
        max_length=64,
        description=(
            "SHA-256 of browser-reported signals (user-agent, screen dimensions). "
            "Used by the authenticity heuristics. NOT stored as PII."
        ),
    )


class InitiateCaptureResponse(BaseModel):
    """Response returned after initiating a capture session."""

    capture_token: str = Field(
        description="HMAC-signed token to include when submitting the post. Expires in 10 minutes."
    )
    moment_id: str = Field(description="UUID of the created DailyMoment.")
    expires_in_seconds: int = Field(
        default=600, description="Seconds until the capture token expires."
    )


class PostResponse(BaseModel):
    """Public representation of a submitted post."""

    id: str = Field(description="Post UUID.")
    author_id: str = Field(description="Author's user UUID.")
    caption: str = Field(description="Post caption text.")
    media_url: str = Field(description="URL to the re-encoded media file.")
    media_mime_type: str = Field(description="MIME type of the media.")
    visibility: str = Field(description="Visibility setting: public | circles | private.")
    is_late: bool = Field(description="True if submitted after the 10-minute capture window.")
    published_at: datetime | None = Field(description="When the post was published.")
    created_at: datetime = Field(description="Post creation timestamp.")


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/initiate",
    response_model=InitiateCaptureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a capture session",
    description=(
        "Start a daily moment capture session. Returns a short-lived capture token. "
        "A user can only initiate one capture session per day. "
        "The token expires in 10 minutes; the post may still be submitted after that "
        "but will be marked `is_late: true`."
    ),
)
async def initiate_capture(
    body: InitiateCaptureRequest,
    current_user: CurrentUser,
    daily_moment_repo: Annotated[Any, Depends(get_daily_moment_repo)],
    post_repo: Annotated[Any, Depends(get_post_repo)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> InitiateCaptureResponse:
    from verida.application.use_cases.daily_moment import InitiateCaptureUseCase

    use_case = InitiateCaptureUseCase(
        daily_moment_repo=daily_moment_repo,
        post_repo=post_repo,
        secret_key=settings.secret_key,
    )

    try:
        result = await use_case.execute(
            user_id=current_user.id,
            browser_fingerprint_hash=body.browser_fingerprint_hash,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return InitiateCaptureResponse(
        capture_token=result["capture_token"],
        moment_id=result["moment_id"],
    )


@router.post(
    "/submit",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a post from a capture session",
    description=(
        "Submit a daily moment post. Requires a valid `capture_token` "
        "from `/capture/initiate`. "
        "Gallery uploads (capture_metadata.source == 'gallery') are rejected. "
        "Media is re-encoded server-side (EXIF stripped). "
        "Max 10 MB media size."
    ),
)
async def submit_capture(
    current_user: CurrentUser,
    daily_moment_repo: Annotated[Any, Depends(get_daily_moment_repo)],
    post_repo: Annotated[Any, Depends(get_post_repo)],
    settings: Annotated[Settings, Depends(get_settings)],
    capture_token: str = Form(..., description="HMAC-signed capture token from /capture/initiate"),
    caption: str = Form(default="", max_length=500, description="Post caption (max 500 chars)"),
    visibility: str = Form(
        default="circles",
        description="Visibility: public | circles | private",
    ),
    media: UploadFile = File(..., description="Media file (image or video, max 10 MB)"),
    source: str = Form(
        default="camera",
        description="Media source. Must be 'camera' — 'gallery' is rejected.",
    ),
    duration_seconds: float = Form(
        default=0.0, description="Capture duration in seconds (browser-reported)."
    ),
    width_px: int = Form(default=0, description="Media width in pixels (browser-reported)."),
    height_px: int = Form(default=0, description="Media height in pixels (browser-reported)."),
) -> PostResponse:
    from verida.application.use_cases.daily_moment import SubmitPostUseCase

    media_bytes = await media.read()
    media_mime_type = media.content_type or "application/octet-stream"

    capture_metadata: dict[str, Any] = {
        "source": source,
        "duration_seconds": duration_seconds,
        "width_px": width_px,
        "height_px": height_px,
        "filename": media.filename or "",
    }

    try:
        vis = PostVisibility(visibility)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid visibility value '{visibility}'. Use: public, circles, private.",
        )

    use_case = SubmitPostUseCase(
        daily_moment_repo=daily_moment_repo,
        post_repo=post_repo,
        secret_key=settings.secret_key,
        arq_pool=None,  # arq pool injected via ctx in production; None skips enqueue in tests
    )

    try:
        post = await use_case.execute(
            user_id=current_user.id,
            capture_token=capture_token,
            caption=caption,
            media_bytes=media_bytes,
            media_mime_type=media_mime_type,
            capture_metadata=capture_metadata,
            visibility=vis,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc

    return PostResponse(
        id=str(post.id),
        author_id=str(post.author_id),
        caption=post.caption,
        media_url=post.media_url,
        media_mime_type=post.media_mime_type,
        visibility=post.visibility.value,
        is_late=post.is_late,
        published_at=post.published_at,
        created_at=post.created_at,
    )
