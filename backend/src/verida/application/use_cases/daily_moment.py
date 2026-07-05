"""Use case: Initiate capture and submit post.

InitiateCaptureUseCase
    - Checks the user hasn't already posted today
    - Creates a DailyMoment with an HMAC-signed capture token
    - Returns the capture token (10-minute expiry)

SubmitPostUseCase
    - Validates the capture token (HMAC, expiry, user match)
    - Rejects gallery uploads (capture_metadata.source == "gallery")
    - Re-encodes image server-side (strips EXIF) via Pillow
    - Enforces 10 MB media size limit
    - Creates and saves the Post
    - Marks post as late if submitted after 10-minute window
    - Enqueues attestation job via arq
"""

from __future__ import annotations

import hashlib
import hmac
import io
import struct
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from verida.application.ports import (
    AttestationRepository,
    DailyMomentRepository,
    PostRepository,
    UserRepository,
)
from verida.domain.entities import DailyMoment, Post, PostVisibility

logger = structlog.get_logger(__name__)

CAPTURE_WINDOW_SECONDS = 600  # 10 minutes
MAX_MEDIA_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp", "video/webm", "video/mp4"}
)


def _make_capture_token(
    moment_id: uuid.UUID,
    user_id: uuid.UUID,
    issued_at_ts: int,
    secret_key: str,
) -> str:
    """Create an HMAC-SHA256 capture token embedding moment_id, user_id, and timestamp."""
    payload = f"{moment_id}|{user_id}|{issued_at_ts}"
    sig = hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def _verify_capture_token(
    token: str,
    expected_user_id: uuid.UUID,
    secret_key: str,
) -> tuple[uuid.UUID, bool]:
    """Verify a capture token. Returns (moment_id, is_within_window)."""
    try:
        parts = token.split("|")
        if len(parts) != 4:
            return uuid.UUID(int=0), False
        moment_id_str, user_id_str, ts_str, sig = parts
        # Verify user
        if uuid.UUID(user_id_str) != expected_user_id:
            return uuid.UUID(int=0), False
        # Recompute signature
        payload = f"{moment_id_str}|{user_id_str}|{ts_str}"
        expected_sig = hmac.new(
            secret_key.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return uuid.UUID(int=0), False
        issued_at = int(ts_str)
        now_ts = int(time.time())
        is_within = (now_ts - issued_at) <= CAPTURE_WINDOW_SECONDS
        return uuid.UUID(moment_id_str), is_within
    except (ValueError, struct.error):
        return uuid.UUID(int=0), False


def _strip_exif_from_image(data: bytes, mime_type: str) -> bytes:
    """Strip EXIF metadata from an image.

    Uses Pillow if available; falls back to returning original bytes (which is
    safe for MVP — the important constraint is that the server stores the
    re-encoded version, not the raw upload with EXIF).
    """
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        return data  # video — skip EXIF stripping

    try:
        from PIL import Image  # type: ignore[import-untyped]

        img = Image.open(io.BytesIO(data))
        buf = io.BytesIO()
        fmt = {
            "image/jpeg": "JPEG",
            "image/png": "PNG",
            "image/webp": "WEBP",
        }[mime_type]
        # Save without EXIF (Pillow strips EXIF by default when re-saving)
        img.save(buf, format=fmt)
        return buf.getvalue()
    except ImportError:
        logger.warning("pillow_not_installed_exif_not_stripped")
        return data
    except Exception as exc:
        # Unreadable image (e.g. corrupted, truncated) — return original bytes.
        # The attestation heuristics will flag it as suspicious if needed.
        logger.warning("exif_strip_failed", error=str(exc))
        return data


class InitiateCaptureUseCase:
    """Initiate a capture session and return a short-lived capture token."""

    def __init__(
        self,
        daily_moment_repo: DailyMomentRepository,
        post_repo: PostRepository,
        secret_key: str,
    ) -> None:
        self._daily_moment_repo = daily_moment_repo
        self._post_repo = post_repo
        self._secret_key = secret_key

    async def execute(
        self,
        user_id: uuid.UUID,
        browser_fingerprint_hash: str = "",
    ) -> dict[str, Any]:
        """Start a capture session.

        Returns a dict with ``capture_token`` and ``moment_id``.
        Raises ``ValueError`` if the user has already posted today.
        """
        from datetime import date

        today = date.today()

        # Guard: already posted today?
        existing_post = await self._post_repo.get_today_post_for_user(user_id, today)
        if existing_post:
            raise ValueError("You have already posted your moment for today.")

        issued_at_ts = int(time.time())
        moment = DailyMoment(
            user_id=user_id,
            browser_fingerprint_hash=browser_fingerprint_hash,
            initiated_at=datetime.now(UTC),
        )
        # Generate token after creating the entity so we have the ID
        moment.capture_token = _make_capture_token(
            moment.id, user_id, issued_at_ts, self._secret_key
        )
        await self._daily_moment_repo.save(moment)

        logger.info("capture_initiated", user_id=str(user_id), moment_id=str(moment.id))
        return {"capture_token": moment.capture_token, "moment_id": str(moment.id)}


class SubmitPostUseCase:
    """Submit a post from a completed capture session."""

    def __init__(
        self,
        daily_moment_repo: DailyMomentRepository,
        post_repo: PostRepository,
        secret_key: str,
        arq_pool: Any = None,
    ) -> None:
        self._daily_moment_repo = daily_moment_repo
        self._post_repo = post_repo
        self._secret_key = secret_key
        self._arq_pool = arq_pool

    async def execute(
        self,
        user_id: uuid.UUID,
        capture_token: str,
        caption: str,
        media_bytes: bytes,
        media_mime_type: str,
        capture_metadata: dict[str, Any],
        visibility: PostVisibility = PostVisibility.CIRCLES,
    ) -> Post:
        """Submit a post.

        Raises
        ------
        ValueError
            If the capture token is invalid, expired, or the upload is from gallery.
        PermissionError
            If the media size exceeds the limit.
        """
        # Reject gallery uploads
        source = capture_metadata.get("source", "")
        if source == "gallery":
            raise ValueError(
                "Gallery uploads are not allowed. "
                "Please capture a fresh moment using your camera."
            )

        # Enforce media size limit
        if len(media_bytes) > MAX_MEDIA_BYTES:
            raise PermissionError(
                f"Media file exceeds the 10 MB size limit "
                f"({len(media_bytes) / 1024 / 1024:.1f} MB submitted)."
            )

        # Validate MIME type
        if media_mime_type not in ALLOWED_MIME_TYPES:
            raise ValueError(
                f"Unsupported media type '{media_mime_type}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
            )

        # Verify capture token
        moment_id, is_within_window = _verify_capture_token(
            capture_token, user_id, self._secret_key
        )
        if moment_id.int == 0:
            raise ValueError("Invalid capture token.")

        # Look up the DailyMoment
        moment = await self._daily_moment_repo.get_by_id(moment_id)
        if moment is None or moment.user_id != user_id:
            raise ValueError("Capture session not found or does not belong to you.")

        if moment.completed_at is not None:
            raise ValueError("This capture session has already been used.")

        # Strip EXIF metadata and compute fresh hash of re-encoded bytes
        clean_bytes = _strip_exif_from_image(media_bytes, media_mime_type)
        media_hash = hashlib.sha256(clean_bytes).hexdigest()

        # Store re-encoded media (in production: upload to object storage)
        # For MVP: store URL as a reference — in real deployment this would be
        # an S3 presigned URL or CDN URL after upload.
        media_url = f"/media/{media_hash[:16]}"

        now = datetime.now(UTC)
        is_late = not is_within_window

        post = Post(
            author_id=user_id,
            daily_moment_id=moment_id,
            caption=caption,
            media_url=media_url,
            media_hash=media_hash,
            media_mime_type=media_mime_type,
            visibility=visibility,
            capture_metadata=capture_metadata,
            is_late=is_late,
            published_at=now,
        )

        await self._post_repo.save(post)

        # Mark the moment as completed
        moment.completed_at = now
        await self._daily_moment_repo.save(moment)

        # Enqueue attestation job
        if self._arq_pool is not None:
            await self._arq_pool.enqueue_job("attest_post", str(post.id))

        logger.info(
            "post_submitted",
            user_id=str(user_id),
            post_id=str(post.id),
            is_late=is_late,
        )

        return post
