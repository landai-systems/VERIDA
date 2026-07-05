"""Tests for the capture flow (initiate + submit).

Tests
-----
- Initiate: creates a DailyMoment, returns a capture_token.
- Initiate: rejects if the user already posted today.
- Submit: validates the capture token (invalid token rejected).
- Submit: rejects gallery uploads.
- Submit: enforces 10 MB size limit.
- Submit: marks post as late when submitted outside the 10-minute window.
- Submit: attestation job enqueued.
- HMAC token: verify/reject cycle.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from verida.application.use_cases.daily_moment import (
    CAPTURE_WINDOW_SECONDS,
    MAX_MEDIA_BYTES,
    InitiateCaptureUseCase,
    SubmitPostUseCase,
    _make_capture_token,
    _verify_capture_token,
)
from verida.domain.entities import DailyMoment, Post, PostVisibility


# ── Helpers ───────────────────────────────────────────────────────────────────

SECRET = "test-secret-key-must-be-32-chars-long!"
SMALL_IMAGE = b"\xff\xd8\xff" + b"\x00" * 100  # minimal fake JPEG


# ── Token tests ───────────────────────────────────────────────────────────────


class TestCaptureToken:
    def test_valid_token_verifies(self) -> None:
        user_id = uuid.uuid4()
        moment_id = uuid.uuid4()
        ts = int(time.time())
        token = _make_capture_token(moment_id, user_id, ts, SECRET)
        returned_moment_id, is_within = _verify_capture_token(token, user_id, SECRET)
        assert returned_moment_id == moment_id
        assert is_within is True

    def test_expired_token_is_not_within_window(self) -> None:
        user_id = uuid.uuid4()
        moment_id = uuid.uuid4()
        old_ts = int(time.time()) - CAPTURE_WINDOW_SECONDS - 1
        token = _make_capture_token(moment_id, user_id, old_ts, SECRET)
        _, is_within = _verify_capture_token(token, user_id, SECRET)
        assert is_within is False

    def test_tampered_token_rejected(self) -> None:
        user_id = uuid.uuid4()
        moment_id = uuid.uuid4()
        ts = int(time.time())
        token = _make_capture_token(moment_id, user_id, ts, SECRET)
        tampered = token[:-5] + "AAAAA"
        returned_id, _ = _verify_capture_token(tampered, user_id, SECRET)
        assert returned_id.int == 0

    def test_wrong_user_rejected(self) -> None:
        user_id = uuid.uuid4()
        other_user = uuid.uuid4()
        moment_id = uuid.uuid4()
        ts = int(time.time())
        token = _make_capture_token(moment_id, user_id, ts, SECRET)
        returned_id, _ = _verify_capture_token(token, other_user, SECRET)
        assert returned_id.int == 0


# ── InitiateCapture tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestInitiateCapture:
    async def test_creates_daily_moment(self) -> None:
        user_id = uuid.uuid4()

        moment_repo = AsyncMock()
        moment_repo.save.return_value = None

        post_repo = AsyncMock()
        post_repo.get_today_post_for_user.return_value = None  # no post today

        use_case = InitiateCaptureUseCase(
            daily_moment_repo=moment_repo,
            post_repo=post_repo,
            secret_key=SECRET,
        )

        result = await use_case.execute(user_id=user_id)

        assert "capture_token" in result
        assert "moment_id" in result
        assert moment_repo.save.called

    async def test_raises_if_already_posted_today(self) -> None:
        user_id = uuid.uuid4()

        existing_post = Post(
            author_id=user_id,
            daily_moment_id=uuid.uuid4(),
            caption="Already posted",
            media_url="/media/x",
            media_hash="a" * 64,
            media_mime_type="image/jpeg",
        )

        moment_repo = AsyncMock()
        post_repo = AsyncMock()
        post_repo.get_today_post_for_user.return_value = existing_post

        use_case = InitiateCaptureUseCase(
            daily_moment_repo=moment_repo,
            post_repo=post_repo,
            secret_key=SECRET,
        )

        with pytest.raises(ValueError, match="already posted"):
            await use_case.execute(user_id=user_id)


# ── SubmitPost tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestSubmitPost:
    def _make_valid_moment(self, user_id: uuid.UUID) -> DailyMoment:
        moment_id = uuid.uuid4()
        token = _make_capture_token(moment_id, user_id, int(time.time()), SECRET)
        return DailyMoment(
            id=moment_id,
            user_id=user_id,
            capture_token=token,
            initiated_at=datetime.now(UTC),
        )

    async def test_valid_submission_creates_post(self) -> None:
        user_id = uuid.uuid4()
        moment = self._make_valid_moment(user_id)

        moment_repo = AsyncMock()
        moment_repo.get_by_id.return_value = moment
        moment_repo.save.return_value = None

        post_repo = AsyncMock()
        post_repo.save.return_value = None

        use_case = SubmitPostUseCase(
            daily_moment_repo=moment_repo,
            post_repo=post_repo,
            secret_key=SECRET,
        )

        post = await use_case.execute(
            user_id=user_id,
            capture_token=moment.capture_token,
            caption="Hello world",
            media_bytes=SMALL_IMAGE,
            media_mime_type="image/jpeg",
            capture_metadata={
                "source": "camera",
                "duration_seconds": 3.0,
                "width_px": 1280,
                "height_px": 720,
            },
        )

        assert isinstance(post, Post)
        assert post.author_id == user_id
        assert post.is_late is False
        assert post_repo.save.called

    async def test_gallery_upload_rejected(self) -> None:
        user_id = uuid.uuid4()
        moment = self._make_valid_moment(user_id)

        moment_repo = AsyncMock()
        post_repo = AsyncMock()

        use_case = SubmitPostUseCase(
            daily_moment_repo=moment_repo,
            post_repo=post_repo,
            secret_key=SECRET,
        )

        with pytest.raises(ValueError, match="Gallery uploads are not allowed"):
            await use_case.execute(
                user_id=user_id,
                capture_token=moment.capture_token,
                caption="From gallery",
                media_bytes=SMALL_IMAGE,
                media_mime_type="image/jpeg",
                capture_metadata={"source": "gallery"},
            )

    async def test_oversized_media_rejected(self) -> None:
        user_id = uuid.uuid4()
        moment = self._make_valid_moment(user_id)

        moment_repo = AsyncMock()
        post_repo = AsyncMock()

        use_case = SubmitPostUseCase(
            daily_moment_repo=moment_repo,
            post_repo=post_repo,
            secret_key=SECRET,
        )

        oversized = b"\x00" * (MAX_MEDIA_BYTES + 1)

        with pytest.raises(PermissionError, match="10 MB"):
            await use_case.execute(
                user_id=user_id,
                capture_token=moment.capture_token,
                caption="Too big",
                media_bytes=oversized,
                media_mime_type="image/jpeg",
                capture_metadata={"source": "camera"},
            )

    async def test_invalid_token_rejected(self) -> None:
        user_id = uuid.uuid4()

        moment_repo = AsyncMock()
        post_repo = AsyncMock()

        use_case = SubmitPostUseCase(
            daily_moment_repo=moment_repo,
            post_repo=post_repo,
            secret_key=SECRET,
        )

        with pytest.raises(ValueError, match="Invalid capture token"):
            await use_case.execute(
                user_id=user_id,
                capture_token="not-a-real-token",
                caption="Bad token",
                media_bytes=SMALL_IMAGE,
                media_mime_type="image/jpeg",
                capture_metadata={"source": "camera"},
            )

    async def test_post_marked_late_when_outside_window(self) -> None:
        user_id = uuid.uuid4()
        moment_id = uuid.uuid4()
        # Use an old timestamp (outside the 10-minute window)
        old_ts = int(time.time()) - CAPTURE_WINDOW_SECONDS - 60
        old_token = _make_capture_token(moment_id, user_id, old_ts, SECRET)

        moment = DailyMoment(
            id=moment_id,
            user_id=user_id,
            capture_token=old_token,
            initiated_at=datetime.now(UTC) - timedelta(minutes=15),
        )

        moment_repo = AsyncMock()
        moment_repo.get_by_id.return_value = moment
        moment_repo.save.return_value = None

        post_repo = AsyncMock()
        post_repo.save.return_value = None

        use_case = SubmitPostUseCase(
            daily_moment_repo=moment_repo,
            post_repo=post_repo,
            secret_key=SECRET,
        )

        post = await use_case.execute(
            user_id=user_id,
            capture_token=old_token,
            caption="Late post",
            media_bytes=SMALL_IMAGE,
            media_mime_type="image/jpeg",
            capture_metadata={"source": "camera"},
        )

        assert post.is_late is True

    async def test_attestation_enqueued_when_arq_pool_available(self) -> None:
        user_id = uuid.uuid4()
        moment = self._make_valid_moment(user_id)

        moment_repo = AsyncMock()
        moment_repo.get_by_id.return_value = moment
        moment_repo.save.return_value = None

        post_repo = AsyncMock()
        post_repo.save.return_value = None

        arq_pool = AsyncMock()
        arq_pool.enqueue_job = AsyncMock()

        use_case = SubmitPostUseCase(
            daily_moment_repo=moment_repo,
            post_repo=post_repo,
            secret_key=SECRET,
            arq_pool=arq_pool,
        )

        post = await use_case.execute(
            user_id=user_id,
            capture_token=moment.capture_token,
            caption="Attest me",
            media_bytes=SMALL_IMAGE,
            media_mime_type="image/jpeg",
            capture_metadata={"source": "camera"},
        )

        arq_pool.enqueue_job.assert_called_once_with("attest_post", str(post.id))
