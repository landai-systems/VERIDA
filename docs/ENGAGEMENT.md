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

**Mechanic (M3 — implemented):** Consecutive days of posting earn a streak.

**Implementation:**
- `UserStreak` entity tracks `current_streak`, `longest_streak`, `last_post_date`
- `UpdateStreakUseCase` is called after each successful post submission
- `GET /api/v1/me/streak` returns streak info

**Grace-day mechanics:**
- Users may miss **up to 2 days per calendar month** without losing their streak
- `grace_days_used_this_month` counter resets on the 1st of each calendar month
- Missing 1 day: uses 1 grace day, streak extends by 1
- Missing 2 days: uses 2 grace days, streak extends by 1
- Missing 3+ days: streak resets to 1 (no grace remaining)

**What the API returns:**
```json
{
  "current_streak": 12,
  "longest_streak": 28,
  "last_post_date": "2024-06-15"
}
```

**What the API intentionally OMITS:**
- ❌ `days_until_reset` — no countdown pressure
- ❌ `grace_days_remaining` — no "you're running out" anxiety
- ❌ Any message framing (that's the frontend's responsibility, with ethical constraints below)

**Frontend contract (enforcement):**
The frontend **MUST NOT**:
- Show "You'll lose your streak in X days" messages
- Show red-dot badges or urgent colours on the streak indicator
- Send push notifications about streak risk
- Use copy like "Don't break your streak!" or "You're on a roll — don't stop now!"

The frontend **MAY**:
- Show the streak number in a neutral, celebratory way
- Mention the longest streak as a positive achievement
- Quietly show a 🔥 or ✨ emoji next to the streak number

**Rationale:**
Countdown-based streak mechanics (Duolingo, Snapchat) are documented to create anxiety and compulsive behaviour. VERIDA streaks are purely informational and positive — they reward consistency without punishing gaps. Users shouldn't feel they need to open the app to prevent losing something.

**Guard rails (mandatory):**
- No streak-shaming: no public display of streak breaks
- Streak loss does NOT send push notifications to pressure re-engagement
- The streak badge is subtle, not prominent
- Users can opt out of streaks entirely (deleting streak data via GDPR export/delete)
- We will never add "streak freeze" purchases

---

### 4. Reactions

**Mechanic (M3 — implemented):** A limited set of curated reactions.

**Implementation:**
- `Reaction` entity, `ReactionModel` (unique: one emoji type per user per post)
- `AddReactionUseCase` (idempotent), `RemoveReactionUseCase`, `GetReactionsUseCase`
- `POST/DELETE /api/v1/posts/{id}/reactions`
- `GET /api/v1/posts/{id}/reactions` — returns **only the current user's reactions**

**Allowed emoji (warm, positive set):**
| Emoji | Value | Character name |
|-------|-------|---------------|
| ❤️ | `\u2764\ufe0f` | Red heart |
| 😊 | `\U0001f60a` | Smiling face with smiling eyes |
| 🔥 | `\U0001f525` | Fire |
| 🌟 | `\U0001f31f` | Glowing star |
| 🤗 | `\U0001f917` | Hugging face |

**No public counters (MVP invariant):**

The `GetReactionsUseCase` only returns reactions by the **current user** — not counts of all reactions. This is an intentional, load-bearing design decision:

- Public counts create competition ("my photo got 47 ❤️s, yours got 12")
- Social comparison via counts is linked to anxiety and decreased wellbeing
- Knowing that *you* reacted warm to someone's moment is sufficient
- Total counts can be added later if there's strong user demand; removing them after the fact is much harder

**What the API returns:**
```json
[
  {"id": "...", "post_id": "...", "emoji": "❤️"}
]
```
This is the CURRENT USER's reactions only. No counts, no other users' reactions.

**Rationale:**
The warm emoji set was chosen to enable positive emotional acknowledgment without enabling comparison or negative reactions. No thumbs-down, no angry face. VERIDA moments are personal — the appropriate response is support or warmth, not judgment.

**Guard rails:**
- One reaction per emoji per user per post (enforced at DB + application layer)
- No reaction leaderboards
- No "X people reacted" copy

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
