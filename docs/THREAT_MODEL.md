# STRIDE Threat Model — VERIDA

**Framework:** STRIDE (Microsoft)  
**Scope:** VERIDA M1–M3 API + Auth system + Consent + GDPR endpoints  
**Last updated:** 2026-07-05 (M3)  
**Status:** Updated with M3 attack surfaces — rate limiting, consent, data export

---

## System components

```
[Browser]  ←HTTPS→  [Caddy/Traefik]  ←HTTP→  [FastAPI]  ←→  [PostgreSQL]
                                                      ↕
                                                   [Redis]
```

**Trust boundaries:**
1. Public internet → Reverse proxy (TLS)
2. Reverse proxy → API (internal network)
3. API → Database (internal network)
4. API → Redis (internal network)

---

## STRIDE analysis

### S — Spoofing

| Threat | Component | Likelihood | Impact | Mitigation | Status |
|--------|-----------|-----------|--------|-----------|--------|
| Attacker logs in as another user | Auth | Medium | High | Argon2id passwords; JWT verification | ✅ M1 |
| JWT token theft (XSS) | Access token | Medium | High | Short TTL (15 min); httpOnly cookies for refresh | ✅ M1 |
| Refresh token theft | Cookie | Low | High | httpOnly; SameSite=Strict; path-restricted | ✅ M1 |
| Account enumeration via login timing | Auth | Medium | Low | Constant-time hash check (dummy hash on unknown email) | ✅ M1 |
| Account enumeration via rate-limit error | Auth | Medium | Low | Generic "Too many requests" error — no email leak | ✅ M3 |
| Fake capture (pre-recorded video) | Capture flow | High | Medium | M3 upgraded heuristics (9 checks); see TRUST_MODEL.md | ⚠️ Partial |
| Replay attack (same media re-uploaded) | Attestation | Medium | Medium | Redis perceptual-hash dedup (7-day TTL) | ✅ M3 |

### T — Tampering

| Threat | Component | Likelihood | Impact | Mitigation | Status |
|--------|-----------|-----------|--------|-----------|--------|
| Media modified after upload | Post | Medium | High | SHA-256 hash recorded at submission | ✅ M1 |
| Database record modification | DB | Low | Critical | DB user has no DDL; audit log planned | 🔶 M4 |
| JWT payload tampering | Auth | Low | Critical | HS256 signature verification | ✅ M1 |
| Capture metadata injection | Attestation | High | Medium | 9 heuristic checks; metadata completeness scoring | ✅ M3 |
| Consent record tampering | Consent | Low | High | Append-only model; no UPDATE on grant (only withdrawn_at) | ✅ M3 |

### R — Repudiation

| Threat | Component | Likelihood | Impact | Mitigation | Status |
|--------|-----------|-----------|--------|-----------|--------|
| User denies posting content | Post | Medium | Medium | Attestation record + timestamp immutable | ✅ M1 |
| User denies consenting | Consent | Medium | High | Append-only consent records with text_version (SHA-256 of shown text) | ✅ M3 |
| Admin denies making change | Admin | Low | Medium | Audit log for admin actions | 🔶 M4 |

### I — Information Disclosure

| Threat | Component | Likelihood | Impact | Mitigation | Status |
|--------|-----------|-----------|--------|-----------|--------|
| Password leak via API | Auth | Low | Critical | Argon2id hash only; hash never returned | ✅ M1 |
| Refresh token in logs | Auth | Low | High | Only token hash logged; raw token never logged | ✅ M1 |
| User email in error messages | API | Medium | Medium | Generic error messages; no field name leak | ✅ M1 |
| Private post visible to non-member | Posts | Medium | High | Circle membership checks | ✅ M2 |
| Full IP address stored in consent records | Consent | Medium | Medium | /24 prefix only, then SHA-256 hashed — never full IP | ✅ M3 |
| GDPR export exposes sensitive data | GDPR | Low | High | argon2_hash excluded from export; only user's own data | ✅ M3 |
| GDPR bulk export as DoS vector | GDPR | Medium | Medium | Auth required; rate limiting on export endpoint | ✅ M3 |
| CSP bypass via inline script | Frontend | Medium | High | CSP: no unsafe-inline, no unsafe-eval | ✅ M3 |
| Clickjacking via iframe | Frontend | Low | Medium | X-Frame-Options: DENY + CSP frame-ancestors: none | ✅ M3 |
| MIME sniffing attack | Frontend | Low | Medium | X-Content-Type-Options: nosniff | ✅ M3 |
| Log files contain PII (IP, email) | Infra | Medium | Medium | Log retention 7 days; IPs truncated to /24 | ⚠️ Partial |

