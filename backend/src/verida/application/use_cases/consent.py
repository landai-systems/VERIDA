"""Consent management use cases — M3.

Implements GDPR Article 7 requirements:
- Freely given, specific, informed, unambiguous consent
- Right to withdraw consent at any time (as easy as giving it)
- Consent records are append-only (immutable audit trail)
- All records include text_version (hash of exact text shown to user)
- IP stored as /24-truncated hash — never the full address

Use cases:
- RecordConsentUseCase: record a new consent grant
- GetConsentHistoryUseCase: retrieve all consent records for a user
- WithdrawConsentUseCase: record consent withdrawal
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Optional

import structlog

from verida.domain.entities import ConsentRecord, ConsentType

logger = structlog.get_logger(__name__)


def _hash_ip_prefix(ip: str) -> str:
    """Truncate IP to /24 prefix and hash it.

    We store a /24-prefix hash rather than the full IP to prevent
    per-user tracking while allowing abuse detection at network level.

    Returns a SHA-256 hex string of the truncated IP.
    """
    if not ip or ip == "unknown":
        return "unknown"
    try:
        if ":" in ip:
            # IPv6: keep /48 prefix
            parts = ip.split(":")
            prefix = ":".join(parts[:3]) + "::"
        else:
            # IPv4: keep /24 prefix
            parts = ip.split(".")
            prefix = ".".join(parts[:3]) + ".0"
        return hashlib.sha256(prefix.encode()).hexdigest()[:32]
    except Exception:
        return "unknown"


class ConsentRepository:
    """Protocol-compatible type hint for the consent repository."""
    pass  # Implemented in SqlConsentRepository


class RecordConsentUseCase:
    """Record a new consent grant.

    Creates an append-only consent record. Multiple consents of the same
    type can coexist — the most recent active one applies.

    Parameters
    ----------
    consent_repo:
        Repository for persisting consent records.
    """

    def __init__(self, consent_repo: object) -> None:
        self._repo = consent_repo

    async def execute(
        self,
        user_id: uuid.UUID,
        consent_type: ConsentType,
        version: str,
        consent_text: str,  # The exact text shown to the user
        client_ip: str = "unknown",
    ) -> ConsentRecord:
        """Record a consent grant.

        Parameters
        ----------
        user_id:
            The user granting consent.
        consent_type:
            Which type of consent is being granted.
        version:
            Semantic version of the consent document (e.g. "1.0").
        consent_text:
            The exact consent text shown to the user. We store its SHA-256
            hash as proof of what the user actually agreed to.
        client_ip:
            Client IP address. Will be truncated to /24 and hashed.

        Returns
        -------
        ConsentRecord:
            The persisted consent record.
        """
        text_version = hashlib.sha256(consent_text.encode()).hexdigest()
        ip_hash = _hash_ip_prefix(client_ip)

        record = ConsentRecord(
            user_id=user_id,
            consent_type=consent_type,
            version=version,
            text_version=text_version,
            ip_hash=ip_hash,
            granted_at=datetime.now(UTC),
        )

        await self._repo.save(record)

        logger.info(
            "consent_recorded",
            user_id=str(user_id),
            consent_type=consent_type.value,
            version=version,
        )

        return record


class GetConsentHistoryUseCase:
    """Retrieve the full consent history for a user.

    Returns all consent records (grants and withdrawals) in chronological order.
    Required for GDPR Article 7 accountability.
    """

    def __init__(self, consent_repo: object) -> None:
        self._repo = consent_repo

    async def execute(
        self,
        user_id: uuid.UUID,
        consent_type: Optional[ConsentType] = None,
    ) -> list[ConsentRecord]:
        """Get consent history.

        Parameters
        ----------
        user_id:
            The user whose history to retrieve.
        consent_type:
            If provided, filter to a specific consent type.

        Returns
        -------
        list[ConsentRecord]:
            All consent records, oldest first.
        """
        return await self._repo.list_for_user(user_id, consent_type=consent_type)


class WithdrawConsentUseCase:
    """Record consent withdrawal.

    Withdrawal is recorded as an update to the existing record's ``withdrawn_at``
    field rather than deletion — we need the audit trail.
    Withdrawal must be as easy as giving consent (GDPR Art. 7(3)).
    """

    def __init__(self, consent_repo: object) -> None:
        self._repo = consent_repo

    async def execute(
        self,
        user_id: uuid.UUID,
        consent_type: ConsentType,
    ) -> list[ConsentRecord]:
        """Withdraw consent for a specific type.

        Sets ``withdrawn_at`` on all active (non-withdrawn) records of the
        given type for this user.

        Parameters
        ----------
        user_id:
            The user withdrawing consent.
        consent_type:
            Which type of consent to withdraw.

        Returns
        -------
        list[ConsentRecord]:
            The updated (withdrawn) consent records.
        """
        records = await self._repo.list_for_user(user_id, consent_type=consent_type)
        active = [r for r in records if r.withdrawn_at is None]

        if not active:
            logger.info(
                "consent_withdrawal_no_active",
                user_id=str(user_id),
                consent_type=consent_type.value,
            )
            return []

        now = datetime.now(UTC)
        for record in active:
            record.withdrawn_at = now
            await self._repo.save(record)

        logger.info(
            "consent_withdrawn",
            user_id=str(user_id),
            consent_type=consent_type.value,
            records_withdrawn=len(active),
        )

        return active
