#!/usr/bin/env python3
"""
VERIDA Staging Seed Script
Faker(seed=42) — fully deterministic.

Usage:
    DATABASE_URL=postgresql://... python scripts/seed.py

Prints:
    Seeded: 10 users, 30 posts, 3 circles
"""
from __future__ import annotations

import hashlib
import os
import random
import uuid
from datetime import datetime, timezone, timedelta

from faker import Faker
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Bootstrap: path so we can import verida models
# ---------------------------------------------------------------------------
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "src"))

from verida.infrastructure.db.models import (  # noqa: E402
    Base,
    UserModel,
    CircleModel,
    CircleMembershipModel,
    DailyMomentModel,
    PostModel,
    AttestationModel,
    ReactionModel,
    CommentModel,
    ConsentRecordModel,
    UserStreakModel,
)

FAKE = Faker()
Faker.seed(42)
random.seed(42)

EMOJIS = ["❤️", "😊", "🔥", "🌟", "🤗"]


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _hash(val: str) -> str:
    return hashlib.sha256(val.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(n: int) -> datetime:
    return _now() - timedelta(days=n)


def seed(db: Session) -> dict[str, int]:
    """Run the seed and return counts."""

    # ------------------------------------------------------------------
    # 1. Users
    # ------------------------------------------------------------------
    users: list[UserModel] = []
    for i in range(10):
        u = UserModel(
            id=_uuid(),
            handle=FAKE.user_name()[:20].lower().replace(".", "_"),
            email=FAKE.unique.email(),
            display_name=FAKE.name(),
            argon2_hash="$argon2id$v=19$m=65536,t=2,p=1$PLACEHOLDER",  # not real
            bio=FAKE.sentence(nb_words=10),
            avatar_url=f"https://i.pravatar.cc/150?img={i + 1}",
            is_active=True,
            is_verified=True,
            created_at=_days_ago(60 + i),
            updated_at=_days_ago(60 + i),
        )
        db.add(u)
        users.append(u)

    db.flush()

    # ------------------------------------------------------------------
    # 2. Circles (3)
    # ------------------------------------------------------------------
    circle_names = ["Close Friends", "Family", "Work Buds"]
    circles: list[CircleModel] = []
    for idx, name in enumerate(circle_names):
        owner = users[idx]
        c = CircleModel(
            id=_uuid(),
            name=name,
            description=FAKE.sentence(nb_words=6),
            owner_id=owner.id,
            is_private=True,
            created_at=_days_ago(50),
            updated_at=_days_ago(50),
        )
        db.add(c)
        circles.append(c)

    db.flush()

    # Add memberships — each circle gets 3–4 members
    membership_map: dict[uuid.UUID, list[uuid.UUID]] = {}
    for cidx, circle in enumerate(circles):
        members = [users[cidx]] + random.sample([u for u in users if u.id != users[cidx].id], k=3)
        membership_map[circle.id] = [m.id for m in members]
        for m in members:
            cm = CircleMembershipModel(
                id=_uuid(),
                circle_id=circle.id,
                user_id=m.id,
                role="owner" if m.id == circle.owner_id else "member",
                invite_status="accepted",
                invited_by=circle.owner_id if m.id != circle.owner_id else None,
                joined_at=_days_ago(45),
            )
            db.add(cm)

    db.flush()

    # ------------------------------------------------------------------
    # 3. Posts (30 — 1/day over past 30 days)
    # ------------------------------------------------------------------
    posts: list[PostModel] = []
    post_users = users.copy()
    random.shuffle(post_users)

    for day in range(30):
        author = post_users[day % len(post_users)]
        posted_at = _days_ago(30 - day)

        moment = DailyMomentModel(
            id=_uuid(),
            user_id=author.id,
            capture_token="seed-token",
            initiated_at=posted_at - timedelta(minutes=5),
            completed_at=posted_at,
            browser_fingerprint_hash=_hash(f"seed-{day}"),
        )
        db.add(moment)
        db.flush()

        post = PostModel(
            id=_uuid(),
            author_id=author.id,
            daily_moment_id=moment.id,
            caption=FAKE.sentence(nb_words=random.randint(5, 15)),
            media_url=f"https://picsum.photos/seed/verida{day}/800/600",
            media_hash=_hash(f"media-{day}"),
            media_mime_type="image/jpeg",
            visibility="circles",
            capture_metadata={"source": "camera", "seed": True},
            is_late=False,
            published_at=posted_at,
            created_at=posted_at,
            updated_at=posted_at,
        )
        db.add(post)
        db.flush()

        attestation = AttestationModel(
            id=_uuid(),
            post_id=post.id,
            status="passed",
            score=0.87 + random.uniform(0, 0.12),
            details={"heuristics": ["timing_ok", "no_gallery", "exif_absent"]},
            checked_at=posted_at + timedelta(seconds=30),
            created_at=posted_at,
        )
        db.add(attestation)
        posts.append(post)

    db.flush()

    # ------------------------------------------------------------------
    # 4. Reactions (20)
    # ------------------------------------------------------------------
    reaction_count = 0
    seen_combos: set[tuple] = set()
    for _ in range(20):
        post = random.choice(posts)
        user = random.choice(users)
        emoji = random.choice(EMOJIS)
        combo = (post.id, user.id, emoji)
        if combo in seen_combos:
            continue
        seen_combos.add(combo)
        db.add(ReactionModel(
            id=_uuid(),
            post_id=post.id,
            user_id=user.id,
            emoji=emoji,
            created_at=_now(),
        ))
        reaction_count += 1

    # ------------------------------------------------------------------
    # 5. Comments (15)
    # ------------------------------------------------------------------
    for _ in range(15):
        post = random.choice(posts)
        user = random.choice(users)
        db.add(CommentModel(
            id=_uuid(),
            post_id=post.id,
            author_id=user.id,
            body=FAKE.sentence(nb_words=random.randint(4, 12))[:500],
            created_at=_now(),
        ))

    # ------------------------------------------------------------------
    # 6. Consent records (2 per user)
    # ------------------------------------------------------------------
    consent_types = ["data_processing", "analytics"]
    for user in users:
        for ct in consent_types:
            text_blob = f"I consent to {ct} under VERIDA ToS v1.0"
            db.add(ConsentRecordModel(
                id=_uuid(),
                user_id=user.id,
                consent_type=ct,
                version="1.0",
                text_version=_hash(text_blob),
                granted_at=_days_ago(50),
                withdrawn_at=None,
                ip_hash=_hash("192.168.1.0"),
                created_at=_days_ago(50),
            ))

    # ------------------------------------------------------------------
    # 7. Streaks
    # ------------------------------------------------------------------
    for i, user in enumerate(users):
        db.add(UserStreakModel(
            user_id=user.id,
            current_streak=random.randint(1, 14),
            longest_streak=random.randint(5, 30),
            grace_days_used_this_month=0,
            last_post_date=_now().date() - timedelta(days=i % 3),
            grace_month=None,
            updated_at=_now(),
        ))

    db.commit()

    return {
        "users": len(users),
        "posts": len(posts),
        "circles": len(circles),
    }


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is required.")
        sys.exit(1)

    # Sync engine (seed script doesn't need async)
    engine = create_engine(database_url, echo=False, future=True)

    with Session(engine) as session:
        # Truncate existing seed data by clearing all rows (dev only!)
        session.execute(text("SET session_replication_role = replica"))  # disable FK checks
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.execute(text("SET session_replication_role = DEFAULT"))
        session.commit()

        counts = seed(session)

    print(f"Seeded: {counts['users']} users, {counts['posts']} posts, {counts['circles']} circles")


if __name__ == "__main__":
    main()
