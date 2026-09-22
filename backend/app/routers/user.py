from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import UserOut, UserUpdate
from ..security import hash_password

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.name is not None:
        user.name = payload.name
    if payload.calorie_goal is not None:
        user.calorie_goal = payload.calorie_goal
    if payload.water_goal_ml is not None:
        user.water_goal_ml = payload.water_goal_ml
    if payload.exercise_goal_days is not None:
        user.exercise_goal_days = payload.exercise_goal_days
    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)

    await db.commit()
    await db.refresh(user)
    return user
