"""CSV import: seed the app with existing lift history.

Format (header required, extra columns ignored):
    date,exercise,weight_kg,reps[,rpe][,is_warmup][,notes]

One session is created per distinct date. Unknown exercises are created as
custom entries (without muscle groups — edit them for accurate volume stats).
"""

import csv
import io
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import DEFAULT_USER_ID
from app.database import get_db
from app.models import Exercise, WorkoutSession, WorkoutSet
from app.schemas import ImportResult

router = APIRouter(prefix="/import", tags=["import"])

MAX_BYTES = 2 * 1024 * 1024
DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y"]
REQUIRED = {"date", "exercise", "weight_kg", "reps"}


def _parse_date(raw: str) -> datetime | None:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).replace(
                hour=12, tzinfo=timezone.utc
            )
        except ValueError:
            continue
    return None


def _parse_bool(raw: str | None) -> bool:
    return (raw or "").strip().lower() in {"1", "true", "yes", "y"}


@router.post("/csv", response_model=ImportResult)
async def import_csv(file: UploadFile, db: AsyncSession = Depends(get_db)):
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "CSV too large (2 MB max)")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(422, "File must be UTF-8 encoded CSV")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise HTTPException(422, "CSV has no header row")
    fields = {f.strip().lower(): f for f in reader.fieldnames}
    missing = REQUIRED - set(fields)
    if missing:
        raise HTTPException(
            422, f"Missing required columns: {sorted(missing)}. Required: {sorted(REQUIRED)}"
        )

    def col(row: dict, name: str) -> str | None:
        original = fields.get(name)
        return row.get(original) if original else None

    exercises = {
        e.name.lower(): e for e in (await db.scalars(select(Exercise))).all()
    }
    warnings: list[str] = []
    created_exercises: list[str] = []
    sessions: dict[str, WorkoutSession] = {}
    set_counters: dict[tuple[str, str], int] = {}
    sets_created = 0

    for line_no, row in enumerate(reader, start=2):
        date_raw = (col(row, "date") or "").strip()
        name_raw = (col(row, "exercise") or "").strip()
        if not date_raw and not name_raw:
            continue
        when = _parse_date(date_raw)
        if when is None:
            warnings.append(f"Line {line_no}: unparseable date '{date_raw}' — skipped")
            continue
        if not name_raw:
            warnings.append(f"Line {line_no}: missing exercise name — skipped")
            continue
        try:
            weight = float((col(row, "weight_kg") or "0").strip() or 0)
            reps = int(float((col(row, "reps") or "0").strip() or 0))
        except ValueError:
            warnings.append(f"Line {line_no}: bad weight/reps — skipped")
            continue
        rpe_raw = (col(row, "rpe") or "").strip()
        rpe = None
        if rpe_raw:
            try:
                rpe = max(1, min(10, int(float(rpe_raw))))
            except ValueError:
                warnings.append(f"Line {line_no}: bad RPE '{rpe_raw}' — ignored")

        exercise = exercises.get(name_raw.lower())
        if exercise is None:
            exercise = Exercise(
                name=name_raw,
                muscle_groups=[],
                is_custom=True,
                created_by=DEFAULT_USER_ID,
            )
            db.add(exercise)
            await db.flush()
            exercises[name_raw.lower()] = exercise
            created_exercises.append(name_raw)
            warnings.append(
                f"Created custom exercise '{name_raw}' with no muscle groups — "
                f"edit it so volume stats count it."
            )

        day_key = when.strftime("%Y-%m-%d")
        session = sessions.get(day_key)
        if session is None:
            session = WorkoutSession(
                user_id=DEFAULT_USER_ID,
                started_at=when,
                ended_at=when + timedelta(hours=1),
                notes="Imported from CSV",
            )
            db.add(session)
            await db.flush()
            sessions[day_key] = session

        counter_key = (day_key, name_raw.lower())
        set_counters[counter_key] = set_counters.get(counter_key, 0) + 1
        db.add(
            WorkoutSet(
                session_id=session.id,
                exercise_id=exercise.id,
                set_number=set_counters[counter_key],
                reps=reps or None,
                weight_kg=weight or None,
                rpe=rpe,
                is_warmup=_parse_bool(col(row, "is_warmup")),
                notes=(col(row, "notes") or "").strip() or None,
                logged_at=when,
            )
        )
        sets_created += 1

    await db.commit()
    return ImportResult(
        sessions_created=len(sessions),
        sets_created=sets_created,
        exercises_created=created_exercises,
        warnings=warnings[:50],
    )
