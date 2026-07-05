# Engagement Mechanics & Ethical Rationale

This document describes how VERIDA is designed to engage users, and the ethical reasoning behind every mechanic.

---

## Core design principle

> **Engagement is a means, not an end.**

VERIDA's goal is to create a space for genuine human connection.
Every engagement mechanic is evaluated against: *does this serve users, or does it exploit them?*

---

## Mechanics

### 1. Daily Moments

**Mechanic:** Each user can post one moment per day, within a short capture window.

**Rationale:**
- Scarcity creates intentionality. One post per day means each one matters.
- Prevents VERIDA from becoming another dopamine scroll feed.
- The spontaneous capture requirement (live in-browser) reduces performative posting.

**Guard rails:**
- No re-opens of the capture window after abandonment (configurable, 5-minute window).
- No editing after submission.
- Clear communication that attestation is heuristic, not cryptographic.

---

### 2. Circles (not "followers")

**Mechanic:** Posts are shared with named circles, not a follower graph.

**Rationale:**
- Encourages intentional sharing with people you actually know.
- Reduces the anxiety of public performance.
- Privacy-preserving: default visibility is circles-only, not public.

**Guard rails:**
- Circles are invite-only by default.
- No public follower counts.
- No algorithmic "suggested circles" in M1–M2 (avoids filter bubbles).

---

### 3. Streaks

**Mechanic (M3+):** Consecutive days of posting earn a streak.

**Rationale:**
- Streaks reward consistency, which is genuinely valuable.
- A short daily commitment is healthy and achievable.

**Guard rails (mandatory):**
- Streaks reset gracefully with a "grace day" after travel or illness.
- No streak-shaming: no public display of streak breaks.
- Streak loss does NOT send push notifications to pressure re-engagement.
- The streak badge is subtle, not prominent.
- Users can opt out of streaks entirely.
- We will never add "streak freeze" purchases.

---

### 4. Reactions

**Mechanic (M3+):** A limited set of curated reactions (not "likes").

**Rationale:**
- Replaces the binary "like" with richer emotional acknowledgment.
- The limited palette prevents reaction inflation.

**Guard rails:**
- Reaction counts are visible only to the post author, not other viewers.
- No total count displayed publicly ("you and 47 others").
- No reaction leaderboards.

---

### 5. Notifications

**Mechanic (M3+):** In-app and email digest for circle activity.

**Rationale:**
- Users deserve to know when people engage with their moments.

**Guard rails:**
- Default: daily digest only. Real-time push is opt-in.
- No "your friend hasn't posted in 3 days" guilt notifications.
- Quiet hours respected (no notifications between 22:00–08:00 local time unless user overrides).
- Unsubscribe from all notifications in one click, always.

---

## What we will NOT implement

| Mechanic | Reason |
|----------|--------|
| Infinite scroll | Designed to exhaust rather than satisfy |
| Algorithmic content ranking | Erodes serendipity; creates filter bubbles |
| Public follower/like counts | Incentivises vanity over authenticity |
| Variable-ratio reward (slot machine feed) | Exploits dopamine systems |
| Social pressure notifications | "Your friend is waiting for your moment" |
| Paid streak freezes | Monetises anxiety |
| Dark patterns on delete/deactivate | Users have the right to leave easily |

---

## Review process

Every new engagement mechanic proposed must be reviewed against this document
by at least two team members before implementation.
Changes to this document require an ADR.
