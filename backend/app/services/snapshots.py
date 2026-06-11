"""Coaching snapshot cache.

AI output is cached per (user, snapshot_type, request params) and reused for
COACHING_CACHE_HOURS unless meaningful new data arrives — a newly logged
session for most snapshot types, or 3+ new sessions of an exercise for
plateau checks.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import CoachingSnapshot, WorkoutSession, WorkoutSet
from app.services.coaching_data import ensure_utc


async def latest_snapshot(
    db: AsyncSession, user_id: UUID, snapshot_type: str, request: dict
) -> CoachingSnapshot | None:
    stmt = (
        select(CoachingSnapshot)
        .where(
            CoachingSnapshot.user_id == user_id,
            CoachingSnapshot.snapshot_type == snapshot_type,
        )
        .order_by(CoachingSnapshot.generated_at.desc())
        .limit(25)
    )
    for snap in (await db.scalars(stmt)).all():
        if (snap.content or {}).get("request") == request:
            return snap
    return None


async def sessions_logged_since(
    db: AsyncSession, user_id: UUID, since: datetime, exercise_id: UUID | None = None
) -> int:
    if exercise_id is None:
        stmt = (
            select(func.count())
            .select_from(WorkoutSession)
            .where(WorkoutSession.user_id == user_id, WorkoutSession.started_at > since)
        )
    else:
        stmt = (
            select(func.count(func.distinct(WorkoutSet.session_id)))
            .select_from(WorkoutSet)
            .join(WorkoutSession, WorkoutSet.session_id == WorkoutSession.id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.started_at > since,
                WorkoutSet.exercise_id == exercise_id,
            )
        )
    return (await db.scalar(stmt)) or 0


async def is_fresh(
    db: AsyncSession,
    snap: CoachingSnapshot | None,
    user_id: UUID,
    exercise_id: UUID | None = None,
    new_session_threshold: int = 1,
) -> bool:
    if snap is None:
        return False
    generated = ensure_utc(snap.generated_at)
    max_age = timedelta(hours=get_settings().coaching_cache_hours)
    if datetime.now(timezone.utc) - generated > max_age:
        return False
    new_count = await sessions_logged_since(db, user_id, snap.generated_at, exercise_id)
    return new_count < new_session_threshold


def save_snapshot(
    db: AsyncSession,
    user_id: UUID,
    snapshot_type: str,
    data: dict,
    request: dict,
    based_on: list[str],
) -> CoachingSnapshot:
    snap = CoachingSnapshot(
        user_id=user_id,
        snapshot_type=snapshot_type,
        content={"data": data, "request": request},
        based_on_sessions=based_on,
    )
    db.add(snap)
    return snap
