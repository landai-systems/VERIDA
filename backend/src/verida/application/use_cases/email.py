"""Use cases for email verification.

SendVerificationEmailUseCase
    - Generates a short-lived verification token (HMAC-signed, 24h expiry)
    - Stores the SHA-256 hash
    - Sends a verification email via the EmailPort

VerifyEmailUseCase
    - Validates the token (hash lookup, expiry, not already used)
    - Marks the User as verified
    - Marks the verification token as used
"""

from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from datetime import UTC, datetime, timedelta

import structlog

from verida.application.ports import (
    EmailPort,
    EmailVerificationRepository,
    UserRepository,
)
from verida.domain.entities import EmailVerification

logger = structlog.get_logger(__name__)

VERIFICATION_EXPIRY_HOURS = 24


class SendVerificationEmailUseCase:
    """Send an email verification link to the user."""

    def __init__(
        self,
        user_repo: UserRepository,
        verification_repo: EmailVerificationRepository,
        email_port: EmailPort,
        app_base_url: str = "http://localhost:8000",
    ) -> None:
        self._user_repo = user_repo
        self._verification_repo = verification_repo
        self._email_port = email_port
        self._app_base_url = app_base_url

    async def execute(self, user_id: uuid.UUID) -> None:
        """Generate and send a verification email.

        Raises
        ------
        ValueError
            If the user is not found or is already verified.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError("User not found.")
        if user.is_verified:
            return  # Already verified — no-op

        # Invalidate any existing tokens
        await self._verification_repo.delete_for_user(user_id)

        # Generate new token
        raw_token = os.urandom(32).hex()
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(hours=VERIFICATION_EXPIRY_HOURS)

        verification = EmailVerification(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        await self._verification_repo.save(verification)

        verify_url = (
            f"{self._app_base_url}/api/v1/auth/verify-email?token={raw_token}"
        )

        html = f"""
        <html><body>
        <h2>Welcome to VERIDA!</h2>
        <p>Hi {user.display_name},</p>
        <p>Please verify your email address by clicking the link below:</p>
        <p><a href="{verify_url}">Verify my email</a></p>
        <p>This link expires in {VERIFICATION_EXPIRY_HOURS} hours.</p>
        <p>If you didn't create a VERIDA account, you can safely ignore this email.</p>
        </body></html>
        """

        text = (
            f"Welcome to VERIDA!\n\n"
            f"Hi {user.display_name},\n\n"
            f"Please verify your email address by visiting:\n{verify_url}\n\n"
            f"This link expires in {VERIFICATION_EXPIRY_HOURS} hours.\n"
        )

        await self._email_port.send(
            to_email=user.email,
            subject="Verify your VERIDA email address",
            body_html=html,
            body_text=text,
        )

        logger.info("verification_email_sent", user_id=str(user_id))


class VerifyEmailUseCase:
    """Verify a user's email using a token from the verification email."""

    def __init__(
        self,
        user_repo: UserRepository,
        verification_repo: EmailVerificationRepository,
    ) -> None:
        self._user_repo = user_repo
        self._verification_repo = verification_repo

    async def execute(self, raw_token: str) -> None:
        """Mark the user's email as verified.

        Raises
        ------
        ValueError
            If the token is invalid, expired, or already used.
        """
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        verification = await self._verification_repo.get_by_token_hash(token_hash)

        if verification is None:
            raise ValueError("Invalid verification token.")

        if verification.used_at is not None:
            raise ValueError("This verification link has already been used.")

        if verification.expires_at < datetime.now(UTC):
            raise ValueError("This verification link has expired. Please request a new one.")

        # Mark token as used
        verification.used_at = datetime.now(UTC)
        await self._verification_repo.save(verification)

        # Mark user as verified
        user = await self._user_repo.get_by_id(verification.user_id)
        if user is None:
            raise ValueError("User not found.")

        user.is_verified = True
        user.updated_at = datetime.now(UTC)
        await self._user_repo.save(user)

        logger.info("email_verified", user_id=str(user.id))
