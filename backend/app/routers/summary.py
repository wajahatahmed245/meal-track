from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import DrinkEntry, ExerciseLog, MealEntry, User
from ..schemas import (
    DailySummaryOut, DrinkEntryOut, ExerciseLogOut,
    MealEntryOut, RangeDayOut, StatsOut, WeeklyDayOut, WeeklySummaryOut,
)

router = APIRouter(prefix="/api/summary", tags=["summary"])

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


@router.get("/today", response_model=DailySummaryOut)
async def today_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _build_daily(db, user, date.today())


@router.get("/day", response_model=DailySummaryOut)
async def day_summary(
    day: date = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _build_daily(db, user, day)


@router.get("/weekly", response_model=WeeklySummaryOut)
async def weekly_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    days_out: List[WeeklyDayOut] = []

    for i in range(7):
        d = week_start + timedelta(days=i)
        meals_res = await db.execute(
            select(MealEntry).where(MealEntry.user_id == user.id, MealEntry.date == d)
        )
        meals = meals_res.scalars().all()
        total_cal = sum(m.calories for m in meals)
        ex_day_res = await db.execute(
            select(ExerciseLog).where(
                ExerciseLog.user_id == user.id,
                ExerciseLog.date == d,
                ExerciseLog.completed.is_(True),
            ).limit(1)
        )
        days_out.append(WeeklyDayOut(
            date=d,
            day=DAYS[i],
            calories=total_cal,
            is_today=(d == today),
            exercise_completed=ex_day_res.scalar_one_or_none() is not None,
        ))

    ex_res = await db.execute(
        select(ExerciseLog).where(
            ExerciseLog.user_id == user.id,
            ExerciseLog.date >= week_start,
            ExerciseLog.date <= today,
            ExerciseLog.completed.is_(True),
        )
    )
    exercise_days = len(set(e.date for e in ex_res.scalars().all()))

    logged_days = [d for d in days_out if d.calories > 0]
    avg_cal = sum(d.calories for d in logged_days) // len(logged_days) if logged_days else 0

    return WeeklySummaryOut(days=days_out, avg_calories=avg_cal, days_exercised=exercise_days)


@router.get("/range", response_model=List[RangeDayOut])
async def range_summary(
    start: date = Query(...),
    end: date = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if (end - start).days > 366:
        raise HTTPException(status_code=400, detail="Range cannot exceed 366 days")

    meals_res = await db.execute(
        select(MealEntry.date, func.sum(MealEntry.calories).label("cal"))
        .where(MealEntry.user_id == user.id, MealEntry.date >= start, MealEntry.date <= end)
        .group_by(MealEntry.date)
    )
    cal_by_date = {row.date: row.cal for row in meals_res.all()}

    drinks_res = await db.execute(
        select(DrinkEntry.date, func.sum(DrinkEntry.amount_ml).label("ml"))
        .where(DrinkEntry.user_id == user.id, DrinkEntry.date >= start, DrinkEntry.date <= end)
        .group_by(DrinkEntry.date)
    )
    water_by_date = {row.date: row.ml for row in drinks_res.all()}

    ex_res = await db.execute(
        select(ExerciseLog.date)
        .where(
            ExerciseLog.user_id == user.id,
            ExerciseLog.date >= start,
            ExerciseLog.date <= end,
            ExerciseLog.completed.is_(True),
        )
        .distinct()
    )
    ex_dates = {row.date for row in ex_res.all()}

    out = []
    delta = (end - start).days
    for i in range(delta + 1):
        d = start + timedelta(days=i)
        out.append(RangeDayOut(
            date=d,
            calories=cal_by_date.get(d, 0),
            water_ml=water_by_date.get(d, 0),
            exercise_completed=d in ex_dates,
        ))
    return out


@router.get("/stats", response_model=StatsOut)
async def stats_overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    start_30 = today - timedelta(days=29)

    # Days with at least one meal logged in last 30 days
    meals_res = await db.execute(
        select(MealEntry.date)
        .where(MealEntry.user_id == user.id, MealEntry.date >= start_30, MealEntry.date <= today)
        .distinct()
    )
    logged_dates = sorted({row.date for row in meals_res.all()})
    days_logged = len(logged_dates)

    # Exercise days in last 30 days
    ex_res = await db.execute(
        select(ExerciseLog.date)
        .where(
            ExerciseLog.user_id == user.id,
            ExerciseLog.date >= start_30,
            ExerciseLog.date <= today,
            ExerciseLog.completed.is_(True),
        )
        .distinct()
    )
    exercise_days = len({row.date for row in ex_res.all()})

    # Current streak (consecutive days ending today with meals logged)
    streak = 0
    check = today
    logged_set = set(logged_dates)
    while check in logged_set:
        streak += 1
        check = check - timedelta(days=1)

    # Average calories (30 days)
    cal_res = await db.execute(
        select(func.sum(MealEntry.calories))
        .where(MealEntry.user_id == user.id, MealEntry.date >= start_30, MealEntry.date <= today)
    )
    total_cal_30 = cal_res.scalar_one_or_none() or 0
    avg_cal = total_cal_30 // days_logged if days_logged else 0

    return StatsOut(
        days_logged=days_logged,
        exercise_days=exercise_days,
        current_streak=streak,
        avg_calories_30d=avg_cal,
    )


async def _build_daily(db: AsyncSession, user: User, day: date) -> DailySummaryOut:
    meals_res = await db.execute(
        select(MealEntry)
        .where(MealEntry.user_id == user.id, MealEntry.date == day)
        .order_by(MealEntry.time.asc())
    )
    meals = meals_res.scalars().all()

    drinks_res = await db.execute(
        select(DrinkEntry)
        .where(DrinkEntry.user_id == user.id, DrinkEntry.date == day)
        .order_by(DrinkEntry.time.asc())
    )
    drinks = drinks_res.scalars().all()

    ex_res = await db.execute(
        select(ExerciseLog)
        .where(ExerciseLog.user_id == user.id, ExerciseLog.date == day)
        .order_by(ExerciseLog.id.desc())
        .limit(1)
    )
    exercise = ex_res.scalar_one_or_none()

    total_cal = sum(m.calories for m in meals)
    total_water = sum(d.amount_ml for d in drinks)
    burned = (exercise.calories_burned or 0) if exercise and exercise.completed else 0
    meal_types_logged = len(set(m.meal_type for m in meals))

    return DailySummaryOut(
        date=day,
        total_calories=total_cal,
        total_water_ml=total_water,
        calories_burned=burned,
        net_calories=total_cal - burned,
        meals_logged=meal_types_logged,
        calorie_goal=user.calorie_goal,
        water_goal_ml=user.water_goal_ml,
        calorie_pct=min(round((total_cal / user.calorie_goal) * 100), 100) if user.calorie_goal else 0,
        water_pct=min(round((total_water / user.water_goal_ml) * 100), 100) if user.water_goal_ml else 0,
        exercise_completed=bool(exercise and exercise.completed),
        meals=[MealEntryOut.model_validate(m) for m in meals],
        drinks=[DrinkEntryOut.model_validate(d) for d in drinks],
        exercise=ExerciseLogOut.model_validate(exercise) if exercise else None,
    )
