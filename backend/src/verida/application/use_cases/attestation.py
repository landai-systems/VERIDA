"""AttestationUseCase — orchestrates content authenticity checking.

Coordinates:
1. Loading the post from the repository
2. Running the HeuristicAuthenticityChecker
3. Saving the Attestation result
4. Returning the attestation

This is a thin orchestration layer — the actual heuristic logic lives in
the infrastructure adapter (HeuristicAuthenticityChecker).
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from verida.application.ports import AttestationRepository, ContentAuthenticityPort, PostRepository
from verida.domain.entities import Attestation, AttestationStatus

logger = structlog.get_logger(__name__)


class AttestationUseCase:
    """Run content authenticity check on a submitted post.

    Parameters
    ----------
    post_repo:
        Repository for loading the post to be attested.
    attestation_repo:
        Repository for saving the attestation result.
    authenticity_checker:
        The authenticity port implementation (heuristics or future ML model).
    """

    def __init__(
        self,
        post_repo: PostRepository,
        attestation_repo: AttestationRepository,
        authenticity_checker: ContentAuthenticityPort,
    ) -> None:
        self._post_repo = post_repo
        self._attestation_repo = attestation_repo
        self._checker = authenticity_checker

    async def execute(self, post_id: uuid.UUID) -> Attestation:
        """Run attestation on a post and persist the result.

        Parameters
        ----------
        post_id:
            UUID of the post to attest.

        Returns
        -------
        Attestation:
            The completed attestation entity.

        Raises
        ------
        ValueError:
            If the post does not exist.
        """
        post = await self._post_repo.get_by_id(post_id)
        if post is None:
            raise ValueError(f"Post not found: {post_id}")

        # Check if already attested (idempotency)
        existing = await self._attestation_repo.get_by_post_id(post_id)
        if existing and existing.status != AttestationStatus.PENDING:
            logger.info(
                "attestation_already_complete",
                post_id=str(post_id),
                status=existing.status.value,
            )
            return existing

        # Run the authenticity check
        attestation = await self._checker.attest(post)

        # Persist result
        await self._attestation_repo.save(attestation)

        logger.info(
            "attestation_use_case_complete",
            post_id=str(post_id),
            status=attestation.status.value,
            score=attestation.score,
        )

        return attestation
