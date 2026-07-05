"""Tests for consent management — M3.

Tests:
- Record a consent grant
- Get consent history
- Withdraw consent
- Verify text_version is a SHA-256 of the consent text
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

import pytest

from verida.application.use_cases.consent import (
    GetConsentHistoryUseCase,
    RecordConsentUseCase,
    WithdrawConsentUseCase,
)
from verida.domain.entities import ConsentRecord, ConsentType


# ── Fake repository ────────────────────────────────────────────────────────────


class FakeConsentRepository:
    def __init__(self) -> None:
        self._records: dict[uuid.UUID, ConsentRecord] = {}

    async def save(self, record: ConsentRecord) -> None:
        self._records[record.id] = record

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        consent_type: ConsentType | None = None,
    ) -> list[ConsentRecord]:
        results = [r for r in self._records.values() if r.user_id == user_id]
        if consent_type is not None:
            results = [r for r in results if r.consent_type == consent_type]
        return sorted(results, key=lambda r: r.created_at)

    async def delete_for_user(self, user_id: uuid.UUID) -> None:
        to_delete = [rid for rid, r in self._records.items() if r.user_id == user_id]
        for rid in to_delete:
            del self._records[rid]


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_consent_creates_record() -> None:
    repo = FakeConsentRepository()
    uc = RecordConsentUseCase(repo)
    user_id = uuid.uuid4()
    consent_text = "I agree to the VERIDA Terms of Service version 1.0."

    record = await uc.execute(
        user_id=user_id,
        consent_type=ConsentType.TERMS_OF_SERVICE,
        version="1.0",
        consent_text=consent_text,
        client_ip="192.168.1.42",
    )

    assert record.user_id == user_id
    assert record.consent_type == ConsentType.TERMS_OF_SERVICE
    assert record.version == "1.0"
    assert record.withdrawn_at is None
    # text_version is SHA-256 of the consent text
    expected_hash = hashlib.sha256(consent_text.encode()).hexdigest()
    assert record.text_version == expected_hash


@pytest.mark.asyncio
async def test_record_consent_hashes_ip() -> None:
    repo = FakeConsentRepository()
    uc = RecordConsentUseCase(repo)
    user_id = uuid.uuid4()

    record = await uc.execute(
        user_id=user_id,
        consent_type=ConsentType.PRIVACY_POLICY,
        version="1.0",
        consent_text="Privacy policy consent text.",
        client_ip="203.0.113.45",
    )

    # Should NOT store the raw IP
    assert "203.0.113.45" not in record.ip_hash
    # Should be a hash string
    assert len(record.ip_hash) > 0


@pytest.mark.asyncio
async def test_get_consent_history_returns_all() -> None:
    repo = FakeConsentRepository()
    user_id = uuid.uuid4()

    # Record two consents
    for ctype in [ConsentType.TERMS_OF_SERVICE, ConsentType.PRIVACY_POLICY]:
        record = ConsentRecord(
            user_id=user_id,
            consent_type=ctype,
            version="1.0",
            text_version="abc",
            ip_hash="hashed",
        )
        await repo.save(record)

    uc = GetConsentHistoryUseCase(repo)
    history = await uc.execute(user_id)
    assert len(history) == 2


@pytest.mark.asyncio
async def test_get_consent_history_filtered_by_type() -> None:
    repo = FakeConsentRepository()
    user_id = uuid.uuid4()

    for ctype in [ConsentType.TERMS_OF_SERVICE, ConsentType.PRIVACY_POLICY]:
        await repo.save(
            ConsentRecord(
                user_id=user_id,
                consent_type=ctype,
                version="1.0",
                text_version="x",
                ip_hash="y",
            )
        )

    uc = GetConsentHistoryUseCase(repo)
    history = await uc.execute(user_id, consent_type=ConsentType.TERMS_OF_SERVICE)
    assert len(history) == 1
    assert history[0].consent_type == ConsentType.TERMS_OF_SERVICE


@pytest.mark.asyncio
async def test_withdraw_consent_sets_withdrawn_at() -> None:
    repo = FakeConsentRepository()
    user_id = uuid.uuid4()

    # Grant consent
    record = ConsentRecord(
        user_id=user_id,
        consent_type=ConsentType.MARKETING,
        version="1.0",
        text_version="hash",
        ip_hash="h",
    )
    await repo.save(record)

    # Withdraw
    uc = WithdrawConsentUseCase(repo)
    withdrawn = await uc.execute(user_id, ConsentType.MARKETING)

    assert len(withdrawn) == 1
    assert withdrawn[0].withdrawn_at is not None


@pytest.mark.asyncio
async def test_withdraw_consent_idempotent_no_active() -> None:
    repo = FakeConsentRepository()
    user_id = uuid.uuid4()

    uc = WithdrawConsentUseCase(repo)
    # No consent to withdraw — should return empty list, not error
    result = await uc.execute(user_id, ConsentType.MARKETING)
    assert result == []


@pytest.mark.asyncio
async def test_consent_records_are_append_only() -> None:
    """Withdrawing consent should not delete the original record."""
    repo = FakeConsentRepository()
    user_id = uuid.uuid4()

    grant_uc = RecordConsentUseCase(repo)
    await grant_uc.execute(
        user_id=user_id,
        consent_type=ConsentType.DATA_PROCESSING,
        version="1.0",
        consent_text="Data processing consent.",
        client_ip="10.0.0.1",
    )

    withdraw_uc = WithdrawConsentUseCase(repo)
    await withdraw_uc.execute(user_id, ConsentType.DATA_PROCESSING)

    history_uc = GetConsentHistoryUseCase(repo)
    history = await history_uc.execute(user_id)

    # Record still exists — append-only audit trail
    assert len(history) == 1
    assert history[0].withdrawn_at is not None
    assert history[0].granted_at is not None  # original grant preserved
