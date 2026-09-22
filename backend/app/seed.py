from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .models import User
from .security import hash_password


async def seed_default_user(db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.email == settings.default_user_email))
    if result.scalar_one_or_none() is not None:
        return

    user = User(
        name=settings.default_user_name,
        email=settings.default_user_email,
        hashed_password=hash_password(settings.default_user_password),
        calorie_goal=2000,
        water_goal_ml=2500,
        exercise_goal_days=4,
    )
    db.add(user)
    await db.commit()
