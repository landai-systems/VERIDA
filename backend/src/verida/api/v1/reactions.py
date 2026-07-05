"""Reactions API — M3.

Endpoints:
    GET    /api/v1/posts/{post_id}/reactions  — get current user's reactions
    POST   /api/v1/posts/{post_id}/reactions  — add a reaction
    DELETE /api/v1/posts/{post_id}/reactions  — remove a reaction

MVP privacy constraint: NO public reaction counters.
Only the authenticated user's own reactions are returned.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from verida.api.v1.deps import AsyncSessionDep, CurrentUser
from verida.application.use_cases.reactions import (
    AddReactionUseCase,
    GetReactionsUseCase,
    RemoveReactionUseCase,
)
from verida.domain.entities import ReactionEmoji

router = APIRouter()


class ReactionRequest(BaseModel):
    emoji: ReactionEmoji


class ReactionResponse(BaseModel):
    id: str
    post_id: str
    emoji: str


@router.get(
    "/{post_id}/reactions",
    response_model=list[ReactionResponse],
    summary="Get my reactions on a post (no public counters)",
)
async def get_reactions(
    post_id: UUID,
    current_user: CurrentUser,
    session: AsyncSessionDep,
) -> list[ReactionResponse]:
    """Return only the current user's reactions on this post.

    Public reaction counts are not available in MVP — only personal reactions.
    """
    from verida.infrastructure.db.repositories import SqlReactionRepository

    repo = SqlReactionRepository(session)
    use_case = GetReactionsUseCase(repo)
    reactions = await use_case.execute(post_id=post_id, current_user_id=current_user.id)

    return [
        ReactionResponse(id=str(r.id), post_id=str(r.post_id), emoji=r.emoji.value)
        for r in reactions
    ]


@router.post(
    "/{post_id}/reactions",
    response_model=ReactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a reaction to a post",
)
async def add_reaction(
    post_id: UUID,
    body: ReactionRequest,
    current_user: CurrentUser,
    session: AsyncSessionDep,
) -> ReactionResponse:
    """Add a reaction to a post. Idempotent — adding the same emoji twice returns the existing one."""
    from verida.infrastructure.db.repositories import SqlReactionRepository

    repo = SqlReactionRepository(session)
    use_case = AddReactionUseCase(repo)
    reaction = await use_case.execute(
        post_id=post_id,
        user_id=current_user.id,
        emoji=body.emoji,
    )
    return ReactionResponse(id=str(reaction.id), post_id=str(reaction.post_id), emoji=reaction.emoji.value)


@router.delete(
    "/{post_id}/reactions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a reaction from a post",
)
async def remove_reaction(
    post_id: UUID,
    body: ReactionRequest,
    current_user: CurrentUser,
    session: AsyncSessionDep,
) -> None:
    """Remove the current user's reaction of the specified emoji from a post."""
    from verida.infrastructure.db.repositories import SqlReactionRepository

    repo = SqlReactionRepository(session)
    use_case = RemoveReactionUseCase(repo)
    removed = await use_case.execute(
        post_id=post_id,
        user_id=current_user.id,
        emoji=body.emoji,
    )
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reaction not found.",
        )
