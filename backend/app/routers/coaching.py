"""AI coaching endpoints.

Each coaching kind has two routes:

- GET  /coaching/<kind>            → cached snapshot if fresh, else a "stale"
                                     envelope (with the last cached content when
                                     available) telling the client to generate.
- POST /coaching/<kind>/generate   → NDJSON stream: {"type":"delta"} lines while
                                     Claude streams, then {"type":"result"} with
                                     the validated JSON (also cached).

Caching: snapshots are reused for COACHING_CACHE_HOURS unless a new session is
logged (plateau checks tolerate up to 2 new sessions of that exercise — they
re-run after every 3rd, per spec).
"""

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.constants import (
    DEFAULT_USER_ID,
    MUSCLE_GROUPS,
    SNAPSHOT_DELOAD_CHECK,
    SNAPSHOT_NEXT_SESSION,
    SNAPSHOT_PLATEAU,
    SNAPSHOT_WEEKLY_REVIEW,
)
from app.database import get_db, session_factory
from app.models import CoachingSnapshot, Exercise
from app.schemas import DeloadAdvice, NextSessionPlan, PlateauReport, WeeklyReview
from app.seed import ensure_default_profile
from app.services import claude
from app.services.coaching_data import (
    deload_data,
    ensure_utc,
    estimated_1rms,
    exercise_session_history,
    infer_target_muscles,
    recent_sessions_for_muscles,
    week_start,
    weekly_review_data,
)
from app.services.prompts import (
    DELOAD_SCHEMA,
    NEXT_SESSION_SCHEMA,
    PLATEAU_SCHEMA,
    WEEKLY_REVIEW_SCHEMA,
    build_deload_prompt,
    build_next_session_prompt,
    build_plateau_prompt,
    build_weekly_review_prompt,
)
from app.services.snapshots import is_fresh, latest_snapshot, save_snapshot

router = APIRouter(prefix="/coaching", tags=["coaching"])

# Plateau snapshots re-generate after every 3rd new session of the exercise.
_FRESHNESS_THRESHOLD = {SNAPSHOT_PLATEAU: 3}


class CoachingContext:
    def __init__(
        self,
        snapshot_type: str,
        prompt: str,
        schema: dict,
        model_cls: type[BaseModel],
        request: dict,
        based_on: list[str],
        exercise_id: UUID | None = None,
    ):
        self.snapshot_type = snapshot_type
        self.prompt = prompt
        self.schema = schema
        self.model_cls = model_cls
        self.request = request
        self.based_on = based_on
        self.exercise_id = exercise_id


# ---------------------------------------------------------------------------
# Context builders (resolve request params + assemble the prompt)


async def _next_session_context(
    db: AsyncSession, muscles: str | None
) -> CoachingContext:
    profile = await ensure_default_profile(db)
    if muscles:
        target = [m.strip() for m in muscles.split(",") if m.strip() in MUSCLE_GROUPS]
        if not target:
            raise HTTPException(422, f"No valid muscle groups in '{muscles}'")
    else:
        target = await infer_target_muscles(db, DEFAULT_USER_ID)
    recent = await recent_sessions_for_muscles(db, DEFAULT_USER_ID, target, n=4)
    prompt = build_next_session_prompt(profile, target, recent, estimated_1rms(recent))
    return CoachingContext(
        SNAPSHOT_NEXT_SESSION,
        prompt,
        NEXT_SESSION_SCHEMA,
        NextSessionPlan,
        request={"muscles": sorted(target)},
        based_on=[s["id"] for s in recent],
    )


async def _weekly_review_context(db: AsyncSession) -> CoachingContext | dict:
    profile = await ensure_default_profile(db)
    data = await weekly_review_data(db, DEFAULT_USER_ID, datetime.now(timezone.utc))
    if data["session_count"] == 0:
        return {"status": "empty", "detail": "No sessions logged this week yet."}
    return CoachingContext(
        SNAPSHOT_WEEKLY_REVIEW,
        build_weekly_review_prompt(profile, data),
        WEEKLY_REVIEW_SCHEMA,
        WeeklyReview,
        request={"week_start": data["week_start"].strftime("%Y-%m-%d")},
        based_on=data["session_ids"],
    )


