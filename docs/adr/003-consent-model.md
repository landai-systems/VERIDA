# ADR 003 — Versioned Consent Model

**Status:** Accepted  
**Date:** 2026-07-05  
**Deciders:** VERIDA engineering team  
**Context:** M3 Trust & Compliance

---

## Context

VERIDA must comply with GDPR Article 7 (conditions for consent) and Article 5(2) (accountability). This requires:

1. **Proof of consent**: We must be able to demonstrate that consent was freely given, specific, informed, and unambiguous at the time of collection.
2. **Versioning**: Consent text changes over time (ToS updates, policy revisions). We need to track exactly which version a user agreed to.
3. **Easy withdrawal**: Withdrawal must be as easy as giving consent (Art. 7(3)).
4. **Auditability**: We must maintain a tamper-evident record of all consent events.

---

## Decision

We implement a **versioned, append-only consent record model** with the following design:

### Consent record structure

```python
@dataclass
class ConsentRecord:
    id: uuid.UUID           # UUIDv7 — time-ordered
    user_id: uuid.UUID
    consent_type: ConsentType  # terms_of_service | privacy_policy | data_processing | marketing
    version: str            # "1.0", "1.1", etc. — semantic version of document
    text_version: str       # SHA-256 of exact consent text shown to user
    granted_at: datetime    # When consent was given
    withdrawn_at: datetime  # When withdrawn (None = still active)
    ip_hash: str            # SHA-256 of /24-truncated IP — NOT the full IP
    created_at: datetime
```

### Append-only semantics

- **Granting consent**: Creates a new `ConsentRecord` row. Old records are preserved.
- **Withdrawing consent**: Sets `withdrawn_at` on existing active records. Never deletes rows.
- This means the DB is an immutable audit log of every consent event.

### text_version

When a user is shown a consent form, the frontend sends the exact text of the consent document. The backend computes:

```python
text_version = hashlib.sha256(consent_text.encode()).hexdigest()
```

This hash is stored. Even if the stored document changes later, we retain proof of exactly what the user agreed to.

### IP privacy

Full IP addresses are never stored. The /24 prefix is extracted, then hashed:

```python
# IPv4 example: 203.0.113.45 → 203.0.113.0/24 → SHA-256 → stored
ip_hash = hashlib.sha256("203.0.113.0".encode()).hexdigest()[:32]
```

This allows network-level accountability (e.g. detecting consent from botnets) without per-user IP tracking.

---

## Alternatives considered

### Alternative 1: Boolean flag on User table

`User.consented_to_tos: bool = True`

**Rejected because:**
- No versioning — can't prove which version they agreed to
- No audit trail — overwritten on withdrawal
- Not Art. 5(2) compliant

### Alternative 2: Separate event log table (event sourcing)

A pure event log: `ConsentGranted`, `ConsentWithdrawn` events in a separate `consent_events` table.

**Rejected because:**
- More complexity for no additional GDPR benefit in MVP
- Current append-only model with `withdrawn_at` achieves the same audit trail
- Can be migrated to event sourcing later if needed

### Alternative 3: Cryptographically signed consent records

Sign each record with the user's private key.

**Rejected because:**
- VERIDA is not a key-management platform
- No user-controlled keys in MVP
- `text_version` hash provides sufficient proof without key management complexity

---

## Consequences

**Positive:**
- Full audit trail of all consent events — Art. 5(2) compliant
- `text_version` provides cryptographic proof of what user agreed to
- Easy withdrawal endpoint satisfies Art. 7(3)
- No full IP storage — stronger privacy than required minimum

**Negative:**
- Consent table grows over time (never shrinks via deletion)
- Requires version coordination between frontend and backend when consent text changes
- `text_version` validation requires sending full consent text over API — larger request payload

**Mitigations:**
- Table growth is bounded (one consent type × number of versions × number of users)
- Frontend and backend maintain a shared `CONSENT_TEXT_REGISTRY` mapping version → text
- Request size is acceptable (consent text is < 10 KB)
