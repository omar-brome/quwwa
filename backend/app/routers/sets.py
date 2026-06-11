from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import DEFAULT_USER_ID
from app.database import get_db
from app.models import WorkoutSet
from app.routers.sessions import _set_out
from app.schemas import SetOut, SetPatch

router = APIRouter(prefix="/sets", tags=["sets"])


async def _get_owned_set(db: AsyncSession, set_id: UUID) -> WorkoutSet:
    workout_set = await db.get(WorkoutSet, set_id)
    if workout_set is None or workout_set.session.user_id != DEFAULT_USER_ID:
        raise HTTPException(404, "Set not found")
    return workout_set


@router.patch("/{set_id}", response_model=SetOut)
async def update_set(set_id: UUID, body: SetPatch, db: AsyncSession = Depends(get_db)):
    workout_set = await _get_owned_set(db, set_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(workout_set, field, value)
    await db.commit()
    await db.refresh(workout_set)
    return _set_out(workout_set)


@router.delete("/{set_id}", status_code=204)
async def delete_set(set_id: UUID, db: AsyncSession = Depends(get_db)):
    workout_set = await _get_owned_set(db, set_id)
    await db.delete(workout_set)
    await db.commit()