async def _deload_context(db: AsyncSession) -> CoachingContext | dict:
    profile = await ensure_default_profile(db)
    data = await deload_data(db, DEFAULT_USER_ID, datetime.now(timezone.utc))
    if data["total_sessions"] < 4:
        return {
            "status": "insufficient_data",
            "detail": "Need at least 4 sessions across the last 3 weeks to assess fatigue.",
        }
    return CoachingContext(
        SNAPSHOT_DELOAD_CHECK,
        build_deload_prompt(profile, data),
        DELOAD_SCHEMA,
        DeloadAdvice,
        request={
            "week_start": week_start(datetime.now(timezone.utc)).strftime("%Y-%m-%d")
        },
        based_on=data["session_ids"],
    )


async def _plateau_context(db: AsyncSession, exercise_id: UUID) -> CoachingContext | dict:
    profile = await ensure_default_profile(db)
    exercise = await db.get(Exercise, exercise_id)
    if exercise is None:
        raise HTTPException(404, "Exercise not found")
    history = await exercise_session_history(db, DEFAULT_USER_ID, exercise_id, limit=8)
    if len(history) < 4:
        return {
            "status": "insufficient_data",
            "detail": f"Need at least 4 logged sessions of {exercise.name} "
            f"(have {len(history)}).",
        }
    history = list(reversed(history))  # oldest → newest for the prompt
    sessions = [
        {
            "date": h["date"].strftime("%Y-%m-%d"),
            "sets": h["sets"],
            "best_e1rm": h["best_e1rm"],
        }
        for h in history
    ]
    return CoachingContext(
        SNAPSHOT_PLATEAU,
        build_plateau_prompt(profile, exercise.name, sessions),
        PLATEAU_SCHEMA,
        PlateauReport,
        request={"exercise_id": str(exercise_id)},
        based_on=[str(h["session_id"]) for h in history],
        exercise_id=exercise_id,
    )


# ---------------------------------------------------------------------------
# Shared GET / generate plumbing


def _snapshot_payload(snap: CoachingSnapshot) -> tuple[Any, str]:
    return (snap.content or {}).get("data"), ensure_utc(snap.generated_at).isoformat()


async def _cached_or_stale(db: AsyncSession, ctx: CoachingContext | dict) -> dict:
    if isinstance(ctx, dict):  # short-circuit: empty / insufficient_data
        return ctx
    snap = await latest_snapshot(db, DEFAULT_USER_ID, ctx.snapshot_type, ctx.request)
    threshold = _FRESHNESS_THRESHOLD.get(ctx.snapshot_type, 1)
    if await is_fresh(db, snap, DEFAULT_USER_ID, ctx.exercise_id, threshold):
        content, generated_at = _snapshot_payload(snap)
        return {
            "status": "fresh",
            "request": ctx.request,
            "content": content,
            "generated_at": generated_at,
        }
    out: dict = {"status": "stale", "request": ctx.request}
    if not get_settings().anthropic_api_key:
        out["status"] = "no_api_key"
    if snap is not None:
        out["cached_content"], out["cached_generated_at"] = _snapshot_payload(snap)
    return out


def _ndjson(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False) + "\n"


def _generate_stream(ctx: CoachingContext) -> StreamingResponse:
    async def gen():
        try:
            result: dict | None = None
            async for event in claude.stream_structured(ctx.prompt, ctx.schema):
                if event["type"] == "delta":
                    yield _ndjson(event)
                elif event["type"] == "result":
                    result = event["content"]
            validated = ctx.model_cls.model_validate(result).model_dump(mode="json")
            # Fresh DB session: the request-scoped one may be torn down while
            # this response is still streaming.
            async with session_factory() as db:
                snap = save_snapshot(
                    db,
                    DEFAULT_USER_ID,
                    ctx.snapshot_type,
                    validated,
                    ctx.request,
                    ctx.based_on,
                )
                await db.commit()
                generated_at = ensure_utc(snap.generated_at).isoformat()
            yield _ndjson(
                {
                    "type": "result",
                    "content": validated,
                    "generated_at": generated_at,
                    "request": ctx.request,
                }
            )
        except (claude.CoachingError, ValidationError) as exc:
            yield _ndjson({"type": "error", "detail": str(exc)})

    return StreamingResponse(gen(), media_type="application/x-ndjson")


