"""
Shared evaluation business logic used by both the API router and the scheduler.
No HTTP request context assumed — works from a raw AsyncSession + User.
"""
import json
import logging
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .gemini import AI_EVALUATION_PROMPT_VERSION, GeminiError, build_input_hash, evaluate_day
from .models import AiDailyEvaluation, MealEntry, User
from .routers.summary import _build_daily
from .schemas import AiEvaluationDetail, GeminiEvaluationResult

logger = logging.getLogger(__name__)


async def get_evaluation(db: AsyncSession, user: User, day: date) -> Optional[AiDailyEvaluation]:
    """Fetch the stored evaluation for a user/date. Returns None if not found."""
    result = await db.execute(
        select(AiDailyEvaluation).where(
            AiDailyEvaluation.user_id == user.id,
            AiDailyEvaluation.date == day,
        )
    )
    return result.scalar_one_or_none()


def _meals_to_dicts(meals) -> list:
    return [
        {
            "id": m.id,
            "name": m.name,
            "calories": m.calories,
            "meal_type": m.meal_type if isinstance(m.meal_type, str) else m.meal_type.value,
            "time": m.time,
            "note": m.note or "",
        }
        for m in meals
    ]


async def generate_evaluation(
    db: AsyncSession,
    user: User,
    day: date,
    trigger_source: str,
    force: bool = False,
) -> AiDailyEvaluation:
    """
    Core evaluation pipeline.

    1. Load meal data.
    2. Check zero-meals → raise ValueError.
    3. If not force and evaluation exists → return existing.
    4. Build input hash.
    5. Call Gemini (outside any write transaction).
    6. Upsert evaluation row.

    Raises:
        ValueError: Zero meals logged — Gemini must not be called.
        GeminiError: Gemini API or validation failure.
    """
    # ── 1. Load meal data ────────────────────────────────────────────────────
    summary = await _build_daily(db, user, day)
    meal_dicts = _meals_to_dicts(summary.meals)

    # ── 2. Zero-meals guard ──────────────────────────────────────────────────
    if not meal_dicts:
        logger.info("Skipping evaluation for %s — zero meals logged", day.isoformat())
        raise ValueError(f"No meals logged for {day.isoformat()} — evaluation skipped")

    # ── 3. Return existing unless force ─────────────────────────────────────
    existing = await get_evaluation(db, user, day)
    if existing and not force:
        logger.info("Returning existing evaluation for %s", day.isoformat())
        return existing

    # ── 4. Build input hash ──────────────────────────────────────────────────
    input_hash = build_input_hash(meal_dicts, summary.calorie_goal)

    # ── 5. Call Gemini (no write transaction open here) ──────────────────────
    gemini_result: GeminiEvaluationResult = await evaluate_day(
        day=day,
        meals=meal_dicts,
        total_calories=summary.total_calories,
        calorie_goal=summary.calorie_goal,
    )
    evaluation_json = gemini_result.model_dump_json()

    # ── 6. Upsert ────────────────────────────────────────────────────────────
    if existing:
        # UPDATE existing row (force=True path)
        existing.overall_score = gemini_result.overall_score
        existing.evaluation_json = evaluation_json
        existing.model_name = settings.gemini_model
        existing.prompt_version = AI_EVALUATION_PROMPT_VERSION
        existing.trigger_source = trigger_source
        existing.input_hash = input_hash
        await db.commit()
        await db.refresh(existing)
        logger.info("Evaluation updated for %s (force re-evaluate)", day.isoformat())
        return existing
    else:
        new_eval = AiDailyEvaluation(
            user_id=user.id,
            date=day,
            overall_score=gemini_result.overall_score,
            evaluation_json=evaluation_json,
            model_name=settings.gemini_model,
            prompt_version=AI_EVALUATION_PROMPT_VERSION,
            trigger_source=trigger_source,
            input_hash=input_hash,
        )
        db.add(new_eval)
        await db.commit()
        await db.refresh(new_eval)
        logger.info("Evaluation persisted for %s (trigger=%s)", day.isoformat(), trigger_source)
        return new_eval


def parse_evaluation(row: AiDailyEvaluation) -> AiEvaluationDetail:
    """Deserialize stored JSON and return a typed AiEvaluationDetail."""
    evaluation = GeminiEvaluationResult.model_validate_json(row.evaluation_json)
    return AiEvaluationDetail(
        id=row.id,
        date=row.date,
        overall_score=row.overall_score,
        model_name=row.model_name,
        prompt_version=row.prompt_version,
        trigger_source=row.trigger_source,
        input_hash=row.input_hash,
        created_at=row.created_at,
        updated_at=row.updated_at,
        evaluation=evaluation,
    )
