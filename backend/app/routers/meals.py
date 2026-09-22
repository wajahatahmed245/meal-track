from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import MealEntry, User
from ..schemas import MealEntryCreate, MealEntryOut, MealEntryUpdate

router = APIRouter(prefix="/api/meals", tags=["meals"])


@router.get("", response_model=List[MealEntryOut])
async def list_meals(
    date: Optional[date] = Query(None),
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(MealEntry).where(MealEntry.user_id == user.id)
    if date:
        q = q.where(MealEntry.date == date)
    else:
        if start:
            q = q.where(MealEntry.date >= start)
        if end:
            q = q.where(MealEntry.date <= end)
    q = q.order_by(MealEntry.date.desc(), MealEntry.time.asc())
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=MealEntryOut, status_code=status.HTTP_201_CREATED)
async def add_meal(
    payload: MealEntryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = MealEntry(
        user_id=user.id,
        date=payload.date or date.today(),
        time=payload.time,
        meal_type=payload.meal_type,
        name=payload.name,
        calories=payload.calories,
        emoji=payload.emoji,
        note=payload.note,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.patch("/{meal_id}", response_model=MealEntryOut)
async def update_meal(
    meal_id: int,
    payload: MealEntryUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await db.get(MealEntry, meal_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Meal not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(entry, field, value)

    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal(
    meal_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await db.get(MealEntry, meal_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Meal not found")
    await db.delete(entry)
    await db.commit()
