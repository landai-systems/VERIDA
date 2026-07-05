# Privacy Policy & GDPR Compliance

**Last updated:** 2026-07-05 (M3)
**Applies to:** VERIDA platform (staging and production)  
**Data controller:** VERIDA / landai-systems  
**Contact:** privacy@verida.example (replace with real address before launch)

---

## 1. Data we collect

| Category | Data | Purpose | Legal basis |
|----------|------|---------|-------------|
| Account | Handle, email, display name, password hash (Argon2id) | Account management | Contract (Art. 6(1)(b)) |
| Content | Photos/videos, captions, timestamps | Core service | Contract (Art. 6(1)(b)) |
| Attestation | Media hash, capture metadata, attestation score | Platform integrity | Legitimate interest (Art. 6(1)(f)) |
| Session | Refresh token hash, login timestamps | Security | Legitimate interest (Art. 6(1)(f)) |
| Technical | IP address truncated to /24 prefix (in logs, TTL 7 days) | Security, abuse prevention | Legitimate interest (Art. 6(1)(f)) |
| Consent | Consent type, version, text hash, timestamp, /24 IP hash | Legal accountability | Legal obligation (Art. 5(2)) |
| Reactions | Emoji type per post (private, never shown publicly) | Core service | Contract (Art. 6(1)(b)) |
| Comments | Plain-text comment body, timestamp | Core service | Contract (Art. 6(1)(b)) |
| Streaks | Post date history, streak count | Core service | Contract (Art. 6(1)(b)) |

We do **NOT** collect:
- Full IP addresses (truncated to /24 before any storage)
- EXIF / location data from media (stripped on upload)
- Device identifiers, advertising IDs
- Data from third-party services (none used)
- Biometric data

---

## 2. Versioned consent flows

### 2.1 Consent types

| Type | Required for service | Can be withdrawn |
|------|---------------------|------------------|
| `terms_of_service` | Yes (account creation) | Yes (terminates account) |
| `privacy_policy` | Yes (account creation) | Yes (terminates account) |
| `data_processing` | Yes (core service) | Yes (terminates account) |
| `marketing` | No | Yes (stops marketing only) |

### 2.2 Versioning

Each consent document has a semantic version (e.g. `"1.0"`, `"1.1"`).  
When a document is updated:
1. Users are shown the new version at next login
2. They must re-consent to continue using the service
3. A new `ConsentRecord` is created with the new `version` and `text_version`

### 2.3 text_version

`text_version` is the SHA-256 hex digest of the **exact text shown to the user** at the time of consent. This provides cryptographic proof of which version of the consent text the user agreed to — even if the stored document changes later.

### 2.4 IP privacy in consent records

Only the /24 prefix of the IP address is stored, after hashing with SHA-256. This allows network-level accountability without per-user IP tracking. Full IPs are **never stored** in consent records.

### 2.5 Withdrawal

Withdrawing consent is **as easy as granting it** (GDPR Art. 7(3)):
- Available at: `POST /api/v1/consent/withdraw`
- Effect is immediate
- Withdrawal records the `withdrawn_at` timestamp on the existing consent record (append-only)
- For required consent types (ToS, Privacy Policy, Data Processing), withdrawal initiates account deletion

---

## 3. Data retention schedules

| Data type | Retention period | Deletion trigger |
|-----------|-----------------|-----------------|
| User account | Until account deletion | User request (Art. 17) |
| Posts + media | Until account deletion | User request (Art. 17) |
| Consent records | Retained per Art. 5(2) accountability | Account deletion (cascade) |
| Refresh tokens (expired) | Purged nightly via `purge_expired_tokens` cron | Automatic |
| IP logs | 7 days max | Rolling TTL in log system |
| Attestation data | Until post deletion | Post deletion (cascade) |
| Reactions | Until user or post deletion | Cascade |
| Comments | Soft-deleted; hard-purged on account deletion | Account deletion |
| Streaks | Until account deletion | Account deletion (cascade) |

---

## 4. Article 20 — Right to data portability

Users can export all their data as a structured JSON document at any time:

