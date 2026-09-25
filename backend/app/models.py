from __future__ import annotations

import enum
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, Float, ForeignKey,
    Integer, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class MealType(str, enum.Enum):
    breakfast       = "Breakfast"
    morning_snack   = "Morning Snack"
    lunch           = "Lunch"
    afternoon_snack = "Afternoon Snack"
    dinner          = "Dinner"
    late_snack      = "Late Snack"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Daily goals
    calorie_goal: Mapped[int] = mapped_column(Integer, nullable=False, default=2000)
    water_goal_ml: Mapped[int] = mapped_column(Integer, nullable=False, default=2500)
    exercise_goal_days: Mapped[int] = mapped_column(Integer, nullable=False, default=5)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    meals: Mapped[List["MealEntry"]] = relationship("MealEntry", back_populates="user", cascade="all, delete-orphan")
    drinks: Mapped[List["DrinkEntry"]] = relationship("DrinkEntry", back_populates="user", cascade="all, delete-orphan")
    exercises: Mapped[List["ExerciseLog"]] = relationship("ExerciseLog", back_populates="user", cascade="all, delete-orphan")


class MealEntry(Base):
    __tablename__ = "meal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    time: Mapped[str] = mapped_column(String(5), nullable=False)           # "HH:MM"
    meal_type: Mapped[MealType] = mapped_column(Enum(MealType), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    calories: Mapped[int] = mapped_column(Integer, nullable=False)
    emoji: Mapped[str] = mapped_column(String(10), nullable=False, default="🍽️")
    note: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="meals")


class DrinkEntry(Base):
    __tablename__ = "drink_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    time: Mapped[str] = mapped_column(String(5), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount_ml: Mapped[int] = mapped_column(Integer, nullable=False)
    emoji: Mapped[str] = mapped_column(String(10), nullable=False, default="💧")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="drinks")


class ExerciseLog(Base):
    __tablename__ = "exercise_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    exercise_type: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    calories_burned: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    time: Mapped[str] = mapped_column(String(5), nullable=False, default="00:00")
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Set when the entry was synced from an external source (e.g. gym-tracker).
    # Used for idempotent upsert — re-delivering the same event is safe.
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True, index=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="exercises")