### D — Denial of Service

| Threat | Component | Likelihood | Impact | Mitigation | Status |
|--------|-----------|-----------|--------|-----------|--------|
| Brute-force login | Auth | High | Medium | Redis sliding-window rate limiter (10 req/60s per /24) | ✅ M3 |
| Credential stuffing | Auth | Medium | High | Rate limiting + Argon2id slows enumeration | ✅ M3 |
| Large media upload flood | Upload | Medium | High | File size limits; rate limiting on capture endpoint | ✅ M3 |
| Attestation compute flood | Attestation | Low | Medium | arq queue; worker autoscaling | ✅ M2 |
| Redis rate-limiter DoS (Redis down) | Rate limiter | Low | Low | Fail-open: allows request, logs warning | ✅ M3 |
| Dependency confusion / supply chain | Build | Low | Critical | pip-audit + gitleaks in CI | ✅ M1 |

### E — Elevation of Privilege

| Threat | Component | Likelihood | Impact | Mitigation | Status |
|--------|-----------|-----------|--------|-----------|--------|
| Regular user accesses admin endpoint | Admin | Medium | Critical | Role-based access control | 🔶 M4 |
| SQL injection via ORM | DB | Low | Critical | SQLAlchemy parameterised queries | ✅ M2 |
| SSRF via media URL | Infrastructure | Low | High | Validate media URLs; no outbound fetches | 🔶 M2 |
| Accidental prod deployment | Infra | Medium | Critical | DO_NOT_DEPLOY guard | ✅ M1 |
| Consent withdrawal for other user | Consent | Low | High | Auth required; withdrawal only affects current user | ✅ M3 |
| GDPR deletion of other user | GDPR | Low | Critical | Auth required; deletion only affects current user | ✅ M3 |

---

## M3 new attack surfaces

### Rate limiting (Redis-backed)

**Threat:** Attacker bypasses rate limiting by rotating IPs.  
**Mitigation:** Rate limit key is per-/24 subnet (not per-IP). Rotating within the same /24 doesn't help. Rotating across /24s requires many more IPs.

**Threat:** Attacker uses rate-limit error to enumerate valid emails.  
**Mitigation:** Rate-limit errors use generic "Too many requests" — never "User not found" or "Incorrect password".

**Threat:** Redis unavailable causes rate limiter to fail.  
**Mitigation:** Fail-open: request is allowed, warning is logged. Rate limiting is defence-in-depth, not the only auth control.

### Consent management

**Threat:** Attacker forges a consent record for a user.  
**Mitigation:** Consent records are created server-side after authentication. Client cannot inject arbitrary records.

**Threat:** Attacker reads consent records of another user.  
**Mitigation:** `GET /api/v1/consent` is auth-gated; returns only current user's records.

**Threat:** Consent text changes after user consented, but `text_version` still shows as valid.  
**Mitigation:** `text_version` is a SHA-256 of the exact text shown at consent time. Even if the stored document changes, the hash provides proof of the original text.

### GDPR data export

**Threat:** Attacker downloads another user's export.  
**Mitigation:** Export is auth-gated. Only current user can export their own data.

**Threat:** Export endpoint used as a DoS vector (large JSON responses).  
**Mitigation:** Rate limiting applies. Export is bounded by user's own data (not a full-table scan).

### GDPR erasure

**Threat:** Attacker deletes another user's account.  
**Mitigation:** Deletion endpoint is auth-gated; requires explicit confirm string "DELETE MY ACCOUNT".

**Threat:** Account deletion is accidental.  
**Mitigation:** Confirmation string required. Operation is logged. No soft-delete — action is permanent.

---

## High-priority open items (post-M3)

---

## Out of scope for M1

- Third-party integrations (none exist)
- Mobile client threats
- Physical security
- Insider threat (organisational)

---

## Review cadence

This document must be updated at:
- Every new feature milestone
- After any security incident
- At least every 6 months
- Before any penetration test

---

## References

- [STRIDE methodology](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats)
- [OWASP Top 10](https://owasp.org/Top10/)
- [VERIDA TRUST_MODEL.md](./TRUST_MODEL.md)
- [VERIDA TOMs.md](./TOMs.md)
