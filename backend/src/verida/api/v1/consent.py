"""Consent management API — M3.

Endpoints:
    GET  /api/v1/consent          — list current user's consent history
    POST /api/v1/consent          — record a new consent grant
    POST /api/v1/consent/withdraw — withdraw a specific consent type

Privacy:
- All operations require authentication
- IP is truncated to /24 before hashing — never logged full
- Generic error messages (no user enumeration)
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator

from verida.api.v1.deps import AsyncSessionDep, CurrentUser
from verida.application.use_cases.consent import (
    GetConsentHistoryUseCase,
    RecordConsentUseCase,
    WithdrawConsentUseCase,
)
from verida.domain.entities import ConsentType

router = APIRouter()


# ── Request / Response schemas ─────────────────────────────────────────────────


class ConsentGrantRequest(BaseModel):
    consent_type: ConsentType
    version: str
    consent_text: str  # Exact text shown to user (hashed for storage)

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if not v or len(v) > 20:
            raise ValueError("Version must be 1-20 characters")
        return v

    @field_validator("consent_text")
    @classmethod
    def validate_consent_text(cls, v: str) -> str:
        if len(v) < 10:
            raise ValueError("consent_text too short to be valid")
        return v


class ConsentWithdrawRequest(BaseModel):
    consent_type: ConsentType


class ConsentRecordResponse(BaseModel):
    id: str
    consent_type: str
    version: str
    text_version: str
    granted_at: datetime
    withdrawn_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get("", response_model=list[ConsentRecordResponse], summary="List consent history")
async def list_consent(
    current_user: CurrentUser,
    session: AsyncSessionDep,
    consent_type: Optional[ConsentType] = None,
) -> list[ConsentRecordResponse]:
    """Return the authenticated user's consent history (all types or filtered)."""
    from verida.infrastructure.db.repositories import SqlConsentRepository

    repo = SqlConsentRepository(session)
    use_case = GetConsentHistoryUseCase(repo)
    records = await use_case.execute(current_user.id, consent_type=consent_type)

    return [
        ConsentRecordResponse(
            id=str(r.id),
            consent_type=r.consent_type.value,
            version=r.version,
            text_version=r.text_version,
            granted_at=r.granted_at,
            withdrawn_at=r.withdrawn_at,
        )
        for r in records
    ]


@router.post("", response_model=ConsentRecordResponse, status_code=status.HTTP_201_CREATED,
             summary="Record consent grant")
async def record_consent(
    body: ConsentGrantRequest,
    request: Request,
    current_user: CurrentUser,
    session: AsyncSessionDep,
) -> ConsentRecordResponse:
    """Record a new consent grant for the authenticated user."""
    from verida.infrastructure.db.repositories import SqlConsentRepository

    repo = SqlConsentRepository(session)
    use_case = RecordConsentUseCase(repo)

    # Extract client IP for /24 hashing (done inside the use case)
    client_ip = request.headers.get("X-Forwarded-For", "")
    if not client_ip and request.client:
        client_ip = request.client.host

    record = await use_case.execute(
        user_id=current_user.id,
        consent_type=body.consent_type,
        version=body.version,
        consent_text=body.consent_text,
        client_ip=client_ip or "unknown",
    )

    return ConsentRecordResponse(
        id=str(record.id),
        consent_type=record.consent_type.value,
        version=record.version,
        text_version=record.text_version,
        granted_at=record.granted_at,
        withdrawn_at=record.withdrawn_at,
    )


@router.post("/withdraw", summary="Withdraw consent")
async def withdraw_consent(
    body: ConsentWithdrawRequest,
    current_user: CurrentUser,
    session: AsyncSessionDep,
) -> dict:
    """Withdraw a specific consent type. Withdrawal is as easy as giving consent (GDPR Art. 7(3))."""
    from verida.infrastructure.db.repositories import SqlConsentRepository

    repo = SqlConsentRepository(session)
    use_case = WithdrawConsentUseCase(repo)

    withdrawn = await use_case.execute(
        user_id=current_user.id,
        consent_type=body.consent_type,
    )

    return {
        "withdrawn": len(withdrawn),
        "consent_type": body.consent_type.value,
        "message": "Consent withdrawn. You can re-grant it at any time.",
    }
