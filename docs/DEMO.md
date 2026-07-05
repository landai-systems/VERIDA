# VERIDA Demo Script

> **Audience:** Developer / product presentation  
> **Time:** ~15 minutes  
> **Prerequisites:** Docker Desktop running, `make` available

---

## Step 0 — Start the stack

```bash
make up       # docker compose up --build -d
make migrate  # alembic upgrade head
make seed     # load 10 synthetic users, 30 posts, 3 circles
```

**Talking points:**
- Single `make up` brings up: FastAPI (uvicorn), PostgreSQL 16, Redis, arq worker, Mailpit (email capture), and Vite dev server
- `make seed` is deterministic — Faker seed 42, same data every run
- Expected output: `Seeded: 10 users, 30 posts, 3 circles`

---

## Step 1 — Open the app

```
http://localhost:5173
```

**[SCREENSHOT PLACEHOLDER: Landing page — dark slate hero with VERIDA logo, Sign in / Sign up buttons]**

**Talking points:**
- Mobile-first PWA — installable from browser menu
- Sub-2s TTI on mid-range mobile (lazy-loaded page chunks ~2–9 KB each)
- Lighthouse mobile score ≥ 90 (performance, accessibility, PWA)

---

## Step 2 — Register a new account

Navigate to **Sign up** → fill in:
- Name: your name
- Handle: `@demo`
- Email: `demo@example.com`
- Password: `supersecret123!`
- ☑ Accept privacy policy

**[SCREENSHOT PLACEHOLDER: Register form with consent checkbox, indigo CTA button]**

**Talking points:**
- Consent checkbox is required — records an append-only `ConsentRecord` with SHA-256 of the exact consent text (Art. 7 compliance)
- Email sent to **Mailpit** for verification

---

## Step 3 — Verify email (Mailpit)

```
http://localhost:8025
```

Open the verification email and click the link.

**[SCREENSHOT PLACEHOLDER: Mailpit inbox showing VERIDA verification email]**

**Talking points:**
- Email never logged at INFO level (privacy by design)
- Verification token is one-time-use with 24h expiry

---

## Step 4 — Reciprocity gate (capture first)

After login, the feed shows:

> "Post your moment first to unlock the feed."

Click **Capture Today's Moment**.

**[SCREENSHOT PLACEHOLDER: Reciprocity gate screen with camera icon and CTA]**

**Talking points:**
- Reciprocity gate: you must share before you see others' shares
- This is the core anti-lurk mechanic — no passive consumption without contribution

---

## Step 5 — Capture a moment

On the Capture page:
1. Browser prompts for camera permission → live viewfinder appears
2. 10-minute countdown timer runs (HMAC-signed token)
3. Click **📸 Capture** → preview shown
4. Add optional caption → **Share Moment**

**[SCREENSHOT PLACEHOLDER: Camera viewfinder with countdown timer "9:42 remaining"]**

**Talking points:**
- `getUserMedia` — live camera only; gallery uploads are rejected at backend
- EXIF stripped server-side (Pillow)
- Attestation badge shows ⏳ Pending immediately after submit
- arq background worker runs 9 heuristics (timing, EXIF, phash dedup, etc.)

---

## Step 6 — View the feed

After capture, the feed unlocks showing the seeded 30 posts.

**[SCREENSHOT PLACEHOLDER: Feed with 3–4 post cards, attestation badges, reaction bar]**

**Talking points:**
- Posts are chronological (oldest-first)
- Each card shows: author avatar, handle, timestamp, attestation badge (✓ Human-verified), optional Late badge
- End of feed: "🌿 You're all caught up!" — no infinite scroll anxiety
- After 10 minutes continuous use: session nudge modal appears ("Take a break? 🌿")

---

## Step 7 — React to a post

Tap any emoji in the reaction bar: ❤️ 😊 🔥 🌟 🤗

**[SCREENSHOT PLACEHOLDER: Reaction bar with ❤️ highlighted (active ring)]**

**Talking points:**
- Reactions are private — no public counters shown (avoids like-count anxiety)
- One reaction per emoji per user per post (unique constraint)
- Warm emoji set only — no negative reactions

---

## Step 8 — Leave a comment

Click **💬 Comment** on any post → type a message → Post.

**[SCREENSHOT PLACEHOLDER: Comment section with 500-char counter]**

**Talking points:**
- 500 char limit with live counter
- Plain text only — no markdown, no mentions
- Authors can delete their own comments

---

## Step 9 — Circles management

Navigate to **Circles** (via bottom nav or Profile → Circles link).

- Seeded circles: Close Friends, Family, Work Buds
- Create a new circle → invite by `@handle`

**[SCREENSHOT PLACEHOLDER: Circles list with 3 cards, invite input field]**

**Talking points:**
- Max 30 members enforced at application layer
- Invite → accept flow (no open-circle discovery)
- Private by default

---

## Step 10 — Profile & streak

Navigate to **Profile**.

**[SCREENSHOT PLACEHOLDER: Profile page with streak badge 🔥 7, archive grid thumbnails]**

**Talking points:**
- Streak shown as 🔥 N days — no countdown, no guilt copy
- Grace days: up to 2/month, resets monthly
- "Your Authentic Year" grid — chronological personal archive
- Streak mechanics documented in `docs/ENGAGEMENT.md`

---

## Step 11 — GDPR export

Navigate to **Settings** → **⬇ Export My Data (Article 20)**.

Downloads a JSON file with: profile, posts, circles, comments, reactions, consent records, streak.

**[SCREENSHOT PLACEHOLDER: Settings page with GDPR section]**

**Talking points:**
- Art. 20 data portability — structured JSON, no argon2 hash exported
- Art. 17 erasure: "Delete Account" requires typing `DELETE MY ACCOUNT` — prevents accidental deletion
- Consent withdrawal: toggles individual consent types, append-only audit trail

---

## Step 12 — Archive view

Navigate to **Archive** (Profile → Your Archive).

Posts grouped by month — personal record of every authentic moment.

**[SCREENSHOT PLACEHOLDER: Archive grid grouped by "July 2026", "June 2026" etc.]**

---

## Lighthouse

To verify PWA / performance:

```bash
make lighthouse
# Instructions: open Chrome → DevTools → Lighthouse → Mobile
# Run against http://localhost:5173
```

Target: ≥ 90 on Performance, Accessibility, PWA.

Key optimizations already in place:
- Lazy-loaded page chunks (2–9 KB gzipped each)
- `vendor` chunk split (React + Router)
- Workbox service worker (precache + NetworkFirst for API)
- `loading="lazy"` on all images
- Semantic HTML with ARIA labels throughout

---

## Tear down

```bash
make down
```

---

## Seed users for manual login

All seed users share password: (not a real password — seed script uses argon2 placeholder).

For interactive login, register a fresh account via the UI (Step 2).
