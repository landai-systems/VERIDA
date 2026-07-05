"""Reactions use cases — M3.

MVP constraints:
- Warm emoji set only: ❤️ 😊 🔥 🌟 🤗
- ONE reaction of each type per user per post (unique constraint at DB + app layer)
- NO public reaction counters — only return whether CURRENT USER reacted
- Adding the same emoji twice is idempotent (returns existing)

Privacy rationale: public counters create social competition and pressure.
By only showing "did I react?", we keep reactions as personal expression.
"""

from __future__ import annotations

import uuid
from typing import Optional

import structlog

from verida.domain.entities import Reaction, ReactionEmoji

logger = structlog.get_logger(__name__)


class AddReactionUseCase:
    """Add a reaction to a post.

    Idempotent: if the user already reacted with the same emoji, returns
    the existing reaction without creating a duplicate.
    """

    def __init__(self, reaction_repo: object) -> None:
        self._repo = reaction_repo

    async def execute(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID,
        emoji: ReactionEmoji,
    ) -> Reaction:
        # Check for existing reaction of this type
        existing = await self._repo.get(post_id=post_id, user_id=user_id, emoji=emoji)
        if existing:
            return existing

        reaction = Reaction(
            post_id=post_id,
            user_id=user_id,
            emoji=emoji,
        )
        await self._repo.save(reaction)

        logger.info(
            "reaction_added",
            post_id=str(post_id),
            user_id=str(user_id),
            emoji=emoji.value,
        )
        return reaction


class RemoveReactionUseCase:
    """Remove a user's reaction from a post."""

    def __init__(self, reaction_repo: object) -> None:
        self._repo = reaction_repo

    async def execute(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID,
        emoji: ReactionEmoji,
    ) -> bool:
        """Remove the reaction. Returns True if it existed and was removed."""
        existing = await self._repo.get(post_id=post_id, user_id=user_id, emoji=emoji)
        if not existing:
            return False

        await self._repo.delete(existing.id)

        logger.info(
            "reaction_removed",
            post_id=str(post_id),
            user_id=str(user_id),
            emoji=emoji.value,
        )
        return True


class GetReactionsUseCase:
    """Get reactions on a post — only the current user's own reactions.

    IMPORTANT: This use case intentionally returns ONLY the current user's
    reactions, not totals or other users' reactions. See docs/ENGAGEMENT.md.
    """

    def __init__(self, reaction_repo: object) -> None:
        self._repo = reaction_repo

    async def execute(
        self,
        post_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> list[Reaction]:
        """Return which emojis the current user has reacted with on this post.

        Returns
        -------
        list[Reaction]:
            The current user's reactions only. Empty list = no reactions.
            Other users' reactions are NOT included.
        """
        return await self._repo.list_by_user_on_post(
            post_id=post_id,
            user_id=current_user_id,
        )
