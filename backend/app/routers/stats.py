from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import DEFAULT_USER_ID, WEEKLY_SET_TARGETS
from app.database import get_db
from app.schemas import WeeklyVolumeOut
from app.services.coaching_data import (
    ensure_utc,
    load_recent_sessions,
    muscle_volume,
    week_start,
)

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/weekly-volume", response_model=WeeklyVolumeOut)
async def weekly_volume(db: AsyncSession = Depends(get_db)):
    """Current week's working sets per muscle group vs. recommended ranges."""
    start = week_start(datetime.now(timezone.utc))
    end = start + timedelta(days=7)
    sessions = [
        s
        for s in await load_recent_sessions(db, DEFAULT_USER_ID, limit=60)
        if start <= ensure_utc(s.started_at) < end
    ]
    volume = muscle_volume(sessions)
    muscles = [
        {
            "muscle": m,
            "sets": volume.get(m, 0),
            "min_sets": WEEKLY_SET_TARGETS.get(m, (None, None))[0],
            "max_sets": WEEKLY_SET_TARGETS.get(m, (None, None))[1],
        }
        for m in WEEKLY_SET_TARGETS
    ]
    # Include untargeted muscles (e.g. forearms) only if trained this week.
    for m, sets in volume.items():
        if m not in WEEKLY_SET_TARGETS:
            muscles.append({"muscle": m, "sets": sets, "min_sets": None, "max_sets": None})
    return {"week_start": start, "muscles": muscles}
