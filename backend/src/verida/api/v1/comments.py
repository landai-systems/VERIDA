"""Comments API — M3.

Endpoints:
    GET    /api/v1/posts/{post_id}/comments              — list comments
    POST   /api/v1/posts/{post_id}/comments              — add comment
    DELETE /api/v1/posts/{post_id}/comments/{comment_id} — delete comment

Constraints:
- Plain-text only, max 500 characters
- Authors can delete their own comments
- Soft delete (deleted_at) is used — body replaced with tombstone in response
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, field_validator

from verida.api.v1.deps import AsyncSessionDep, CurrentUser
from verida.application.use_cases.comments import (
    AddCommentUseCase,
    DeleteCommentUseCase,
    ListCommentsUseCase,
)

router = APIRouter()

MAX_COMMENT_LENGTH = 500


class AddCommentRequest(BaseModel):
    body: str

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Comment body cannot be empty.")
        if len(v) > MAX_COMMENT_LENGTH:
            raise ValueError(f"Comment exceeds {MAX_COMMENT_LENGTH} character limit.")
        return v


class CommentResponse(BaseModel):
    id: str
    post_id: str
    author_id: str
    body: str
    created_at: datetime
    is_deleted: bool


@router.get(
    "/{post_id}/comments",
    response_model=list[CommentResponse],
    summary="List comments on a post",
)
async def list_comments(
    post_id: UUID,
    current_user: CurrentUser,
    session: AsyncSessionDep,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[CommentResponse]:
    """Return comments on a post, oldest first. Deleted comments show tombstone."""
    from verida.infrastructure.db.repositories import SqlCommentRepository

    repo = SqlCommentRepository(session)
    use_case = ListCommentsUseCase(repo)
    comments = await use_case.execute(post_id=post_id, limit=limit, offset=offset)

    return [
        CommentResponse(
            id=str(c.id),
            post_id=str(c.post_id),
            author_id=str(c.author_id),
            body=c.body if not c.deleted_at else "[deleted]",
            created_at=c.created_at,
            is_deleted=c.deleted_at is not None,
        )
        for c in comments
    ]


@router.post(
    "/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment to a post",
)
async def add_comment(
    post_id: UUID,
    body: AddCommentRequest,
    current_user: CurrentUser,
    session: AsyncSessionDep,
) -> CommentResponse:
    """Add a plain-text comment. Max 500 characters."""
    from verida.infrastructure.db.repositories import SqlCommentRepository, SqlPostRepository

    comment_repo = SqlCommentRepository(session)
    post_repo = SqlPostRepository(session)
    use_case = AddCommentUseCase(comment_repo=comment_repo, post_repo=post_repo)

    try:
        comment = await use_case.execute(
            post_id=post_id,
            author_id=current_user.id,
            body=body.body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return CommentResponse(
        id=str(comment.id),
        post_id=str(comment.post_id),
        author_id=str(comment.author_id),
        body=comment.body,
        created_at=comment.created_at,
        is_deleted=False,
    )


@router.delete(
    "/{post_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment (author only)",
)
async def delete_comment(
    post_id: UUID,
    comment_id: UUID,
    current_user: CurrentUser,
    session: AsyncSessionDep,
) -> None:
    """Soft-delete a comment. Only the author or a moderator can delete."""
    from verida.infrastructure.db.repositories import SqlCommentRepository

    repo = SqlCommentRepository(session)
    use_case = DeleteCommentUseCase(repo)

    try:
        await use_case.execute(
            comment_id=comment_id,
            requesting_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
