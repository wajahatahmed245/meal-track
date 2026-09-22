from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import ExerciseLog, User
from ..schemas import ExerciseLogCreate, ExerciseLogOut, ExerciseLogUpdate

router = APIRouter(prefix="/api/exercise", tags=["exercise"])


@router.get("", response_model=List[ExerciseLogOut])
async def list_exercise(
    date: Optional[date] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(ExerciseLog).where(ExerciseLog.user_id == user.id)
    if date:
        q = q.where(ExerciseLog.date == date)
    q = q.order_by(ExerciseLog.date.desc())
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=ExerciseLogOut, status_code=status.HTTP_201_CREATED)
async def log_exercise(
    payload: ExerciseLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = ExerciseLog(
        user_id=user.id,
        date=payload.date or date.today(),
        exercise_type=payload.exercise_type,
        duration_minutes=payload.duration_minutes,
        calories_burned=payload.calories_burned,
        time=payload.time,
        completed=payload.completed,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.patch("/{exercise_id}", response_model=ExerciseLogOut)
async def update_exercise(
    exercise_id: int,
    payload: ExerciseLogUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await db.get(ExerciseLog, exercise_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Exercise log not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(entry, field, value)

    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise(
    exercise_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await db.get(ExerciseLog, exercise_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Exercise log not found")
    await db.delete(entry)
    await db.commit()
