from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import DrinkEntry, User
from ..schemas import DrinkEntryCreate, DrinkEntryOut, DrinkEntryUpdate

router = APIRouter(prefix="/api/drinks", tags=["drinks"])


@router.get("", response_model=List[DrinkEntryOut])
async def list_drinks(
    date: Optional[date] = Query(None),
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(DrinkEntry).where(DrinkEntry.user_id == user.id)
    if date:
        q = q.where(DrinkEntry.date == date)
    else:
        if start:
            q = q.where(DrinkEntry.date >= start)
        if end:
            q = q.where(DrinkEntry.date <= end)
    q = q.order_by(DrinkEntry.date.desc(), DrinkEntry.time.asc())
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=DrinkEntryOut, status_code=status.HTTP_201_CREATED)
async def add_drink(
    payload: DrinkEntryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = DrinkEntry(
        user_id=user.id,
        date=payload.date or date.today(),
        time=payload.time,
        name=payload.name,
        amount_ml=payload.amount_ml,
        emoji=payload.emoji,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.patch("/{drink_id}", response_model=DrinkEntryOut)
async def update_drink(
    drink_id: int,
    payload: DrinkEntryUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await db.get(DrinkEntry, drink_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Drink not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(entry, field, value)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{drink_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_drink(
    drink_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await db.get(DrinkEntry, drink_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Drink not found")
    await db.delete(entry)
    await db.commit()
