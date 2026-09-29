from __future__ import annotations

import enum
from datetime import date, datetime
from typing import List, Optional

import json as _json

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint, func,
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
    evaluations: Mapped[List["AiDailyEvaluation"]] = relationship("AiDailyEvaluation", back_populates="user", cascade="all, delete-orphan")
    food_suggestion_usage: Mapped[List["AiFoodSuggestionUsage"]] = relationship("AiFoodSuggestionUsage", back_populates="user", cascade="all, delete-orphan")
    food_suggestion_sessions: Mapped[List["AiFoodSuggestionSession"]] = relationship("AiFoodSuggestionSession", back_populates="user", cascade="all, delete-orphan")


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


class AiDailyEvaluation(Base):
    __tablename__ = "ai_daily_evaluations"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_ai_eval_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    # Full Gemini structured response stored as JSON text
    evaluation_json: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    # "scheduled" or "manual"
    trigger_source: Mapped[str] = mapped_column(String(20), nullable=False)
    # SHA-256 of the meal input — lets UI detect stale evaluations after meal edits
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="evaluations")


class AiFoodSuggestionUsage(Base):
    """Tracks how many AI food suggestion requests a user has made on a given PKT date."""
    __tablename__ = "ai_food_suggestion_usage"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_suggestion_usage_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped["User"] = relationship("User", back_populates="food_suggestion_usage")


class AiFoodSuggestionSession(Base):
    """
    One persisted generation session — a single successful AI call.
    Stores a snapshot of the calorie state at generation time so that
    later meals do not retroactively alter historical records.
    """
    __tablename__ = "ai_food_suggestion_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Snapshot — frozen at generation time
    daily_goal_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    consumed_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    # Which request number this was on this day (1-5)
    request_number: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    user: Mapped["User"] = relationship("User", back_populates="food_suggestion_sessions")
    items: Mapped[List["AiFoodSuggestionItem"]] = relationship(
        "AiFoodSuggestionItem",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AiFoodSuggestionItem.display_order",
    )


class AiFoodSuggestionItem(Base):
    """One food suggestion within a session. Five per successful session."""
    __tablename__ = "ai_food_suggestion_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("ai_food_suggestion_sessions.id"), nullable=False, index=True
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)   # 1-5
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    estimated_calories: Mapped[int] = mapped_column(Integer, nullable=False)
    price_min_pkr: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price_max_pkr: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Projected total after eating this item (snapshot + estimated_calories)
    calories_after: Mapped[int] = mapped_column(Integer, nullable=False)
    # budget | balanced | restaurant | snack | protein
    category_tag: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    notes: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    # JSON array of {"item": str, "calories": int} — individual food components
    components_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    session: Mapped["AiFoodSuggestionSession"] = relationship(
        "AiFoodSuggestionSession", back_populates="items"
    )

    @property
    def components(self) -> list:
        try:
            return _json.loads(self.components_json or "[]")
        except Exception:
            return []
