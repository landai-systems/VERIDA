"""Posts endpoints — read and delete individual posts.

GET    /api/v1/posts/{post_id}   — get a single post (must be in same circle or author)
DELETE /api/v1/posts/{post_id}   — delete a post (author only)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from verida.api.v1.deps import CurrentUser, get_post_repo

logger = structlog.get_logger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class AttestationResponse(BaseModel):
    status: str = Field(description="Attestation status: pending | passed | flagged | rejected.")
    score: float = Field(description="Authenticity score (0.0 – 1.0).")
    checked_at: datetime | None = Field(description="When the attestation was performed.")


class PostDetailResponse(BaseModel):
    id: str
    author_id: str
    caption: str
    media_url: str
    media_mime_type: str
    visibility: str
    is_late: bool
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    attestation: AttestationResponse | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/{post_id}",
    response_model=PostDetailResponse,
    summary="Get a single post by ID",
)
async def get_post(
    post_id: Annotated[str, Path(description="Post UUID")],
    current_user: CurrentUser,
    post_repo: Annotated[Any, Depends(get_post_repo)],
) -> PostDetailResponse:
    try:
        pid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid post ID format.",
        )

    post = await post_repo.get_by_id(pid)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    # Access control: only the author can view private posts
    if post.visibility.value == "private" and post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this post.",
        )

    att = None
    if post.attestation:
        att = AttestationResponse(
            status=post.attestation.status.value,
            score=post.attestation.score,
            checked_at=post.attestation.checked_at,
        )

    return PostDetailResponse(
        id=str(post.id),
        author_id=str(post.author_id),
        caption=post.caption,
        media_url=post.media_url,
        media_mime_type=post.media_mime_type,
        visibility=post.visibility.value,
        is_late=post.is_late,
        published_at=post.published_at,
        created_at=post.created_at,
        updated_at=post.updated_at,
        attestation=att,
    )


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a post (author only)",
)
async def delete_post(
    post_id: Annotated[str, Path(description="Post UUID")],
    current_user: CurrentUser,
    post_repo: Annotated[Any, Depends(get_post_repo)],
) -> None:
    try:
        pid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid post ID format.",
        )

    post = await post_repo.get_by_id(pid)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the post author can delete it.",
        )

    await post_repo.delete(pid)
    logger.info("post_deleted", post_id=post_id, user_id=str(current_user.id))
