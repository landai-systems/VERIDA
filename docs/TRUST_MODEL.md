# Trust Model — What VERIDA Attestation Proves (and Doesn't)

**Read this document before relying on attestation status for any trust decision.**

---

## What VERIDA attests

When a post shows a "PASSED" attestation, it means:

1. **A SHA-256 hash of the media was recorded at submission time.**  
   If the media file was altered after upload, the hash would no longer match.

2. **The MIME type was in the approved set** (JPEG, PNG, WebP, WebM, MP4).

3. **The reported capture metadata (duration, resolution) is within plausible ranges.**

4. **The caption length is within acceptable bounds.**

That is all. These are heuristic checks.

---

## What VERIDA does NOT prove

VERIDA's M1–M2 attestation system explicitly does **NOT** prove:

| Claim | Why it's NOT proven |
|-------|---------------------|
| The content was captured live, in real time | A pre-recorded video can pass all heuristic checks |
| The person in the content is the account holder | No face verification; account could be shared |
| The content is unmodified from what the camera captured | Hash is client-reported; a malicious client can lie |
| The content was captured on the device's camera | getUserMedia can be spoofed with virtual cameras |
| The moment happened at the reported time | Timestamps are client-reported |
| The content is not AI-generated | AI-generated images pass MIME and hash checks |

---

## What we're being honest about

VERIDA's attestation provides **social friction**, not cryptographic proof.
It raises the cost of faking a live moment without making it impossible.

This is a deliberate design choice in M1–M2. In later milestones (M3+) we plan to explore:

- **On-device ML liveness detection** — checks for camera feed artifacts
- **Challenge-response during capture** — server-issued visual challenge displayed during recording
- **Signed media hashes** — hash signed on-device with hardware-backed key
- **Ambient noise cross-correlation** — optional, privacy-preserving signal

Even with all of the above, VERIDA cannot claim absolute proof-of-human.
We will always communicate this limitation to users.

---

## Transparency commitments

1. Attestation status and score are visible to the post author.
2. Attestation rejection reasons are provided in plain language.
3. Users can appeal flagged content.
4. We will never market VERIDA attestation as "fraud-proof" or "AI-proof".
5. This document is public and versioned in the repository.

---

## For auditors

The heuristic logic lives in:
```
backend/src/verida/infrastructure/heuristic_authenticity.py
```

The ContentAuthenticityPort Protocol (which any future ML-based adapter must implement) is in:
```
backend/src/verida/application/ports.py
```

All attestation records are stored in the database and never deleted
(they are part of the audit trail).