def _require_api_key() -> None:
    if not get_settings().anthropic_api_key:
        raise HTTPException(
            503,
            "ANTHROPIC_API_KEY is not configured. Add it to backend/.env "
            "(or the compose .env) to enable AI coaching.",
        )


def _require_context(ctx: CoachingContext | dict) -> CoachingContext:
    if isinstance(ctx, dict):
        raise HTTPException(409, ctx.get("detail", "Not enough data to generate this yet"))
    return ctx


# ---------------------------------------------------------------------------
# Routes


@router.get("/next-session")
async def get_next_session(muscles: str | None = None, db: AsyncSession = Depends(get_db)):
    return await _cached_or_stale(db, await _next_session_context(db, muscles))


@router.post("/next-session/generate")
async def generate_next_session(
    muscles: str | None = None, db: AsyncSession = Depends(get_db)
):
    _require_api_key()
    ctx = _require_context(await _next_session_context(db, muscles))
    return _generate_stream(ctx)


@router.get("/weekly-review")
async def get_weekly_review(db: AsyncSession = Depends(get_db)):
    return await _cached_or_stale(db, await _weekly_review_context(db))


@router.post("/weekly-review/generate")
async def generate_weekly_review(db: AsyncSession = Depends(get_db)):
    _require_api_key()
    ctx = _require_context(await _weekly_review_context(db))
    return _generate_stream(ctx)


@router.get("/deload-check")
async def get_deload_check(db: AsyncSession = Depends(get_db)):
    return await _cached_or_stale(db, await _deload_context(db))


@router.post("/deload-check/generate")
async def generate_deload_check(db: AsyncSession = Depends(get_db)):
    _require_api_key()
    ctx = _require_context(await _deload_context(db))
    return _generate_stream(ctx)


@router.get("/plateau-alerts")
async def plateau_alerts(db: AsyncSession = Depends(get_db)):
    """Exercises whose latest plateau snapshot is not 'progressing'."""
    from sqlalchemy import select

    stmt = (
        select(CoachingSnapshot)
        .where(
            CoachingSnapshot.user_id == DEFAULT_USER_ID,
            CoachingSnapshot.snapshot_type == SNAPSHOT_PLATEAU,
        )
        .order_by(CoachingSnapshot.generated_at.desc())
        .limit(100)
    )
    latest_by_exercise: dict[str, CoachingSnapshot] = {}
    for snap in (await db.scalars(stmt)).all():
        ex_id = (snap.content or {}).get("request", {}).get("exercise_id")
        if ex_id and ex_id not in latest_by_exercise:
            latest_by_exercise[ex_id] = snap

    alerts = []
    for ex_id, snap in latest_by_exercise.items():
        data = (snap.content or {}).get("data", {})
        if data.get("status") in ("plateaued", "regressing", "fatigued"):
            exercise = await db.get(Exercise, UUID(ex_id))
            alerts.append(
                {
                    "exercise_id": ex_id,
                    "exercise_name": exercise.name if exercise else "Unknown",
                    "status": data["status"],
                    "urgency": data.get("urgency", "low"),
                    "generated_at": ensure_utc(snap.generated_at).isoformat(),
                }
            )
    return {"alerts": alerts}


@router.get("/plateau/{exercise_id}")
async def get_plateau(exercise_id: UUID, db: AsyncSession = Depends(get_db)):
    return await _cached_or_stale(db, await _plateau_context(db, exercise_id))


@router.post("/plateau/{exercise_id}/generate")
async def generate_plateau(exercise_id: UUID, db: AsyncSession = Depends(get_db)):
    _require_api_key()
    ctx = _require_context(await _plateau_context(db, exercise_id))
    return _generate_stream(ctx)
