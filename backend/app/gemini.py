"""
Gemini AI client for MealTrack daily food evaluations.

Isolated module — no DB access, no FastAPI imports, no router coupling.
Accepts prepared meal data, calls Gemini, validates structured output,
returns a typed GeminiEvaluationResult.

SDK: google-genai (NOT the legacy google-generativeai)
"""
import hashlib
import json
import logging
from datetime import date
from typing import List

from google import genai
from google.genai import types

from .config import settings
from .schemas import GeminiEvaluationResult, MealEvaluationItem

logger = logging.getLogger(__name__)

AI_EVALUATION_PROMPT_VERSION = "v1"

_SYSTEM_INSTRUCTION = """\
You are the daily food-evaluation engine for a personal nutrition tracking application called MealTrack.

You receive one COMPLETE calendar day's logged meals.

Your purpose is to provide a concise, practical nutritional-quality evaluation of the food consumed that day.

IMPORTANT:
The calorie values supplied by MealTrack are authoritative. Never replace or recalculate them.

Evaluate the whole day, not individual foods in isolation.

Consider where reasonably inferable:
- overall calorie pattern
- meal balance
- calorie density
- likely protein sources
- likely vegetables/fruit/fibre
- likely added sugar
- likely saturated fat
- likely sodium
- degree of processing
- meal timing
- repetition of calorie-dense foods
- variety across the day

Do not invent exact macro or micronutrient values.

When recipe, preparation method, ingredients, or serving size are unknown, acknowledge uncertainty.

Do not describe normal foods as toxic or poisonous.

Do not diagnose disease.

Do not make claims that one day's food caused or prevented a medical condition.

Use practical, non-alarmist language. Use cautious qualifiers: likely, may, could, generally, \
based on the logged information, exact composition depends on preparation.

A high-calorie food is not automatically unhealthy. A low-calorie food is not automatically healthy.

Recommendations should focus on realistic improvements: portion balance, food variety, vegetables, \
fruit, protein balance, limiting repeated fried/sugary/highly processed foods, meal timing, overall balance.

Do not recommend extreme restriction.

The result must be understandable to a normal user reading a mobile dashboard.

Return ONLY data matching the supplied structured-output schema.
"""


def build_input_hash(meals: list, calorie_goal: int) -> str:
    """
    Deterministic SHA-256 of meal inputs so the UI can detect stale evaluations.
    Stable across restarts — based only on the meal data content.
    """
    parts = []
    for m in sorted(meals, key=lambda x: x.get("id", 0)):
        parts.append(
            f"{m.get('id')}|{m.get('name')}|{m.get('calories')}|"
            f"{m.get('meal_type')}|{m.get('time')}|{m.get('note', '')}"
        )
    parts.append(f"goal:{calorie_goal}")
    raw = "\n".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()


def _build_prompt(day: date, meals: list, total_calories: int, calorie_goal: int) -> str:
    lines = [
        f"Date: {day.isoformat()}",
        f"Daily calorie goal: {calorie_goal} kcal",
        f"Total calories consumed: {total_calories} kcal",
        "",
        "Meals logged:",
    ]
    for m in meals:
        note_part = f" | Note: {m['note']}" if m.get("note") else ""
        lines.append(
            f"  - {m['meal_type']} at {m['time']}: {m['name']} "
            f"({m['calories']} kcal){note_part}"
        )
    return "\n".join(lines)


def _gemini_response_schema() -> dict:
    """JSON schema for Gemini structured output, matching GeminiEvaluationResult."""
    meal_item_schema = {
        "type": "OBJECT",
        "properties": {
            "food_name":        {"type": "STRING"},
            "meal_type":        {"type": "STRING"},
            "time":             {"type": "STRING"},
            "logged_calories":  {"type": "INTEGER"},
            "assessment":       {"type": "STRING"},
            "likely_benefits":  {"type": "ARRAY", "items": {"type": "STRING"}},
            "things_to_watch":  {"type": "ARRAY", "items": {"type": "STRING"}},
        },
        "required": ["food_name", "meal_type", "time", "logged_calories",
                     "assessment", "likely_benefits", "things_to_watch"],
    }
    return {
        "type": "OBJECT",
        "properties": {
            "overall_score":                    {"type": "INTEGER"},
            "overall_assessment":               {"type": "STRING"},
            "what_went_well":                   {"type": "ARRAY", "items": {"type": "STRING"}},
            "things_to_watch":                  {"type": "ARRAY", "items": {"type": "STRING"}},
            "meal_evaluations":                 {"type": "ARRAY", "items": meal_item_schema},
            "daily_benefits":                   {"type": "ARRAY", "items": {"type": "STRING"}},
            "daily_concerns":                   {"type": "ARRAY", "items": {"type": "STRING"}},
            "improve_tomorrow":                 {"type": "ARRAY", "items": {"type": "STRING"}},
            "reduce_or_avoid_repeating_tomorrow": {"type": "ARRAY", "items": {"type": "STRING"}},
            "final_recommendation":             {"type": "STRING"},
            "confidence":                       {"type": "STRING"},
        },
        "required": [
            "overall_score", "overall_assessment", "what_went_well", "things_to_watch",
            "meal_evaluations", "daily_benefits", "daily_concerns", "improve_tomorrow",
            "reduce_or_avoid_repeating_tomorrow", "final_recommendation", "confidence",
        ],
    }


class GeminiError(Exception):
    """Raised when the Gemini API call fails or returns invalid data."""


async def evaluate_day(
    day: date,
    meals: list,
    total_calories: int,
    calorie_goal: int,
) -> GeminiEvaluationResult:
    """
    Call Gemini for a structured daily food evaluation.

    Args:
        day: The calendar date being evaluated.
        meals: List of meal dicts with keys: id, name, calories, meal_type, time, note.
        total_calories: Sum of all meal calories for the day.
        calorie_goal: User's daily calorie goal.

    Returns:
        Validated GeminiEvaluationResult.

    Raises:
        GeminiError: On API failure or schema validation failure.
    """
    if not settings.gemini_api_key:
        raise GeminiError("GEMINI_API_KEY is not configured")

    prompt = _build_prompt(day, meals, total_calories, calorie_goal)
    logger.info("Gemini request started for %s (%d meals)", day.isoformat(), len(meals))

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=_gemini_response_schema(),
                temperature=0.4,
            ),
        )
    except Exception as exc:
        logger.error("Gemini API call failed for %s: %s", day.isoformat(), exc)
        raise GeminiError(f"Gemini API error: {exc}") from exc

    raw_text = response.text
    if not raw_text:
        raise GeminiError("Gemini returned an empty response")

    logger.info("Gemini request succeeded for %s", day.isoformat())

    try:
        data = json.loads(raw_text)
        result = GeminiEvaluationResult.model_validate(data)
    except Exception as exc:
        logger.error("Gemini response validation failed for %s: %s", day.isoformat(), exc)
        raise GeminiError(f"Gemini response schema validation failed: {exc}") from exc

    # Clamp score to 1–10
    result.overall_score = max(1, min(10, result.overall_score))
    return result
