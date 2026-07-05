# Trust Model — What VERIDA Attestation Proves (and Doesn't)

**Read this document before relying on attestation status for any trust decision.**

---

## What VERIDA attests (M3 upgraded heuristics)

When a post shows a "PASSED" attestation, it means all of the following
heuristics passed. **Read the limitations carefully before trusting any of these.**

| Heuristic | What it checks | Can be faked? |
|-----------|---------------|---------------|
| `media_hash_present` | SHA-256 hash submitted and valid hex | Yes — client reports its own hash |
| `mime_type_allowed` | MIME type in approved set (JPEG, PNG, WebP, WebM, MP4) | Yes — trivial to spoof |
| `capture_duration_plausible` | Reported duration 0.5–60 seconds | Yes — client-reported |
| `resolution_plausible` | Width/height within camera bounds, aspect ratio sane | Yes — client-reported |
| `timing_window` | Post published within 20 minutes of server time | Partially — server-side check |
| `exif_absent` | No EXIF/GPS/camera-model fields in metadata | Partially — client can omit |
| `phash_unique` | Perceptual hash not seen in Redis in past 7 days | Partially — cropping evades it |
| `metadata_completeness` | All expected fields present (duration, resolution, captured_at) | Yes — client-reported |
| `gallery_upload_absent` | No signals indicating file-picker / gallery source | Partially — client can omit |

**Score:** Each heuristic contributes equally. Final score = mean of all heuristic scores.  
**PASSED** = score ≥ 0.60 | **FLAGGED** = 0.30–0.60 | **REJECTED** = < 0.30

**Replay detection:** The `phash_unique` check uses a Redis sorted set to track
perceptual hashes of recent posts. Near-duplicate replays (e.g. uploading the same
photo twice) are detected. Note: cropping or applying a filter will evade this check.
This is documented as a limitation, not a security claim.

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
