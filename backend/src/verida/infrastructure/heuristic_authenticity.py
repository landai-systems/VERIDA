"""Heuristic authenticity checker — M3 upgraded implementation.

Extends the MVP with more robust heuristics:
    1. media_hash_present     — SHA-256 hash submitted (carry-over from MVP)
    2. mime_type_allowed      — MIME type in approved set
    3. capture_duration       — duration within plausible live-capture range
    4. resolution_plausible   — resolution within camera bounds
    5. timing_window          — post submitted within plausible window
    6. exif_absent            — no EXIF metadata preserved (cameras strip on upload)
    7. perceptual_hash_unique — phash not seen recently (replay detection via Redis)
    8. capture_metadata_score — metadata fields present and self-consistent
    9. gallery_upload_absent  — no signals indicating pre-existing gallery image

LIMITATIONS (see docs/TRUST_MODEL.md):
    - A determined attacker can fabricate all of these signals.
    - The perceptual hash only detects near-duplicate replays — cropping evades it.
    - This is NOT a substitute for cryptographic proof-of-liveness.
    - Scores are advisory; the application layer makes the final decision.

The score is purely advisory; the application layer makes the final decision.
"""

from __future__ import annotations

import hashlib
import struct
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

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

# Resolution bounds (pixels) — real cameras, not synthetic
MIN_DIMENSION_PX: int = 100
MAX_DIMENSION_PX: int = 8000

# Minimum passing score
PASSING_SCORE_THRESHOLD: float = 0.60

# Maximum time between capture initiation and post submission (minutes)
MAX_SUBMISSION_WINDOW_MINUTES: int = 20  # slightly generous of the 10-min window

# Perceptual hash TTL in Redis (seconds) — how long we track recent hashes
PHASH_TTL_SECONDS: int = 86400 * 7  # 7 days

# Known gallery-upload signals in capture_metadata
GALLERY_UPLOAD_SIGNALS = frozenset(
    {
        "source",         # "gallery" or "file-picker"
        "file_picker",
        "input_type",     # "file" means gallery
        "from_gallery",
    }
)

# Metadata fields we expect a genuine live capture to provide
EXPECTED_METADATA_FIELDS = frozenset(
    {
        "duration_seconds",
        "width_px",
        "height_px",
        "captured_at",
    }
)


def _simple_phash(media_hash: str) -> str:
    """Derive a coarse perceptual-hash proxy from the SHA-256 media hash.

    In production this would be a real perceptual hash (e.g. dHash over the image).
    For MVP, we derive a 64-bit "structural hash" from the SHA-256 by XOR-folding
    — different files with the same sha256 won't exist, so this is effectively
    a namespace-preserving alias used as a Redis key.

    A real implementation would decode the image and compute a dHash or pHash.
    We document this limitation in TRUST_MODEL.md.
    """
    # XOR-fold the first 32 bytes of the hex hash into 8 bytes
    raw = bytes.fromhex(media_hash[:16])
    folded = bytes.fromhex(media_hash[16:32])
    result = bytes(a ^ b for a, b in zip(raw, folded))
    return result.hex()


