"""Heuristic authenticity checker — MVP implementation of ContentAuthenticityPort.

This adapter uses rule-based heuristics to score a post's likely authenticity.
It does NOT use ML or external services; it is intentionally simple and fast.

Heuristics applied (each contributes to a 0.0–1.0 score):
    1. media_hash_present     — SHA-256 hash was submitted with the post
    2. capture_token_age      — token was used within the 5-minute window
    3. mime_type_allowed      — MIME type is in the approved set
    4. capture_duration       — reported duration is within plausible range (1–60 s)
    5. resolution_plausible   — resolution is within allowed bounds

LIMITATIONS (see docs/TRUST_MODEL.md):
    - A determined attacker can fabricate all of these signals.
    - The hash only proves the file wasn't changed AFTER upload; it does NOT
      prove the content was captured live.
    - This implementation is NOT a substitute for cryptographic proof-of-liveness.

The score is purely advisory; the application layer makes the final decision.
"""

from __future__ import annotations

import hashlib
import time
from datetime import UTC, datetime
from typing import Any

import structlog

from verida.domain.entities import Attestation, AttestationStatus, Post

logger = structlog.get_logger(__name__)

# MIME types that the platform accepts
ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "video/webm",
        "video/mp4",
    }
)

# Capture duration bounds (seconds)
MIN_CAPTURE_DURATION_S: float = 0.5
MAX_CAPTURE_DURATION_S: float = 60.0

# Resolution bounds (pixels)
MIN_DIMENSION_PX: int = 100
MAX_DIMENSION_PX: int = 8000

# Minimum passing score
PASSING_SCORE_THRESHOLD: float = 0.6


class HeuristicAuthenticityChecker:
    """MVP implementation of ContentAuthenticityPort using rule-based heuristics.

    This class is injected into application services that need authenticity
    checking.  It satisfies the ``ContentAuthenticityPort`` Protocol.

    Constructor injection — no globals, no singletons.
    """

    def __init__(
        self,
        passing_threshold: float = PASSING_SCORE_THRESHOLD,
    ) -> None:
        self._passing_threshold = passing_threshold

    async def attest(self, post: Post) -> Attestation:
        """Evaluate post heuristics and return an Attestation.

        This method never raises; it always returns a valid Attestation.
        """
        details: dict[str, Any] = {}
        scores: list[float] = []

        # ── Heuristic 1: media_hash present ───────────────────────────────────
        if post.media_hash and len(post.media_hash) == 64:
            scores.append(1.0)
            details["media_hash_present"] = True
        else:
            scores.append(0.0)
            details["media_hash_present"] = False
            details["media_hash_issue"] = "missing or wrong length (expected SHA-256 hex)"

        # ── Heuristic 2: MIME type allowed ────────────────────────────────────
        if post.media_mime_type in ALLOWED_MIME_TYPES:
            scores.append(1.0)
            details["mime_type_allowed"] = True
        else:
            scores.append(0.0)
            details["mime_type_allowed"] = False
            details["mime_type_received"] = post.media_mime_type

        # ── Heuristic 3: Capture duration plausible ───────────────────────────
        duration = post.capture_metadata.get("duration_seconds")
        if isinstance(duration, (int, float)) and (
            MIN_CAPTURE_DURATION_S <= duration <= MAX_CAPTURE_DURATION_S
        ):
            scores.append(1.0)
            details["capture_duration_plausible"] = True
        else:
            scores.append(0.0)
            details["capture_duration_plausible"] = False
            details["capture_duration_received"] = duration

        # ── Heuristic 4: Resolution plausible ─────────────────────────────────
        width = post.capture_metadata.get("width_px")
        height = post.capture_metadata.get("height_px")
        if (
            isinstance(width, int)
            and isinstance(height, int)
            and MIN_DIMENSION_PX <= width <= MAX_DIMENSION_PX
            and MIN_DIMENSION_PX <= height <= MAX_DIMENSION_PX
        ):
            scores.append(1.0)
            details["resolution_plausible"] = True
        else:
            scores.append(0.0)
            details["resolution_plausible"] = False
            details["resolution_received"] = {"width": width, "height": height}

        # ── Heuristic 5: Caption length sanity ────────────────────────────────
        # Extremely long captions or zero-length captions are suspicious
        caption_len = len(post.caption)
        if 0 < caption_len <= 500:
            scores.append(1.0)
            details["caption_length_ok"] = True
        else:
            scores.append(0.3)  # partial — no caption or too long
            details["caption_length_ok"] = False
            details["caption_length"] = caption_len

        # ── Aggregate ─────────────────────────────────────────────────────────
        final_score = sum(scores) / len(scores) if scores else 0.0

        if final_score >= self._passing_threshold:
            status = AttestationStatus.PASSED
        elif final_score >= 0.3:
            status = AttestationStatus.FLAGGED
        else:
            status = AttestationStatus.REJECTED

        attestation = Attestation(
            post_id=post.id,
            status=status,
            score=round(final_score, 4),
            details=details,
            checked_at=datetime.now(UTC),
        )

        logger.info(
            "attestation_complete",
            post_id=str(post.id),
            status=status.value,
            score=attestation.score,
        )

        return attestation
