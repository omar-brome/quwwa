from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import DEFAULT_USER_ID, MUSCLE_GROUPS
from app.database import get_db
from app.models import Exercise, WorkoutSession, WorkoutSet
from app.schemas import ExerciseCreate, ExerciseHistoryOut, ExerciseOut
from app.services.coaching_data import ensure_utc, exercise_session_history

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("", response_model=list[ExerciseOut])
async def list_exercises(
    q: str | None = None,
    muscle: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Exercise library, sorted by most-recently-used first (then name).

    Includes each exercise's last logged working weight/reps so the logger
    can pre-populate inputs.
    """
    stmt = select(Exercise)
    if q:
        stmt = stmt.where(func.lower(Exercise.name).contains(q.lower()))
    exercises = list((await db.scalars(stmt)).all())
    if muscle:
        exercises = [e for e in exercises if muscle in (e.muscle_groups or [])]

    # Most recent non-warmup set per exercise for this user.
    last_sets_stmt = (
        select(WorkoutSet)
        .join(WorkoutSession, WorkoutSet.session_id == WorkoutSession.id)
        .where(WorkoutSession.user_id == DEFAULT_USER_ID, WorkoutSet.is_warmup.is_(False))
        .order_by(WorkoutSet.logged_at.desc())
        .limit(2000)
    )
    last_by_exercise: dict[UUID, WorkoutSet] = {}
    for s in (await db.scalars(last_sets_stmt)).all():
        if s.exercise_id not in last_by_exercise:
            last_by_exercise[s.exercise_id] = s

    out = []
    for e in exercises:
        item = ExerciseOut.model_validate(e)
        last = last_by_exercise.get(e.id)
        if last is not None:
            item.last_used_at = ensure_utc(last.logged_at)
            item.last_weight_kg = float(last.weight_kg) if last.weight_kg is not None else None
            item.last_reps = last.reps
        out.append(item)
    out.sort(
        key=lambda x: (
            x.last_used_at.timestamp() if x.last_used_at else 0,
            x.name,
        ),
        reverse=True,
    )
    return out


@router.post("", response_model=ExerciseOut, status_code=201)
async def create_exercise(body: ExerciseCreate, db: AsyncSession = Depends(get_db)):
    invalid = [m for m in body.muscle_groups if m not in MUSCLE_GROUPS]
    if invalid:
        raise HTTPException(422, f"Unknown muscle groups: {invalid}. Valid: {MUSCLE_GROUPS}")
    existing = await db.scalar(
        select(Exercise).where(func.lower(Exercise.name) == body.name.strip().lower())
    )
    if existing:
        raise HTTPException(409, f"Exercise '{existing.name}' already exists")
    exercise = Exercise(
        name=body.name.strip(),
        muscle_groups=body.muscle_groups,
        category=body.category,
        equipment=body.equipment,
        is_custom=True,
        created_by=DEFAULT_USER_ID,
    )
    db.add(exercise)
    await db.commit()
    await db.refresh(exercise)
    return exercise


@router.get("/{exercise_id}", response_model=ExerciseOut)
async def get_exercise(exercise_id: UUID, db: AsyncSession = Depends(get_db)):
    exercise = await db.get(Exercise, exercise_id)
    if exercise is None:
        raise HTTPException(404, "Exercise not found")
    return exercise


@router.get("/{exercise_id}/history", response_model=ExerciseHistoryOut)
async def get_exercise_history(
    exercise_id: UUID,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    exercise = await db.get(Exercise, exercise_id)
    if exercise is None:
        raise HTTPException(404, "Exercise not found")
    sessions = await exercise_session_history(
        db, DEFAULT_USER_ID, exercise_id, limit=min(limit, 50)
    )
    return {"exercise": exercise, "sessions": sessions}
