#!/usr/bin/env python3
"""
VERIDA Staging Seed Script
Faker(seed=42) — fully deterministic.

Usage (inside container via make seed):
    python scripts/seed.py

Requires DATABASE_URL env var (set automatically in Docker Compose).
Uses psycopg2 (sync) — install psycopg2-binary for the seed to work.
"""
from __future__ import annotations

import hashlib
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Path setup (works both in container /app and locally from backend/) ───────
_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

try:
    from faker import Faker
except ImportError:
    print("ERROR: faker not installed. Run: pip install faker")
    sys.exit(1)

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
except ImportError:
    print("ERROR: sqlalchemy not installed.")
    sys.exit(1)

try:
    from verida.infrastructure.db.models import (
        AttestationModel,
        Base,
        CircleMembershipModel,
        CircleModel,
        CommentModel,
        ConsentRecordModel,
        DailyMomentModel,
        PostModel,
        ReactionModel,
        UserModel,
        UserStreakModel,
    )
except ImportError as e:
    print(f"ERROR: Could not import verida models: {e}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

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

    # ── 1. Users ──────────────────────────────────────────────────────────────
    users: list[UserModel] = []
    for i in range(10):
        u = UserModel(
            id=_uuid(),
            handle=FAKE.user_name()[:20].lower().replace(".", "_"),
            email=FAKE.unique.email(),
            display_name=FAKE.name(),
            argon2_hash="$argon2id$v=19$m=65536,t=2,p=1$SEED_PLACEHOLDER",
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

    # ── 2. Circles ────────────────────────────────────────────────────────────
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

    for cidx, circle in enumerate(circles):
        members = [users[cidx]] + random.sample(
            [u for u in users if u.id != users[cidx].id], k=3
        )
        for m in members:
            db.add(CircleMembershipModel(
                id=_uuid(),
                circle_id=circle.id,
                user_id=m.id,
                role="owner" if m.id == circle.owner_id else "member",
                invite_status="accepted",
                invited_by=circle.owner_id if m.id != circle.owner_id else None,
                joined_at=_days_ago(45),
            ))
    db.flush()

    # ── 3. Posts (30 — 1/day over past 30 days) ───────────────────────────────
    posts: list[PostModel] = []
    post_users = users.copy()
    random.shuffle(post_users)

    for day in range(30):
        author = post_users[day % len(post_users)]
        posted_at = _days_ago(30 - day)

        moment = DailyMomentModel(
            id=_uuid(),
            user_id=author.id,
            capture_token=f"seed-token-{day}",
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

        db.add(AttestationModel(
            id=_uuid(),
            post_id=post.id,
            status="passed",
            score=round(0.87 + random.uniform(0, 0.12), 3),
            details={"heuristics": ["timing_ok", "no_gallery", "exif_absent"]},
            checked_at=posted_at + timedelta(seconds=30),
            created_at=posted_at,
        ))
        posts.append(post)
    db.flush()

    # ── 4. Reactions (20) ─────────────────────────────────────────────────────
    seen_combos: set[tuple] = set()
    reaction_count = 0
    attempts = 0
    while reaction_count < 20 and attempts < 100:
        attempts += 1
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

    # ── 5. Comments (15) ──────────────────────────────────────────────────────
    for _ in range(15):
        db.add(CommentModel(
            id=_uuid(),
            post_id=random.choice(posts).id,
            author_id=random.choice(users).id,
            body=FAKE.sentence(nb_words=random.randint(4, 12))[:500],
            created_at=_now(),
        ))

    # ── 6. Consent records (2 per user) ───────────────────────────────────────
    for user in users:
        for ct in ["data_processing", "analytics"]:
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

    # ── 7. Streaks ────────────────────────────────────────────────────────────
    for i, user in enumerate(users):
        db.add(UserStreakModel(
            user_id=user.id,
            current_streak=random.randint(1, 14),
            longest_streak=random.randint(5, 30),
            grace_days_used_this_month=0,
            last_post_date=(_now() - timedelta(days=i % 3)).date(),
            grace_month=None,
            updated_at=_now(),
        ))

    db.commit()
    return {"users": len(users), "posts": len(posts), "circles": len(circles)}


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        sys.exit(1)

    # Seed script uses sync SQLAlchemy — convert asyncpg URL to psycopg2
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    print(f"Connecting to database...")
    try:
        engine = create_engine(sync_url, echo=False, future=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}")
        print(f"DATABASE_URL (sanitized): {sync_url.split('@')[-1]}")
        sys.exit(1)

    with Session(engine) as session:
        print("Clearing existing data...")
        session.execute(text("SET session_replication_role = replica"))
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.execute(text("SET session_replication_role = DEFAULT"))
        session.commit()

        print("Seeding...")
        counts = seed(session)

    print(f"✅ Seeded: {counts['users']} users, {counts['posts']} posts, {counts['circles']} circles")


if __name__ == "__main__":
    main()
