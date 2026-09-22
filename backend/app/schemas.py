from datetime import date
from typing import List, Optional

from pydantic import BaseModel, EmailStr, field_validator

from .models import MealType


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── User ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    calorie_goal: int
    water_goal_ml: int
    exercise_goal_days: int

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: Optional[str] = None
    calorie_goal: Optional[int] = None
    water_goal_ml: Optional[int] = None
    exercise_goal_days: Optional[int] = None
    password: Optional[str] = None


# ── Meals ─────────────────────────────────────────────────────────────────────

class MealEntryCreate(BaseModel):
    date: Optional[date] = None
    time: str
    meal_type: MealType
    name: str
    calories: int
    emoji: str = "🍽️"
    note: str = ""

    @field_validator("calories")
    @classmethod
    def calories_positive(cls, v):
        if v < 0:
            raise ValueError("calories must be >= 0")
        return v


class MealEntryUpdate(BaseModel):
    time: Optional[str] = None
    meal_type: Optional[MealType] = None
    name: Optional[str] = None
    calories: Optional[int] = None
    emoji: Optional[str] = None
    note: Optional[str] = None


class MealEntryOut(BaseModel):
    id: int
    date: date
    time: str
    meal_type: str
    name: str
    calories: int
    emoji: str
    note: str

    model_config = {"from_attributes": True}


# ── Drinks ────────────────────────────────────────────────────────────────────

class DrinkEntryCreate(BaseModel):
    date: Optional[date] = None
    time: str
    name: str
    amount_ml: int
    emoji: str = "💧"

    @field_validator("amount_ml")
    @classmethod
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("amount_ml must be > 0")
        return v


class DrinkEntryUpdate(BaseModel):
    time: Optional[str] = None
    name: Optional[str] = None
    amount_ml: Optional[int] = None
    emoji: Optional[str] = None


class DrinkEntryOut(BaseModel):
    id: int
    date: date
    time: str
    name: str
    amount_ml: int
    emoji: str

    model_config = {"from_attributes": True}


# ── Exercise ──────────────────────────────────────────────────────────────────

class ExerciseLogCreate(BaseModel):
    date: Optional[date] = None
    exercise_type: str
    duration_minutes: int
    calories_burned: Optional[int] = None
    time: str = "00:00"
    completed: bool = True


class ExerciseLogUpdate(BaseModel):
    exercise_type: Optional[str] = None
    duration_minutes: Optional[int] = None
    calories_burned: Optional[int] = None
    time: Optional[str] = None
    completed: Optional[bool] = None


class ExerciseLogOut(BaseModel):
    id: int
    date: date
    exercise_type: str
    duration_minutes: int
    calories_burned: Optional[int]
    time: str
    completed: bool

    model_config = {"from_attributes": True}


# ── Dashboard / Summary ───────────────────────────────────────────────────────

class DailySummaryOut(BaseModel):
    date: date
    total_calories: int
    total_water_ml: int
    calories_burned: int
    net_calories: int
    meals_logged: int
    calorie_goal: int
    water_goal_ml: int
    calorie_pct: int
    water_pct: int
    exercise_completed: bool
    meals: List[MealEntryOut]
    drinks: List[DrinkEntryOut]
    exercise: Optional[ExerciseLogOut]


class WeeklyDayOut(BaseModel):
    date: date
    day: str
    calories: int
    is_today: bool
    exercise_completed: bool


class WeeklySummaryOut(BaseModel):
    days: List[WeeklyDayOut]
    avg_calories: int
    days_exercised: int


class RangeDayOut(BaseModel):
    date: date
    calories: int
    water_ml: int
    exercise_completed: bool


class StatsOut(BaseModel):
    days_logged: int
    exercise_days: int
    current_streak: int
    avg_calories_30d: int


class FoodItem(BaseModel):
    name: str
    calories: int
    emoji: str
    per: str
