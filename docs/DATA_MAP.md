# Data Map — VERIDA Data Inventory

**Purpose:** Fulfils GDPR Article 30 (Records of Processing Activities) obligation.  
**Last updated:** 2026-07-05 (M3)  
**Owner:** Data Protection Lead (to be designated before launch)

---

## Data inventory table

| Data element | Table / Field | Category | PII? | Encrypted at rest? | Encrypted in transit? | Retention | Basis |
|---|---|---|---|---|---|---|---|
| Email address | `users.email` | Account | ✅ Yes | ✅ DB-level | ✅ TLS | Until deletion + 30d | Contract |
| Handle (@username) | `users.handle` | Account | Pseudonym | ✅ | ✅ | Until deletion + 30d | Contract |
| Display name | `users.display_name` | Account | Indirect | ✅ | ✅ | Until deletion + 30d | Contract |
| Argon2id hash | `users.argon2_hash` | Account | Derived | ✅ | ✅ | Until deletion + 30d | Contract |
| Avatar URL | `users.avatar_url` | Content | Indirect | ✅ | ✅ | Until deletion + 30d | Contract |
| Bio | `users.bio` | Content | Possible | ✅ | ✅ | Until deletion + 30d | Contract |
| Media file (photo/video) | Object storage | Content | ✅ Yes | ✅ | ✅ | Until deletion | Contract |
| Media SHA-256 hash | `posts.media_hash` | Integrity | No | ✅ | ✅ | 2 years | Leg. interest |
| Caption | `posts.caption` | Content | Possible | ✅ | ✅ | Until deletion | Contract |
| Capture metadata | `posts.capture_metadata` (JSONB) | Technical | No | ✅ | ✅ | 2 years | Leg. interest |
| Attestation score | `attestations.score` | Integrity | No | ✅ | ✅ | 2 years | Leg. interest |
| Attestation details | `attestations.details` (JSONB) | Integrity | No | ✅ | ✅ | 2 years | Leg. interest |
| Refresh token hash | `refresh_tokens.token_hash` | Security | No | ✅ | ✅ | 30 days / logout | Leg. interest |
| IP address (logs) | Application logs | Technical | ✅ Yes | ✅ | ✅ | 7 days | Leg. interest |
| Login timestamps | `users.updated_at`, logs | Technical | Indirect | ✅ | ✅ | 7 days (logs) | Leg. interest |
| Circle name/description | `circles.*` | Social | Possible | ✅ | ✅ | Until deletion | Contract |
| Circle membership | `circle_memberships.*` | Social | Derived | ✅ | ✅ | Until deletion | Contract |
| Consent type + version | `consent_records.consent_type`, `.version` | Legal | No | ✅ | ✅ | Art. 5(2) accountability | Legal obligation |
| Consent text hash | `consent_records.text_version` | Legal | No | ✅ | ✅ | Art. 5(2) accountability | Legal obligation |
| Consent IP hash | `consent_records.ip_hash` | Legal | Derived | ✅ | ✅ | Art. 5(2) accountability | Legal obligation |
| Reaction emoji | `reactions.emoji` | Social | No | ✅ | ✅ | Until deletion | Contract |
| Comment body | `comments.body` | Content | Possible | ✅ | ✅ | Until deletion | Contract |
| Streak count | `user_streaks.current_streak`, `.longest_streak` | Behavioural | Indirect | ✅ | ✅ | Until deletion | Contract |
| Last post date | `user_streaks.last_post_date` | Behavioural | Indirect | ✅ | ✅ | Until deletion | Contract |

---

## Data flows

```
Browser (HTTPS/TLS)
  └─→ API (Docker / Caddy TLS termination)
        ├─→ PostgreSQL 16 (encrypted at rest, local network only)
        ├─→ Redis (local network only, no PII stored)
        └─→ Object Storage (TLS, presigned URLs)
```

**External transfers:** None in M1–M2. All data stays within EU/EEA.

---

## Data minimisation checks

- [ ] Do we collect location data? **No** — no GPS, no IP geolocation stored
- [ ] Do we collect device identifiers? **No** — browser fingerprint is a SHA-256 hash, not stored long-term
- [ ] Do we use third-party analytics? **No**
- [ ] Do we share data with advertisers? **No**

---

## Review schedule

This document must be reviewed at:
- Every new feature that introduces a new data element
- Annually (GDPR Art. 30 requirement)
- Before any new third-party processor is added
