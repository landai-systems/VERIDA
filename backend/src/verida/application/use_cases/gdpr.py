"""GDPR use cases — M3.

Implements:
- Article 20 (Right to data portability): ExportUserDataUseCase
- Article 17 (Right to erasure): DeleteUserDataUseCase

Design:
- Export collects ALL user data into a single structured JSON document
- Deletion hard-deletes with cascade; async purge job handles orphaned media
- No soft-delete for personal data — we use actual DELETE statements
- Scheduled purge handles any data that couldn't be deleted synchronously

Privacy constraints:
- Exports include consent records (proof of lawful basis)
- Exports strip internal hashes not needed by the user (argon2_hash)
- All exports are logged for accountability
- Deletion is logged with user_id and timestamp only (no PII in logs)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ExportUserDataUseCase:
    """Collect all user data into a portable JSON document (GDPR Art. 20).

    Collects:
    - User profile (without password hash)
    - All posts + attestations + capture metadata
    - Circle memberships
    - Comments authored by user
    - Reactions by user
    - Consent records
    - Streak data

    Parameters
    ----------
    user_repo, post_repo, circle_repo, consent_repo,
    comment_repo, reaction_repo, streak_repo:
        Repositories for each entity type.
    """

    def __init__(
        self,
        user_repo: object,
        post_repo: object,
        circle_repo: object,
        consent_repo: object,
        comment_repo: object,
        reaction_repo: object,
        streak_repo: object,
    ) -> None:
        self._user_repo = user_repo
        self._post_repo = post_repo
        self._circle_repo = circle_repo
        self._consent_repo = consent_repo
        self._comment_repo = comment_repo
        self._reaction_repo = reaction_repo
        self._streak_repo = streak_repo

    async def execute(self, user_id: uuid.UUID) -> dict[str, Any]:
        """Export all data for the user.

        Returns
        -------
        dict:
            Structured JSON-serialisable export document.

        Raises
        ------
        ValueError:
            If user not found.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User not found: {user_id}")

        # Collect all data in parallel conceptually — in practice sequential
        # since we're in a single async transaction boundary
        posts = await self._post_repo.list_by_author(user_id, limit=10000)
        circles = await self._circle_repo.list_for_member(user_id)
        consent_records = await self._consent_repo.list_for_user(user_id)
        comments = await self._comment_repo.list_by_author(user_id, limit=10000)
        reactions = await self._reaction_repo.list_by_user(user_id, limit=10000)
        streak = await self._streak_repo.get_for_user(user_id)

        export = {
            "export_format_version": "1.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "gdpr_article": "Art. 20 — Right to data portability",
            "data_controller": "VERIDA (landai-systems)",
            "user": {
                "id": str(user.id),
                "handle": user.handle,
                "display_name": user.display_name,
                "email": user.email,
                "bio": user.bio,
                "avatar_url": user.avatar_url,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat(),
            },
            "posts": [
                {
                    "id": str(p.id),
                    "caption": p.caption,
                    "media_url": p.media_url,
                    "media_mime_type": p.media_mime_type,
                    "visibility": p.visibility.value,
                    "is_late": p.is_late,
                    "published_at": p.published_at.isoformat() if p.published_at else None,
                    "created_at": p.created_at.isoformat(),
                    "attestation": (
                        {
                            "status": p.attestation.status.value,
                            "score": p.attestation.score,
                            "checked_at": p.attestation.checked_at.isoformat()
                            if p.attestation.checked_at else None,
                        }
                        if p.attestation else None
                    ),
                }
                for p in posts
            ],
            "circles": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "description": c.description,
                    "is_owner": c.owner_id == user_id,
                }
                for c in circles
            ],
            "comments": [
                {
                    "id": str(c.id),
                    "post_id": str(c.post_id),
                    "body": c.body,
                    "created_at": c.created_at.isoformat(),
                    "deleted_at": c.deleted_at.isoformat() if c.deleted_at else None,
                }
                for c in comments
            ],
            "reactions": [
                {
                    "id": str(r.id),
                    "post_id": str(r.post_id),
                    "emoji": r.emoji.value,
                    "created_at": r.created_at.isoformat(),
                }
                for r in reactions
            ],
            "consent_records": [
                {
                    "id": str(cr.id),
                    "consent_type": cr.consent_type.value,
                    "version": cr.version,
                    "text_version": cr.text_version,
                    "granted_at": cr.granted_at.isoformat(),
                    "withdrawn_at": cr.withdrawn_at.isoformat() if cr.withdrawn_at else None,
                }
                for cr in consent_records
            ],
            "streak": (
                {
                    "current_streak": streak.current_streak,
                    "longest_streak": streak.longest_streak,
                    "last_post_date": streak.last_post_date.isoformat()
                    if streak.last_post_date else None,
                }
                if streak else None
            ),
        }

        logger.info(
            "gdpr_export_complete",
            user_id=str(user_id),
            posts_count=len(posts),
            comments_count=len(comments),
            reactions_count=len(reactions),
        )

        return export


