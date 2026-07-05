# STRIDE Threat Model — VERIDA

**Framework:** STRIDE (Microsoft)  
**Scope:** VERIDA M1 API + Auth system  
**Last updated:** 2026-07-05  
**Status:** Skeleton — to be expanded with mitigations before M3 launch

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
| Fake capture (pre-recorded video) | Capture flow | High | Medium | Heuristic attestation; see TRUST_MODEL.md | ⚠️ Partial |

### T — Tampering

| Threat | Component | Likelihood | Impact | Mitigation | Status |
|--------|-----------|-----------|--------|-----------|--------|
| Media modified after upload | Post | Medium | High | SHA-256 hash recorded at submission | ✅ M1 |
| Database record modification | DB | Low | Critical | DB user has no DDL; audit log planned | 🔶 M4 |
| JWT payload tampering | Auth | Low | Critical | HS256 signature verification | ✅ M1 |
| Capture metadata injection | Attestation | High | Medium | Heuristic bounds checks | ⚠️ Partial |

### R — Repudiation

| Threat | Component | Likelihood | Impact | Mitigation | Status |
|--------|-----------|-----------|--------|-----------|--------|
| User denies posting content | Post | Medium | Medium | Attestation record + timestamp immutable | ✅ M1 |
| Admin denies making change | Admin | Low | Medium | Audit log for admin actions | 🔶 M3 |

### I — Information Disclosure

| Threat | Component | Likelihood | Impact | Mitigation | Status |
|--------|-----------|-----------|--------|-----------|--------|
| Password leak via API | Auth | Low | Critical | Argon2id hash only; hash never returned | ✅ M1 |
| Refresh token in logs | Auth | Low | High | Only token hash logged; raw token never logged | ✅ M1 |
| User email in error messages | API | Medium | Medium | Generic error messages; no field name leak | ✅ M1 |
| Private post visible to non-member | Posts | Medium | High | Circle membership checks | 🔶 M2 |
| Log files contain PII (IP, email) | Infra | Medium | Medium | Log retention 7 days; future: log scrubbing | 🔶 M4 |

### D — Denial of Service

| Threat | Component | Likelihood | Impact | Mitigation | Status |
|--------|-----------|-----------|--------|-----------|--------|
| Brute-force login | Auth | High | Medium | Rate limiting at gateway layer | 🔶 M3 |
| Large media upload flood | Upload | Medium | High | File size limits; rate limiting | 🔶 M2 |
| Attestation compute flood | Attestation | Low | Medium | arq queue; worker autoscaling | 🔶 M2 |
| Dependency confusion / supply chain | Build | Low | Critical | pip-audit + gitleaks in CI | ✅ M1 |

### E — Elevation of Privilege

| Threat | Component | Likelihood | Impact | Mitigation | Status |
|--------|-----------|-----------|--------|-----------|--------|
| Regular user accesses admin endpoint | Admin | Medium | Critical | Role-based access control | 🔶 M3 |
| SQL injection via ORM | DB | Low | Critical | SQLAlchemy parameterised queries | 🔶 M2 |
| SSRF via media URL | Infrastructure | Low | High | Validate media URLs; no outbound fetches | 🔶 M2 |
| Accidental prod deployment | Infra | Medium | Critical | DO_NOT_DEPLOY guard | ✅ M1 |

---

## High-priority open items

1. **Rate limiting** on auth endpoints (M3) — brute-force is currently unbounded
2. **Circle membership enforcement** on post queries (M2) — visibility not yet enforced
3. **SQL injection review** when SQLAlchemy models are added (M2)
4. **SSRF prevention** for any feature that fetches external URLs (M2)
5. **Role-based access control** for admin endpoints (M3)

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
