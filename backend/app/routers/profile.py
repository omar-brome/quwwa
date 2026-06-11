from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import EQUIPMENT_TYPES
from app.database import get_db
from app.schemas import ProfileOut, ProfileUpdate
from app.seed import ensure_default_profile

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
async def get_profile(db: AsyncSession = Depends(get_db)):
    return await ensure_default_profile(db)


@router.put("", response_model=ProfileOut)
async def update_profile(body: ProfileUpdate, db: AsyncSession = Depends(get_db)):
    invalid = [e for e in body.equipment if e not in EQUIPMENT_TYPES]
    if invalid:
        raise HTTPException(422, f"Unknown equipment: {invalid}. Valid: {EQUIPMENT_TYPES}")
    profile = await ensure_default_profile(db)
    profile.training_goal = body.training_goal
    profile.experience = body.experience
    profile.training_days = body.training_days
    profile.equipment = body.equipment
    profile.injury_notes = body.injury_notes
    profile.units = body.units
    await db.commit()
    await db.refresh(profile)
    return profile
