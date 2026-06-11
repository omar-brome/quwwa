from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import DEFAULT_USER_ID, EQUIPMENT_TYPES
from app.models import Exercise, UserProfile
from app.seed_data import EXERCISES


async def seed_exercises(db: AsyncSession) -> int:
    """Insert the exercise library if no seeded exercises exist. Idempotent."""
    count = await db.scalar(
        select(func.count()).select_from(Exercise).where(Exercise.is_custom.is_(False))
    )
    if count and count > 0:
        return 0
    for name, muscles, category, equipment in EXERCISES:
        db.add(
            Exercise(
                name=name,
                muscle_groups=muscles,
                category=category,
                equipment=equipment,
                is_custom=False,
            )
        )
    await db.commit()
    return len(EXERCISES)


async def ensure_default_profile(db: AsyncSession) -> UserProfile:
    profile = await db.get(UserProfile, DEFAULT_USER_ID)
    if profile is None:
        profile = UserProfile(
            user_id=DEFAULT_USER_ID,
            equipment=list(EQUIPMENT_TYPES),
        )
        db.add(profile)
        await db.commit()
    return profile