```
POST /api/v1/gdpr/export
Authorization: Bearer <token>
```

The export includes:
- User profile (excluding password hash)
- All posts + attestation results
- Circle memberships
- All comments authored by the user
- All reactions by the user
- Full consent record history
- Streak data

The export is returned as a JSON file download (`Content-Disposition: attachment`).

**Implementation:** `ExportUserDataUseCase` in `application/use_cases/gdpr.py`

---

## 5. Article 17 — Right to erasure ("right to be forgotten")

Users can permanently delete their account and all associated data:

```
DELETE /api/v1/gdpr/me
Authorization: Bearer <token>
Content-Type: application/json

{"confirm": "DELETE MY ACCOUNT"}
```

The confirmation string prevents accidental deletion.

**What is deleted:**
1. User account deactivated immediately (prevents login during deletion process)
2. Comments hard-deleted
3. Reactions hard-deleted
4. Streak data hard-deleted
5. User row hard-deleted (cascades to posts, circles, tokens, consent records via ON DELETE CASCADE)
6. Async purge job scheduled for any remaining cleanup (media files, Redis keys)

**Implementation:** `DeleteUserDataUseCase` in `application/use_cases/gdpr.py`

**Note on consent records:** GDPR Art. 5(2) requires controllers to demonstrate lawful basis for processing. Consent records may be retained as evidence of lawful processing even after account deletion. In the current implementation, consent records cascade-delete with the user row.

---

## 6. No third-party services

VERIDA does not use any third-party data processors, analytics services, advertising networks, or CDNs that would constitute international data transfers. All processing occurs on self-hosted infrastructure.

---

## 7. Security measures (technical and organisational — TOMs)

See `docs/TOMs.md` for the full Technical and Organisational Measures document.

Key measures relevant to this privacy policy:
- Passwords hashed with Argon2id (time_cost=2, memory=64 MiB)
- Refresh tokens stored as SHA-256 hashes only
- All API communication over HTTPS (enforced via HSTS)
- CSRF protection via SameSite cookies
- Rate limiting on authentication endpoints (Redis sliding window)
- IP addresses truncated to /24 before any storage or logging
- Media EXIF data stripped on upload
- CSP headers prevent injection attacks (`no unsafe-inline`)

---

## 8. Contact and rights

To exercise your rights under GDPR (access, rectification, erasure, portability, objection):

- **In-app:** Use the data export and account deletion endpoints above
- **Email:** privacy@verida.example (replace before launch)
- **Supervisory authority:** The competent authority in your EU member state.
  In Germany: Bundesbeauftragte für den Datenschutz und die Informationsfreiheit (BfDI)

You have the right to lodge a complaint with your supervisory authority at any time.

---

## 9. German summary / Deutschsprachige Zusammenfassung

**VERIDA Datenschutzerklärung (Zusammenfassung)**

Wir erheben nur die Daten, die für den Betrieb der Plattform unbedingt erforderlich sind. Insbesondere:

- **IP-Adressen** werden nur als /24-Präfix gespeichert (z.B. wird `203.0.113.45` zu `203.0.113.0/24`) und anschließend gehasht. Vollständige IP-Adressen werden nicht gespeichert.
- **Einwilligungen** werden versioniert gespeichert. Der Widerruf ist jederzeit so einfach wie die Erteilung der Einwilligung (Art. 7 Abs. 3 DSGVO).
- **Datenexport** (Art. 20 DSGVO): Alle Ihre Daten können als JSON-Datei heruntergeladen werden.
- **Löschung** (Art. 17 DSGVO): Ihr Konto und alle zugehörigen Daten können vollständig und unwiderruflich gelöscht werden.
- **Drittanbieter**: Keine. Alle Verarbeitung erfolgt auf eigenen Servern.

Bei Fragen oder zur Ausübung Ihrer Datenschutzrechte wenden Sie sich an: privacy@verida.example

Zuständige Aufsichtsbehörde in Deutschland: Bundesbeauftragte für den Datenschutz und die Informationsfreiheit (BfDI), https://www.bfdi.bund.de/