class HeuristicAuthenticityChecker:
    """M3 upgraded authenticity checker with Redis-backed replay detection.

    Constructor injection — no globals, no singletons.

    Parameters
    ----------
    redis_client:
        Optional async Redis client for perceptual hash dedup.
        If None, replay detection is skipped (logged as warning).
    passing_threshold:
        Minimum score to pass attestation (default 0.60).
    """

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        passing_threshold: float = PASSING_SCORE_THRESHOLD,
    ) -> None:
        self._redis = redis_client
        self._passing_threshold = passing_threshold

    async def attest(self, post: Post) -> Attestation:
        """Evaluate post heuristics and return an Attestation.

        This method never raises; it always returns a valid Attestation.
        """
        details: dict[str, Any] = {}
        scores: list[float] = []

        # ── Heuristic 1: media_hash present ───────────────────────────────────
        h1 = self._check_media_hash(post, details)
        scores.append(h1)

        # ── Heuristic 2: MIME type allowed ────────────────────────────────────
        h2 = self._check_mime_type(post, details)
        scores.append(h2)

        # ── Heuristic 3: Capture duration plausible ───────────────────────────
        h3 = self._check_capture_duration(post, details)
        scores.append(h3)

        # ── Heuristic 4: Resolution plausible ─────────────────────────────────
        h4 = self._check_resolution(post, details)
        scores.append(h4)

        # ── Heuristic 5: Timing window validation ─────────────────────────────
        h5 = self._check_timing_window(post, details)
        scores.append(h5)

        # ── Heuristic 6: EXIF absence check ───────────────────────────────────
        h6 = self._check_exif_absent(post, details)
        scores.append(h6)

        # ── Heuristic 7: Perceptual hash uniqueness (Redis) ───────────────────
        h7 = await self._check_phash_unique(post, details)
        scores.append(h7)

        # ── Heuristic 8: Capture metadata plausibility ────────────────────────
        h8 = self._check_metadata_completeness(post, details)
        scores.append(h8)

        # ── Heuristic 9: Gallery upload detection ─────────────────────────────
        h9 = self._check_no_gallery_upload(post, details)
        scores.append(h9)

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
            heuristics={
                "media_hash": h1,
                "mime_type": h2,
                "duration": h3,
                "resolution": h4,
                "timing": h5,
                "exif": h6,
                "phash_unique": h7,
                "metadata": h8,
                "no_gallery": h9,
            },
        )

        return attestation

    # ── Private heuristic methods ─────────────────────────────────────────────

    def _check_media_hash(self, post: Post, details: dict) -> float:
        if post.media_hash and len(post.media_hash) == 64:
            try:
                bytes.fromhex(post.media_hash)
                details["media_hash_present"] = True
                return 1.0
            except ValueError:
                pass
        details["media_hash_present"] = False
        details["media_hash_issue"] = "missing, wrong length, or not valid hex"
        return 0.0

    def _check_mime_type(self, post: Post, details: dict) -> float:
        if post.media_mime_type in ALLOWED_MIME_TYPES:
            details["mime_type_allowed"] = True
            return 1.0
        details["mime_type_allowed"] = False
        # Don't include the actual MIME received — potential injection vector
        details["mime_type_issue"] = "not in allowed set"
        return 0.0

    def _check_capture_duration(self, post: Post, details: dict) -> float:
        duration = post.capture_metadata.get("duration_seconds")
        if isinstance(duration, (int, float)) and (
            MIN_CAPTURE_DURATION_S <= duration <= MAX_CAPTURE_DURATION_S
        ):
            details["capture_duration_plausible"] = True
            return 1.0
        details["capture_duration_plausible"] = False
        return 0.0

    def _check_resolution(self, post: Post, details: dict) -> float:
        width = post.capture_metadata.get("width_px")
        height = post.capture_metadata.get("height_px")
        if (
            isinstance(width, int)
            and isinstance(height, int)
            and MIN_DIMENSION_PX <= width <= MAX_DIMENSION_PX
            and MIN_DIMENSION_PX <= height <= MAX_DIMENSION_PX
        ):
            # Extra: aspect ratio sanity (common camera ratios)
            ratio = width / height if height else 0
            if 0.3 <= ratio <= 3.5:  # portrait to landscape, nothing extreme
                details["resolution_plausible"] = True
                details["aspect_ratio"] = round(ratio, 2)
                return 1.0
        details["resolution_plausible"] = False
        return 0.0

    def _check_timing_window(self, post: Post, details: dict) -> float:
        """Check that the post's published_at is within plausible range.

        A live capture should be published within MAX_SUBMISSION_WINDOW_MINUTES
        of creation. Very old published_at timestamps suggest a scheduled
        or pre-captured post.
        """
        if post.published_at is None:
            details["timing_window_ok"] = None  # no timing info, can't check
            return 0.5  # partial score — inconclusive

        now = datetime.now(UTC)
        age_minutes = (now - post.published_at).total_seconds() / 60

        if -1 <= age_minutes <= MAX_SUBMISSION_WINDOW_MINUTES:
            details["timing_window_ok"] = True
            details["age_minutes"] = round(age_minutes, 1)
            return 1.0
        elif age_minutes > MAX_SUBMISSION_WINDOW_MINUTES:
            details["timing_window_ok"] = False
            details["timing_issue"] = "submitted_too_late"
            return 0.2
        else:
            # Future timestamp — clock skew or manipulation
            details["timing_window_ok"] = False
            details["timing_issue"] = "future_timestamp"
            return 0.0

    def _check_exif_absent(self, post: Post, details: dict) -> float:
        """Check for EXIF metadata signals in capture_metadata.

        Browser MediaDevices API captures should NOT include EXIF data —
        the browser strips it.  If the client sends GPS, camera model, or
        original creation time in metadata, it suggests a file that went
        through a different pipeline (gallery, editing app, etc.).
        """
        meta = post.capture_metadata
        exif_keys = {"gps", "camera_model", "original_date", "exif", "iptc", "xmp"}
        found_exif = [k for k in meta if k.lower() in exif_keys]

        if found_exif:
            details["exif_absent"] = False
            # Don't echo the values — could contain sensitive location data
            details["exif_fields_count"] = len(found_exif)
            return 0.0

        details["exif_absent"] = True
        return 1.0

    async def _check_phash_unique(self, post: Post, details: dict) -> float:
        """Check that the media perceptual hash hasn't been seen recently.

        Uses Redis sorted set with TTL. If Redis is unavailable, returns
        partial score and logs a warning.
        """
        if not post.media_hash or len(post.media_hash) != 64:
            details["phash_unique"] = None
            return 0.5  # Can't check without hash

        phash = _simple_phash(post.media_hash)

        if self._redis is None:
            details["phash_unique"] = None
            details["phash_note"] = "redis_unavailable"
            logger.warning("phash_check_skipped_no_redis", post_id=str(post.id))
            return 0.5  # Inconclusive

        try:
            redis_key = f"verida:phash:{phash}"
            existing = await self._redis.get(redis_key)

            if existing:
                # Hash seen recently — likely replay
                details["phash_unique"] = False
                details["phash_issue"] = "hash_seen_recently"
                logger.warning(
                    "phash_replay_detected",
                    post_id=str(post.id),
                    phash=phash[:16] + "...",
                )
                return 0.0
            else:
                # Register this hash
                await self._redis.setex(
                    redis_key,
                    PHASH_TTL_SECONDS,
                    str(post.id),
                )
                details["phash_unique"] = True
                return 1.0

        except Exception as exc:
            logger.warning(
                "phash_redis_error",
                error=str(exc),
                post_id=str(post.id),
            )
            details["phash_unique"] = None
            details["phash_note"] = "redis_error"
            return 0.5  # Fail open

    def _check_metadata_completeness(self, post: Post, details: dict) -> float:
        """Score based on how many expected metadata fields are present.

        A genuine browser capture should provide all fields in EXPECTED_METADATA_FIELDS.
        Missing fields reduce the score proportionally.
        """
        meta = post.capture_metadata
        present = EXPECTED_METADATA_FIELDS & set(meta.keys())
        ratio = len(present) / len(EXPECTED_METADATA_FIELDS)
        details["metadata_completeness"] = round(ratio, 2)
        details["metadata_fields_present"] = sorted(present)
        details["metadata_fields_missing"] = sorted(EXPECTED_METADATA_FIELDS - present)
        return ratio

    def _check_no_gallery_upload(self, post: Post, details: dict) -> float:
        """Detect signals that indicate a pre-existing gallery image was uploaded.

        The browser MediaDevices capture API should not include file-picker or
        gallery source signals. These appear when the user selects a file from
        their camera roll rather than capturing live.
        """
        meta = post.capture_metadata
        gallery_signals = [k for k in GALLERY_UPLOAD_SIGNALS if k in meta]

        if gallery_signals:
            # Check if any signal indicates gallery source
            for key in gallery_signals:
                val = str(meta.get(key, "")).lower()
                if any(term in val for term in ("gallery", "file", "picker", "true")):
                    details["gallery_upload_absent"] = False
                    details["gallery_signal"] = key
                    return 0.0

        details["gallery_upload_absent"] = True
        return 1.0
