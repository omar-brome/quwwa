from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import DEFAULT_USER_ID
from app.database import get_db
from app.models import Exercise, WorkoutSession, WorkoutSet
from app.schemas import (
    SessionCreate,
    SessionDetail,
    SessionListOut,
    SessionPatch,
    SessionSummary,
    SetCreate,
    SetOut,
)
from app.services.coaching_data import ensure_utc

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _set_out(s: WorkoutSet) -> SetOut:
    return SetOut(
        id=s.id,
        session_id=s.session_id,
        exercise_id=s.exercise_id,
        exercise_name=s.exercise.name,
        muscle_groups=list(s.exercise.muscle_groups or []),
        set_number=s.set_number,
        reps=s.reps,
        weight_kg=float(s.weight_kg) if s.weight_kg is not None else None,
        rpe=s.rpe,
        is_warmup=s.is_warmup,
        notes=s.notes,
        logged_at=ensure_utc(s.logged_at),
    )


def _summary(session: WorkoutSession) -> dict:
    working = [s for s in session.sets if not s.is_warmup]
    volume = sum(float(s.weight_kg or 0) * (s.reps or 0) for s in working)
    names: list[str] = []
    muscles: set[str] = set()
    for s in session.sets:
        if s.exercise.name not in names:
            names.append(s.exercise.name)
        muscles.update(s.exercise.muscle_groups or [])
    return {
        "id": session.id,
        "started_at": ensure_utc(session.started_at),
        "ended_at": ensure_utc(session.ended_at),
        "rpe": session.rpe,
        "notes": session.notes,
        "bodyweight_kg": float(session.bodyweight_kg) if session.bodyweight_kg else None,
        "total_sets": len(session.sets),
        "working_sets": len(working),
        "total_volume_kg": round(volume, 1),
        "exercise_names": names,
        "muscle_groups": sorted(muscles),
    }


@router.post("", response_model=SessionSummary, status_code=201)
async def start_session(body: SessionCreate, db: AsyncSession = Depends(get_db)):
    session = WorkoutSession(
        user_id=DEFAULT_USER_ID,
        started_at=body.started_at or datetime.now(timezone.utc),
        bodyweight_kg=body.bodyweight_kg,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return _summary(session)


@router.get("", response_model=SessionListOut)
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    base = select(WorkoutSession).where(WorkoutSession.user_id == DEFAULT_USER_ID)
    total = await db.scalar(
        select(func.count()).select_from(WorkoutSession).where(
            WorkoutSession.user_id == DEFAULT_USER_ID
        )
    )
    stmt = base.order_by(WorkoutSession.started_at.desc()).offset(offset).limit(min(limit, 100))
    sessions = (await db.scalars(stmt)).all()
    return {"items": [_summary(s) for s in sessions], "total": total or 0}


async def _get_owned_session(db: AsyncSession, session_id: UUID) -> WorkoutSession:
    session = await db.get(WorkoutSession, session_id)
    if session is None or session.user_id != DEFAULT_USER_ID:
        raise HTTPException(404, "Session not found")
    return session


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    session = await _get_owned_session(db, session_id)
    volume_by_muscle: dict[str, int] = {}
    for s in session.sets:
        if s.is_warmup:
            continue
        for m in s.exercise.muscle_groups or []:
            volume_by_muscle[m] = volume_by_muscle.get(m, 0) + 1
    return {
        **_summary(session),
        "sets": [_set_out(s) for s in session.sets],
        "volume_by_muscle": volume_by_muscle,
    }


@router.patch("/{session_id}", response_model=SessionSummary)
async def update_session(
    session_id: UUID, body: SessionPatch, db: AsyncSession = Depends(get_db)
):
    session = await _get_owned_session(db, session_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(session, field, value)
    await db.commit()
    await db.refresh(session)
    return _summary(session)


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    session = await _get_owned_session(db, session_id)
    await db.delete(session)
    await db.commit()


@router.post("/{session_id}/sets", response_model=SetOut, status_code=201)
async def log_set(session_id: UUID, body: SetCreate, db: AsyncSession = Depends(get_db)):
    session = await _get_owned_session(db, session_id)
    exercise = await db.get(Exercise, body.exercise_id)
    if exercise is None:
        raise HTTPException(404, "Exercise not found")

    set_number = body.set_number
    if set_number is None:
        existing = [s for s in session.sets if s.exercise_id == body.exercise_id]
        set_number = len(existing) + 1

    workout_set = WorkoutSet(
        session_id=session.id,
        exercise=exercise,
        set_number=set_number,
        reps=body.reps,
        weight_kg=body.weight_kg,
        rpe=body.rpe,
        is_warmup=body.is_warmup,
        notes=body.notes,
    )
    db.add(workout_set)
    await db.commit()
    return _set_out(workout_set)
