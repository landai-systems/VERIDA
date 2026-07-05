"""Comments use cases — M3.

Constraints:
- Plain-text only, max 500 characters
- No markdown, no mentions, no rich text in MVP
- Authors and moderators can delete (soft-delete)
- Hard delete on GDPR erasure
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Optional

import structlog

from verida.domain.entities import Comment

logger = structlog.get_logger(__name__)

MAX_COMMENT_LENGTH = 500


class AddCommentUseCase:
    """Add a plain-text comment to a post."""

    def __init__(self, comment_repo: object, post_repo: object) -> None:
        self._comment_repo = comment_repo
        self._post_repo = post_repo

    async def execute(
        self,
        post_id: uuid.UUID,
        author_id: uuid.UUID,
        body: str,
    ) -> Comment:
        """Add a comment.

        Parameters
        ----------
        post_id:
            The post being commented on.
        author_id:
            The commenting user.
        body:
            Plain-text comment. Max 500 characters.

        Raises
        ------
        ValueError:
            If post not found or body is too long / empty.
        """
        # Validate
        body = body.strip()
        if not body:
            raise ValueError("Comment body cannot be empty.")
        if len(body) > MAX_COMMENT_LENGTH:
            raise ValueError(
                f"Comment body cannot exceed {MAX_COMMENT_LENGTH} characters "
                f"(got {len(body)})."
            )

        # Verify post exists
        post = await self._post_repo.get_by_id(post_id)
        if post is None:
            raise ValueError(f"Post not found: {post_id}")

        comment = Comment(
            post_id=post_id,
            author_id=author_id,
            body=body,
        )
        await self._comment_repo.save(comment)

        logger.info(
            "comment_added",
            post_id=str(post_id),
            author_id=str(author_id),
            body_length=len(body),
        )
        return comment


class DeleteCommentUseCase:
    """Soft-delete a comment (author or moderator action)."""

    def __init__(self, comment_repo: object) -> None:
        self._comment_repo = comment_repo

    async def execute(
        self,
        comment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_moderator: bool = False,
    ) -> None:
        """Delete a comment.

        Raises
        ------
        ValueError:
            If comment not found.
        PermissionError:
            If requester is not the author or a moderator.
        """
        comment = await self._comment_repo.get_by_id(comment_id)
        if comment is None:
            raise ValueError(f"Comment not found: {comment_id}")

        if comment.author_id != requesting_user_id and not is_moderator:
            raise PermissionError("Only the comment author or a moderator can delete comments.")

        comment.deleted_at = datetime.now(UTC)
        await self._comment_repo.save(comment)

        logger.info(
            "comment_deleted",
            comment_id=str(comment_id),
            by_user=str(requesting_user_id),
            is_moderator=is_moderator,
        )


class ListCommentsUseCase:
    """List comments on a post, excluding soft-deleted entries."""

    def __init__(self, comment_repo: object) -> None:
        self._comment_repo = comment_repo

    async def execute(
        self,
        post_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Comment]:
        """Return comments for a post, oldest first, without deleted entries."""
        return await self._comment_repo.list_for_post(
            post_id=post_id,
            limit=limit,
            offset=offset,
            include_deleted=False,
        )
