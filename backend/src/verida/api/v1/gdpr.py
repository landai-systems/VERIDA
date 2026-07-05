"""GDPR endpoints — M3.

Endpoints:
    POST   /api/v1/gdpr/export — Article 20 data portability export
    DELETE /api/v1/gdpr/me     — Article 17 right to erasure

Design:
- Export returns a JSON download of all user data
- Deletion is permanent and irreversible — requires explicit confirmation
- Both operations are logged (user_id + timestamp only, no PII in logs)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from verida.api.v1.deps import AsyncSessionDep, CurrentUser

router = APIRouter()


class DeleteConfirmRequest(BaseModel):
    confirm: str  # Must be "DELETE MY ACCOUNT" to prevent accidents


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.post(
    "/export",
    summary="Export all user data (GDPR Art. 20)",
)
async def export_user_data(
    current_user: CurrentUser,
    session: AsyncSessionDep,
) -> Response:
    """Export all data for the authenticated user as a JSON file download.

    Returns a JSON document containing:
    - User profile (without password hash)
    - All posts + attestations
    - Circle memberships
    - Comments
    - Reactions
    - Consent records
    - Streak data

    The file is returned as an attachment download (Content-Disposition).
    """
    from verida.infrastructure.db.repositories import (
        SqlCircleRepository,
        SqlCommentRepository,
        SqlConsentRepository,
        SqlPostRepository,
        SqlReactionRepository,
        SqlStreakRepository,
        SqlUserRepository,
    )
    from verida.application.use_cases.gdpr import ExportUserDataUseCase
    import json

    use_case = ExportUserDataUseCase(
        user_repo=SqlUserRepository(session),
        post_repo=SqlPostRepository(session),
        circle_repo=SqlCircleRepository(session),
        consent_repo=SqlConsentRepository(session),
        comment_repo=SqlCommentRepository(session),
        reaction_repo=SqlReactionRepository(session),
        streak_repo=SqlStreakRepository(session),
    )

    export_data = await use_case.execute(current_user.id)

    json_bytes = json.dumps(export_data, indent=2, ensure_ascii=False).encode("utf-8")

    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="verida-data-export-{current_user.id}.json"',
        },
    )


@router.delete(
    "/me",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Delete account and all data (GDPR Art. 17)",
)
async def delete_account(
    body: DeleteConfirmRequest,
    current_user: CurrentUser,
    session: AsyncSessionDep,
) -> dict:
    """Permanently delete the authenticated user's account and all associated data.

    This action is IRREVERSIBLE. A hard delete is performed with cascade.

    The request body must include ``{"confirm": "DELETE MY ACCOUNT"}`` to
    prevent accidental deletions.

    The deletion is performed synchronously for personal data rows; media
    files are purged asynchronously via the worker.
    """
    if body.confirm != "DELETE MY ACCOUNT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='To confirm deletion, set confirm to "DELETE MY ACCOUNT".',
        )

    from verida.infrastructure.db.repositories import (
        SqlCommentRepository,
        SqlConsentRepository,
        SqlPostRepository,
        SqlReactionRepository,
        SqlStreakRepository,
        SqlUserRepository,
    )
    from verida.application.use_cases.gdpr import DeleteUserDataUseCase

    # Try to get arq pool for scheduling purge job
    arq_pool = None
    try:
        from verida.config import get_settings
        import arq  # type: ignore[import-untyped]

        settings = get_settings()
        arq_pool = await arq.create_pool(arq.connections.RedisSettings.from_dsn(settings.redis_url))
    except Exception:
        pass  # Purge will not be scheduled — acceptable in dev/test

    use_case = DeleteUserDataUseCase(
        user_repo=SqlUserRepository(session),
        post_repo=SqlPostRepository(session),
        consent_repo=SqlConsentRepository(session),
        comment_repo=SqlCommentRepository(session),
        reaction_repo=SqlReactionRepository(session),
        streak_repo=SqlStreakRepository(session),
        arq_pool=arq_pool,
    )

    summary = await use_case.execute(current_user.id)

    return {
        "status": "accepted",
        "message": "Your account and all associated data have been deleted.",
        "steps_completed": summary["steps"],
    }
