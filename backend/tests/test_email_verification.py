"""Tests for the email verification flow.

Tests
-----
- SendVerificationEmail: generates token, stores hash, sends email.
- SendVerificationEmail: no-op if user is already verified.
- SendVerificationEmail: deletes old tokens before generating new one.
- VerifyEmail: marks user verified, marks token used.
- VerifyEmail: rejects invalid token.
- VerifyEmail: rejects already-used token.
- VerifyEmail: rejects expired token.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from verida.application.use_cases.email import (
    SendVerificationEmailUseCase,
    VerifyEmailUseCase,
)
from verida.domain.entities import EmailVerification, User
from verida.infrastructure.email import StubEmailAdapter


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user(is_verified: bool = False) -> User:
    return User(
        handle="testuser",
        email="testuser@example.com",
        display_name="Test User",
        is_verified=is_verified,
    )


# ── SendVerificationEmail ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestSendVerificationEmail:
    async def test_sends_email_to_unverified_user(self) -> None:
        user = _make_user(is_verified=False)

        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = user

        verification_repo = AsyncMock()
        verification_repo.delete_for_user.return_value = None
        verification_repo.save.return_value = None

        email_adapter = StubEmailAdapter()

        use_case = SendVerificationEmailUseCase(
            user_repo=user_repo,
            verification_repo=verification_repo,
            email_port=email_adapter,
        )

        await use_case.execute(user.id)

        assert len(email_adapter.sent_messages) == 1
        msg = email_adapter.sent_messages[0]
        assert msg["to"] == user.email
        assert "Verify" in msg["subject"]
        assert "verify-email" in msg["text"]

        # Verify the token hash was saved
        assert verification_repo.save.called
        saved: EmailVerification = verification_repo.save.call_args[0][0]
        assert saved.user_id == user.id
        assert len(saved.token_hash) == 64  # SHA-256 hex

    async def test_no_op_if_already_verified(self) -> None:
        user = _make_user(is_verified=True)

        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = user

        verification_repo = AsyncMock()
        email_adapter = StubEmailAdapter()

        use_case = SendVerificationEmailUseCase(
            user_repo=user_repo,
            verification_repo=verification_repo,
            email_port=email_adapter,
        )

        await use_case.execute(user.id)

        # No email should be sent
        assert len(email_adapter.sent_messages) == 0
        assert not verification_repo.save.called

    async def test_deletes_old_tokens_before_sending(self) -> None:
        user = _make_user(is_verified=False)

        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = user

        verification_repo = AsyncMock()
        verification_repo.delete_for_user.return_value = None
        verification_repo.save.return_value = None

        email_adapter = StubEmailAdapter()

        use_case = SendVerificationEmailUseCase(
            user_repo=user_repo,
            verification_repo=verification_repo,
            email_port=email_adapter,
        )

        await use_case.execute(user.id)

        verification_repo.delete_for_user.assert_called_once_with(user.id)


# ── VerifyEmail ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestVerifyEmail:
    def _make_verification(
        self,
        user_id: uuid.UUID,
        raw_token: str,
        *,
        expired: bool = False,
        used: bool = False,
    ) -> EmailVerification:
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = (
            datetime.now(UTC) - timedelta(hours=1)
            if expired
            else datetime.now(UTC) + timedelta(hours=24)
        )
        used_at = datetime.now(UTC) if used else None
        return EmailVerification(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            used_at=used_at,
        )

    async def test_valid_token_marks_user_verified(self) -> None:
        user = _make_user(is_verified=False)
        raw_token = "validtoken1234567890abcdef"
        verification = self._make_verification(user.id, raw_token)

        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = user
        user_repo.save.return_value = None

        verification_repo = AsyncMock()
        verification_repo.get_by_token_hash.return_value = verification
        verification_repo.save.return_value = None

        use_case = VerifyEmailUseCase(user_repo=user_repo, verification_repo=verification_repo)
        await use_case.execute(raw_token)

        # User should be saved with is_verified=True
        assert user_repo.save.called
        saved_user: User = user_repo.save.call_args[0][0]
        assert saved_user.is_verified is True

        # Verification token should be marked as used
        assert verification_repo.save.called
        saved_ver: EmailVerification = verification_repo.save.call_args[0][0]
        assert saved_ver.used_at is not None

    async def test_invalid_token_raises(self) -> None:
        verification_repo = AsyncMock()
        verification_repo.get_by_token_hash.return_value = None

        use_case = VerifyEmailUseCase(
            user_repo=AsyncMock(), verification_repo=verification_repo
        )

        with pytest.raises(ValueError, match="Invalid verification token"):
            await use_case.execute("invalid-token-here")

    async def test_already_used_token_raises(self) -> None:
        user = _make_user()
        raw_token = "usedtoken1234567890abcdef"
        verification = self._make_verification(user.id, raw_token, used=True)

        verification_repo = AsyncMock()
        verification_repo.get_by_token_hash.return_value = verification

        use_case = VerifyEmailUseCase(
            user_repo=AsyncMock(), verification_repo=verification_repo
        )

        with pytest.raises(ValueError, match="already been used"):
            await use_case.execute(raw_token)

    async def test_expired_token_raises(self) -> None:
        user = _make_user()
        raw_token = "expiredtoken1234567890abc"
        verification = self._make_verification(user.id, raw_token, expired=True)

        verification_repo = AsyncMock()
        verification_repo.get_by_token_hash.return_value = verification

        use_case = VerifyEmailUseCase(
            user_repo=AsyncMock(), verification_repo=verification_repo
        )

        with pytest.raises(ValueError, match="expired"):
            await use_case.execute(raw_token)