class DeleteUserDataUseCase:
    """Hard-delete all user data (GDPR Art. 17 — Right to erasure).

    Cascade strategy:
    1. Mark user as deleted (is_active=False) immediately — stops login
    2. Delete directly-owned personal data: posts, consent records, reactions,
       comments, streaks
    3. Schedule async purge job for media files and any deferred cleanup
    4. Hard-delete the User row (cascade handles FK relations via ON DELETE CASCADE)

    The user_id is enqueued in Redis for the purge worker to pick up.

    Parameters
    ----------
    user_repo, post_repo, consent_repo, comment_repo, reaction_repo, streak_repo:
        Repositories for cascade deletion.
    arq_pool:
        Optional arq Redis pool for scheduling the async purge job.
    """

    def __init__(
        self,
        user_repo: object,
        post_repo: object,
        consent_repo: object,
        comment_repo: object,
        reaction_repo: object,
        streak_repo: object,
        arq_pool: Any = None,
    ) -> None:
        self._user_repo = user_repo
        self._post_repo = post_repo
        self._consent_repo = consent_repo
        self._comment_repo = comment_repo
        self._reaction_repo = reaction_repo
        self._streak_repo = streak_repo
        self._arq_pool = arq_pool

    async def execute(self, user_id: uuid.UUID) -> dict[str, Any]:
        """Delete all user data.

        Returns
        -------
        dict:
            Summary of what was deleted and scheduled for purge.

        Raises
        ------
        ValueError:
            If user not found.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User not found: {user_id}")

        summary: dict[str, Any] = {
            "user_id": str(user_id),
            "deleted_at": datetime.now(UTC).isoformat(),
            "steps": [],
        }

        # Step 1: Deactivate immediately (prevents login during deletion)
        user.is_active = False
        await self._user_repo.save(user)
        summary["steps"].append("user_deactivated")

        # Step 2: Delete personal data rows (FK CASCADE handles related tables)
        # Comments (authored by user)
        await self._comment_repo.delete_all_by_author(user_id)
        summary["steps"].append("comments_deleted")

        # Reactions
        await self._reaction_repo.delete_all_by_user(user_id)
        summary["steps"].append("reactions_deleted")

        # Streak
        await self._streak_repo.delete_for_user(user_id)
        summary["steps"].append("streak_deleted")

        # Consent records — kept for legal accountability per Art. 5(2)
        # We anonymise rather than delete: set user_id to NULL-equivalent
        # Actually: GDPR allows retention of consent records for accountability
        # We keep them but they'll cascade-delete with the user row anyway
        summary["steps"].append("consent_records_cascade_with_user")

        # Step 3: Schedule async purge (media files, deferred cleanup)
        if self._arq_pool is not None:
            await self._arq_pool.enqueue_job(
                "purge_deleted_user_data", str(user_id)
            )
            summary["steps"].append("purge_job_scheduled")
        else:
            summary["steps"].append("purge_job_not_scheduled_no_pool")

        # Step 4: Hard delete the user row (CASCADE deletes posts, tokens, etc.)
        await self._user_repo.delete(user_id)
        summary["steps"].append("user_row_deleted")

        logger.info(
            "gdpr_erasure_complete",
            user_id=str(user_id),
            steps=summary["steps"],
        )

        return summary
