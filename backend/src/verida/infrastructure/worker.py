"""arq background worker — task definitions and scheduler.

Tasks
-----
attest_post
    - Loads the post from DB
    - Runs HeuristicAuthenticityChecker.attest()
    - Saves the resulting Attestation

send_daily_prompt
    - Scheduled per-user at a random time between 08:00 and 20:00 local time
    - Creates a DailyMoment record with a pre-generated capture token
    - (In production: push notification; for MVP: email via MailpitAdapter)

purge_expired_tokens
    - Deletes expired RefreshToken rows from the DB
    - Run nightly (cron-style via arq.cron)

Worker configuration
--------------------
    arq worker verida.infrastructure.worker.WorkerSettings

Environment variables consumed:
    REDIS_URL       — arq broker URL
    DATABASE_URL    — async PostgreSQL URL
    SECRET_KEY      — for HMAC capture token generation
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


async def _get_db_session() -> Any:
    """Create a standalone DB session for use inside arq workers."""
    from verida.infrastructure.db.session import async_session_factory

    return async_session_factory()


async def attest_post(ctx: dict[str, Any], post_id_str: str) -> None:
    """arq task: run content authenticity check on a submitted post.

    Parameters
    ----------
    ctx:
        arq context dict (contains the Redis pool).
    post_id_str:
        String representation of the post UUID.
    """
    from verida.infrastructure.db.repositories import (
        SqlAttestationRepository,
        SqlPostRepository,
    )
    from verida.infrastructure.heuristic_authenticity import HeuristicAuthenticityChecker

    post_id = uuid.UUID(post_id_str)
    checker = HeuristicAuthenticityChecker()

    async with await _get_db_session() as session:
        post_repo = SqlPostRepository(session)
        attestation_repo = SqlAttestationRepository(session)

        post = await post_repo.get_by_id(post_id)
        if post is None:
            logger.warning("attest_post_not_found", post_id=post_id_str)
            return

        attestation = await checker.attest(post)
        await attestation_repo.save(attestation)

    logger.info(
        "attest_post_complete",
        post_id=post_id_str,
        status=attestation.status.value,
        score=attestation.score,
    )


async def send_daily_prompt(ctx: dict[str, Any], user_id_str: str) -> None:
    """arq task: send (or enqueue) today's daily prompt for a user.

    This task is scheduled with a random delay per user so that not all
    users receive their prompt at the same moment (to prevent a traffic spike).

    The actual notification mechanism is a stub in MVP; in production this
    would send a push notification via FCM/APNs.
    """
    from verida.config import get_settings
    from verida.infrastructure.db.repositories import (
        SqlDailyMomentRepository,
        SqlUserRepository,
    )
    from verida.application.use_cases.daily_moment import InitiateCaptureUseCase

    settings = get_settings()
    user_id = uuid.UUID(user_id_str)

    async with await _get_db_session() as session:
        user_repo = SqlUserRepository(session)
        moment_repo = SqlDailyMomentRepository(session)
        post_repo_module = __import__(
            "verida.infrastructure.db.repositories",
            fromlist=["SqlPostRepository"],
        )
        SqlPostRepository = post_repo_module.SqlPostRepository  # noqa: N806

        user = await user_repo.get_by_id(user_id)
        if user is None or not user.is_active:
            logger.info("send_daily_prompt_skipped_inactive", user_id=user_id_str)
            return

        use_case = InitiateCaptureUseCase(
            daily_moment_repo=moment_repo,
            post_repo=SqlPostRepository(session),
            secret_key=settings.secret_key,
        )

        try:
            result = await use_case.execute(user_id=user_id)
            logger.info(
                "daily_prompt_sent",
                user_id=user_id_str,
                moment_id=result["moment_id"],
            )
        except ValueError:
            # User already posted today — skip
            logger.info("daily_prompt_skipped_already_posted", user_id=user_id_str)


async def purge_expired_tokens(ctx: dict[str, Any]) -> None:
    """arq cron task: delete expired refresh tokens from the database."""
    from verida.infrastructure.db.repositories import SqlRefreshTokenRepository

    async with await _get_db_session() as session:
        repo = SqlRefreshTokenRepository(session)
        deleted = await repo.delete_expired()

    logger.info("purge_expired_tokens_complete", deleted=deleted)


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup: configure logging."""
    from verida.config import get_settings
    import logging

    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
    logger.info("arq_worker_started")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown: close DB engine."""
    from verida.infrastructure.db.session import close_engine

    await close_engine()
    logger.info("arq_worker_stopped")


def _make_cron_jobs() -> list[Any]:
    """Build the list of scheduled arq cron jobs."""
    try:
        from arq.cron import cron  # type: ignore[import-untyped]

        return [
            # Purge expired tokens nightly at 02:00 UTC
            cron(purge_expired_tokens, hour={2}, minute={0}),
        ]
    except ImportError:
        return []


class WorkerSettings:
    """arq WorkerSettings — pass this class to ``arq worker``."""

    functions = [attest_post, send_daily_prompt, purge_expired_tokens]
    cron_jobs = _make_cron_jobs()
    on_startup = startup
    on_shutdown = shutdown

    @classmethod
    def get_redis_settings(cls) -> Any:
        from arq.connections import RedisSettings  # type: ignore[import-untyped]
        from verida.config import get_settings

        settings = get_settings()
        return RedisSettings.from_dsn(settings.redis_url)

    redis_settings = property(get_redis_settings)
