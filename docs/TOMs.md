# Technical and Organisational Measures (TOMs)

**Applies to:** VERIDA platform  
**Framework:** GDPR Article 32  
**Last updated:** 2026-07-05

---

## Overview

This document lists the technical and organisational security measures implemented to protect personal data processed by VERIDA.

---

## Technical measures

### Encryption

| Measure | Status | Detail |
|---------|--------|--------|
| Encryption in transit | ✅ Implemented | TLS 1.2+ via Caddy/Traefik for all external traffic |
| Encryption at rest | ✅ Implemented | PostgreSQL database on encrypted filesystem (provider-level) |
| Password hashing | ✅ Implemented | Argon2id — time_cost=2, memory_cost=64 MiB, parallelism=2 |
| Refresh token storage | ✅ Implemented | SHA-256 hash only — plaintext never persisted |
| Secrets management | ✅ Implemented | All secrets via environment variables, validated at startup |

### Access control

| Measure | Status | Detail |
|---------|--------|--------|
| JWT authentication | ✅ Implemented | 15-minute access tokens, HS256 signed |
| Rotating refresh tokens | ✅ Implemented | Old token revoked on each rotation |
| Principle of least privilege | ✅ Implemented | DB user has CONNECT + DML only, no DDL in prod |
| Admin access | 🔶 Planned (M3) | Separate admin role with MFA requirement |
| API rate limiting | 🔶 Planned (M3) | At reverse proxy layer; not application-level |

### Availability and integrity

| Measure | Status | Detail |
|---------|--------|--------|
| Database backups | 🔶 Planned | Daily backups, 30-day retention |
| Automated health checks | ✅ Implemented | Docker healthcheck on all services |
| DO_NOT_DEPLOY guard | ✅ Implemented | Prevents accidental production deployment |
| Dependency scanning | ✅ Implemented | pip-audit in CI, runs on every PR |
| SAST | ✅ Implemented | bandit + ruff security rules in CI |
| Secret scanning | ✅ Implemented | gitleaks in CI |

### Logging and monitoring

| Measure | Status | Detail |
|---------|--------|--------|
| Structured logging | ✅ Implemented | structlog JSON format |
| Log retention | 🔶 Planned | 7 days for application logs containing PII signals |
| Metrics | 🔶 Planned (M4) | Prometheus + Grafana |
| Alerting | 🔶 Planned (M4) | PagerDuty or equivalent |
| Audit trail | ✅ Implemented | Attestation records never deleted |

---

## Organisational measures

| Measure | Status | Detail |
|---------|--------|--------|
| Data minimisation | ✅ Policy | No PII collected beyond service requirement |
| Privacy by design | ✅ Policy | New features require privacy review |
| Access control review | 🔶 Planned | Quarterly review of who has production access |
| Security training | 🔶 Planned | Annual developer security awareness |
| Incident response plan | 🔶 Planned | To be written before M4 launch |
| Vendor assessments | 🔶 Planned | DPA required for all new processors |
| Data retention enforcement | 🔶 Planned | Automated deletion jobs (M4) |

---

## Open items (before production launch)

1. Formal Data Processing Agreement (DPA) with hosting provider
2. Penetration test (at least once before M4 launch)
3. Privacy Impact Assessment (PIA) update
4. Incident response runbook
5. MFA for admin accounts
6. Automated log rotation with verified PII purge
7. Backup restore test procedure

---

## Change log

| Date | Change |
|------|--------|
| 2026-07-05 | Initial TOMs document — M1 scope |
