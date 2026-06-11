"""Builds the data each coaching prompt needs from logged history."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import MUSCLE_GROUPS, WEEKLY_SET_TARGETS
from app.models import WorkoutSession, WorkoutSet
from app.services.e1rm import best_e1rm, epley_1rm


def ensure_utc(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; normalize everything to aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def week_start(dt: datetime) -> datetime:
    dt = ensure_utc(dt)
    monday = dt - timedelta(days=dt.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def session_effort(session: WorkoutSession) -> int | None:
    """Session RPE, falling back to the hardest set when not rated."""
    if session.rpe is not None:
        return session.rpe
    set_rpes = [s.rpe for s in session.sets if s.rpe is not None]
    return max(set_rpes) if set_rpes else None


def _set_dict(s: WorkoutSet) -> dict:
    return {
        "exercise_name": s.exercise.name,
        "muscle_groups": list(s.exercise.muscle_groups or []),
        "weight_kg": float(s.weight_kg) if s.weight_kg is not None else None,
        "reps": s.reps,
        "rpe": s.rpe,
        "is_warmup": s.is_warmup,
    }


async def load_recent_sessions(
    db: AsyncSession, user_id: UUID, limit: int = 40
) -> list[WorkoutSession]:
    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == user_id)
        .order_by(WorkoutSession.started_at.desc())
        .limit(limit)
    )
    return list((await db.scalars(stmt)).all())


def session_payload(session: WorkoutSession, muscles: list[str] | None = None) -> dict:
    """Session as prompt-ready dict; optionally only sets hitting given muscles."""
    sets = []
    for s in session.sets:
        d = _set_dict(s)
        if muscles is None or set(d["muscle_groups"]) & set(muscles):
            sets.append(d)
    return {
        "id": str(session.id),
        "date": ensure_utc(session.started_at).strftime("%Y-%m-%d"),
        "session_rpe": session.rpe,
        "sets": sets,
    }


async def recent_sessions_for_muscles(
    db: AsyncSession, user_id: UUID, muscles: list[str], n: int = 4
) -> list[dict]:
    """Last n sessions that trained any of the target muscles (newest first),
    with only the relevant sets included."""
    out: list[dict] = []
    for session in await load_recent_sessions(db, user_id):
        payload = session_payload(session, muscles)
        if payload["sets"]:
            out.append(payload)
        if len(out) >= n:
            break
    return out


def estimated_1rms(session_payloads: list[dict]) -> list[dict]:
    """Best Epley e1RM per exercise across the given session payloads."""
    best: dict[str, float] = {}
    for sp in session_payloads:
        for s in sp["sets"]:
            if s["is_warmup"] or not s["weight_kg"] or not s["reps"]:
                continue
            v = epley_1rm(s["weight_kg"], s["reps"])
            if v > best.get(s["exercise_name"], 0):
                best[s["exercise_name"]] = v
    return [{"exercise_name": k, "e1rm_kg": v} for k, v in sorted(best.items())]


async def infer_target_muscles(db: AsyncSession, user_id: UUID) -> list[str]:
    """Default target for 'what should I do today': the three least-recently
    trained muscle groups. Falls back to a push split for brand-new users."""
    last_trained: dict[str, datetime] = {}
    for session in await load_recent_sessions(db, user_id):
        when = ensure_utc(session.started_at)
        for s in session.sets:
            for m in s.exercise.muscle_groups or []:
                if m not in last_trained or when > last_trained[m]:
                    last_trained[m] = when
    if not last_trained:
        return ["chest", "shoulders", "triceps"]
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    ranked = sorted(MUSCLE_GROUPS, key=lambda m: last_trained.get(m, epoch))
    return ranked[:3]


async def exercise_session_history(
    db: AsyncSession, user_id: UUID, exercise_id: UUID, limit: int = 10
) -> list[dict]:
    """Per-session history for one exercise (newest first): sets + best e1RM."""
    stmt = (
        select(WorkoutSet)
        .join(WorkoutSession, WorkoutSet.session_id == WorkoutSession.id)
        .where(WorkoutSession.user_id == user_id, WorkoutSet.exercise_id == exercise_id)
        .order_by(WorkoutSession.started_at.desc(), WorkoutSet.logged_at)
    )
    sets = list((await db.scalars(stmt)).all())
    by_session: dict[UUID, dict] = {}
    for s in sets:
        entry = by_session.setdefault(
            s.session_id,
            {
                "session_id": s.session_id,
                "date": ensure_utc(s.session.started_at),
                "sets": [],
            },
        )
        entry["sets"].append(
            {
                "set_number": s.set_number,
                "reps": s.reps,
                "weight_kg": float(s.weight_kg) if s.weight_kg is not None else None,
                "rpe": s.rpe,
                "is_warmup": s.is_warmup,
            }
        )
        if len(by_session) > limit:
            break
    sessions = list(by_session.values())[:limit]
    for entry in sessions:
        entry["best_e1rm"] = best_e1rm(entry["sets"])
    return sessions


def muscle_volume(sessions: list[WorkoutSession]) -> dict[str, int]:
    """Working sets per muscle group. A set counts toward every muscle group
    of its exercise."""
    volume: dict[str, int] = {}
    for session in sessions:
        for s in session.sets:
            if s.is_warmup:
                continue
            for m in s.exercise.muscle_groups or []:
                volume[m] = volume.get(m, 0) + 1
    return volume


async def weekly_review_data(db: AsyncSession, user_id: UUID, now: datetime) -> dict:
    """Everything the weekly review prompt needs for the week containing `now`."""
    start = week_start(now)
    end = start + timedelta(days=7)
    sessions = [
        s
        for s in await load_recent_sessions(db, user_id, limit=60)
        if start <= ensure_utc(s.started_at) < end
    ]
    volume = muscle_volume(sessions)
    efforts = [e for e in (session_effort(s) for s in sessions) if e is not None]

    # PRs: best e1RM this week vs best before this week, per exercise.
    week_best: dict[str, dict] = {}
    for session in sessions:
        for s in session.sets:
            if s.is_warmup or not s.weight_kg or not s.reps:
                continue
            v = epley_1rm(float(s.weight_kg), s.reps)
            cur = week_best.get(s.exercise.name)
            if cur is None or v > cur["e1rm"]:
                week_best[s.exercise.name] = {
                    "e1rm": v,
                    "weight_kg": float(s.weight_kg),
                    "reps": s.reps,
                }
    prior_best: dict[str, float] = {}
    for session in await load_recent_sessions(db, user_id, limit=200):
        if ensure_utc(session.started_at) >= start:
            continue
        for s in session.sets:
            if s.is_warmup or not s.weight_kg or not s.reps:
                continue
            v = epley_1rm(float(s.weight_kg), s.reps)
            if v > prior_best.get(s.exercise.name, 0):
                prior_best[s.exercise.name] = v
    prs = []
    for name, entry in week_best.items():
        prev = prior_best.get(name)
        if prev is None or entry["e1rm"] > prev:
            prs.append(
                {
                    "exercise_name": name,
                    "weight_kg": entry["weight_kg"],
                    "reps": entry["reps"],
                    "previous_best": f"~{prev}kg e1RM" if prev else "first time logged",
                }
            )

    return {
        "week_start": start,
        "week_end": end,
        "session_ids": [str(s.id) for s in sessions],
        "session_count": len(sessions),
        "total_sets": sum(len([x for x in s.sets if not x.is_warmup]) for s in sessions),
        "avg_rpe": round(sum(efforts) / len(efforts), 1) if efforts else None,
        "muscle_volumes": [
            {
                "muscle": m,
                "sets": volume.get(m, 0),
                "min_sets": WEEKLY_SET_TARGETS[m][0],
                "max_sets": WEEKLY_SET_TARGETS[m][1],
            }
            for m in WEEKLY_SET_TARGETS
            if volume.get(m, 0) > 0 or m in WEEKLY_SET_TARGETS
        ],
        "prs": prs,
    }


async def deload_data(db: AsyncSession, user_id: UUID, now: datetime) -> dict:
    """Last 3 ISO weeks of fatigue signals (oldest week first)."""
    this_week = week_start(now)
    weeks = []
    all_sessions = await load_recent_sessions(db, user_id, limit=120)
    bodyweights: list[float] = []
    for i in range(2, -1, -1):
        start = this_week - timedelta(days=7 * i)
        end = start + timedelta(days=7)
        sessions = [s for s in all_sessions if start <= ensure_utc(s.started_at) < end]
        efforts = [e for e in (session_effort(s) for s in sessions) if e is not None]
        weeks.append(
            {
                "week_number": 3 - i,
                "start": start,
                "session_ids": [str(s.id) for s in sessions],
                "session_count": len(sessions),
                "avg_rpe": round(sum(efforts) / len(efforts), 1) if efforts else None,
                "total_sets": sum(
                    len([x for x in s.sets if not x.is_warmup]) for s in sessions
                ),
                "high_rpe_count": len([e for e in efforts if e >= 9]),
            }
        )
        bodyweights.extend(
            float(s.bodyweight_kg) for s in sessions if s.bodyweight_kg is not None
        )

    rated = [w["avg_rpe"] for w in weeks if w["avg_rpe"] is not None]
    if len(rated) >= 2:
        delta = rated[-1] - rated[0]
        rpe_trend = "worsening" if delta > 0.4 else "improving" if delta < -0.4 else "stable"
    else:
        rpe_trend = "stable"

    if len(bodyweights) >= 2:
        bw_delta = bodyweights[-1] - bodyweights[0]
        bw_trend = (
            "declining" if bw_delta < -0.7 else "increasing" if bw_delta > 0.7 else "stable"
        )
    else:
        bw_trend = "not logged"

    return {
        "weeks": weeks,
        "rpe_trend": rpe_trend,
        "bw_trend": bw_trend,
        "session_ids": [sid for w in weeks for sid in w["session_ids"]],
        "total_sessions": sum(w["session_count"] for w in weeks),
    }
