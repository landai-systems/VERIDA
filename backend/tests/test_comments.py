"""Tests for comments — M3.

Tests:
- Add a comment (success)
- Reject empty body
- Reject body over 500 chars
- Delete a comment (author)
- Delete a comment (non-author raises PermissionError)
- List comments excludes soft-deleted entries
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Optional

import pytest

from verida.application.use_cases.comments import (
    AddCommentUseCase,
    DeleteCommentUseCase,
    ListCommentsUseCase,
)
from verida.domain.entities import Comment, Post, PostVisibility


# ── Fake repositories ─────────────────────────────────────────────────────────


class FakeCommentRepository:
    def __init__(self) -> None:
        self._comments: dict[uuid.UUID, Comment] = {}

    async def get_by_id(self, comment_id: uuid.UUID) -> Optional[Comment]:
        return self._comments.get(comment_id)

    async def save(self, comment: Comment) -> None:
        self._comments[comment.id] = comment

    async def list_for_post(
        self,
        post_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> list[Comment]:
        results = [c for c in self._comments.values() if c.post_id == post_id]
        if not include_deleted:
            results = [c for c in results if c.deleted_at is None]
        results.sort(key=lambda c: c.created_at)
        return results[offset : offset + limit]

    async def list_by_author(self, author_id: uuid.UUID, limit: int = 1000) -> list[Comment]:
        return [c for c in self._comments.values() if c.author_id == author_id]

    async def delete_all_by_author(self, author_id: uuid.UUID) -> None:
        for comment in list(self._comments.values()):
            if comment.author_id == author_id:
                del self._comments[comment.id]


class FakePostRepository:
    def __init__(self, post: Optional[Post] = None) -> None:
        self._post = post

    async def get_by_id(self, post_id: uuid.UUID) -> Optional[Post]:
        if self._post and self._post.id == post_id:
            return self._post
        return None


def _make_post() -> Post:
    return Post(
        id=uuid.uuid4(),
        author_id=uuid.uuid4(),
        daily_moment_id=uuid.uuid4(),
        caption="Test post",
        media_url="https://cdn.example.com/photo.jpg",
        media_hash="a" * 64,
        media_mime_type="image/jpeg",
    )


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_comment_success() -> None:
    post = _make_post()
    comment_repo = FakeCommentRepository()
    post_repo = FakePostRepository(post)
    uc = AddCommentUseCase(comment_repo=comment_repo, post_repo=post_repo)
    author_id = uuid.uuid4()

    comment = await uc.execute(post_id=post.id, author_id=author_id, body="Great post!")

    assert comment.post_id == post.id
    assert comment.author_id == author_id
    assert comment.body == "Great post!"
    assert comment.deleted_at is None


@pytest.mark.asyncio
async def test_add_comment_empty_body_raises() -> None:
    post = _make_post()
    comment_repo = FakeCommentRepository()
    post_repo = FakePostRepository(post)
    uc = AddCommentUseCase(comment_repo=comment_repo, post_repo=post_repo)

    with pytest.raises(ValueError, match="empty"):
        await uc.execute(post_id=post.id, author_id=uuid.uuid4(), body="   ")


@pytest.mark.asyncio
async def test_add_comment_too_long_raises() -> None:
    post = _make_post()
    comment_repo = FakeCommentRepository()
    post_repo = FakePostRepository(post)
    uc = AddCommentUseCase(comment_repo=comment_repo, post_repo=post_repo)

    long_body = "x" * 501

    with pytest.raises(ValueError, match="500"):
        await uc.execute(post_id=post.id, author_id=uuid.uuid4(), body=long_body)


@pytest.mark.asyncio
async def test_add_comment_exact_limit_allowed() -> None:
    """500 characters is exactly the limit — should be allowed."""
    post = _make_post()
    comment_repo = FakeCommentRepository()
    post_repo = FakePostRepository(post)
    uc = AddCommentUseCase(comment_repo=comment_repo, post_repo=post_repo)

    body_500 = "a" * 500
    comment = await uc.execute(post_id=post.id, author_id=uuid.uuid4(), body=body_500)
    assert len(comment.body) == 500


@pytest.mark.asyncio
async def test_add_comment_post_not_found_raises() -> None:
    comment_repo = FakeCommentRepository()
    post_repo = FakePostRepository(None)
    uc = AddCommentUseCase(comment_repo=comment_repo, post_repo=post_repo)

    with pytest.raises(ValueError, match="Post not found"):
        await uc.execute(post_id=uuid.uuid4(), author_id=uuid.uuid4(), body="Hello")


@pytest.mark.asyncio
async def test_delete_comment_by_author_success() -> None:
    post = _make_post()
    author_id = uuid.uuid4()
    comment_repo = FakeCommentRepository()
    post_repo = FakePostRepository(post)

    add_uc = AddCommentUseCase(comment_repo=comment_repo, post_repo=post_repo)
    comment = await add_uc.execute(post_id=post.id, author_id=author_id, body="Test comment")

    delete_uc = DeleteCommentUseCase(comment_repo)
    await delete_uc.execute(comment_id=comment.id, requesting_user_id=author_id)

    updated = await comment_repo.get_by_id(comment.id)
    assert updated is not None
    assert updated.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_comment_by_non_author_raises() -> None:
    post = _make_post()
    author_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    comment_repo = FakeCommentRepository()
    post_repo = FakePostRepository(post)

    add_uc = AddCommentUseCase(comment_repo=comment_repo, post_repo=post_repo)
    comment = await add_uc.execute(post_id=post.id, author_id=author_id, body="Test")

    delete_uc = DeleteCommentUseCase(comment_repo)
    with pytest.raises(PermissionError):
        await delete_uc.execute(comment_id=comment.id, requesting_user_id=other_user_id)


@pytest.mark.asyncio
async def test_list_comments_excludes_deleted() -> None:
    post = _make_post()
    author_id = uuid.uuid4()
    comment_repo = FakeCommentRepository()
    post_repo = FakePostRepository(post)

    add_uc = AddCommentUseCase(comment_repo=comment_repo, post_repo=post_repo)
    c1 = await add_uc.execute(post_id=post.id, author_id=author_id, body="First")
    c2 = await add_uc.execute(post_id=post.id, author_id=author_id, body="Second")

    delete_uc = DeleteCommentUseCase(comment_repo)
    await delete_uc.execute(comment_id=c1.id, requesting_user_id=author_id)

    list_uc = ListCommentsUseCase(comment_repo)
    visible = await list_uc.execute(post_id=post.id)

    assert len(visible) == 1
    assert visible[0].id == c2.id
