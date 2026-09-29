"""
AI Food Suggestions router.

POST /api/ai-food-suggestions/generate  — ask Gemini for food ideas that fit remaining calories.
GET  /api/ai-food-suggestions/usage     — return today's usage count.

Hard limit: 5 requests per user per PKT calendar day.
"""
import json
import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import AiFoodSuggestionUsage, MealEntry, User
from ..schemas import FoodSuggestionItem, FoodSuggestionsResponse, SuggestionUsageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-food-suggestions", tags=["ai-food-suggestions"])

PKT = timezone(timedelta(hours=5))
DAILY_LIMIT = 5

_SYSTEM_INSTRUCTION = """\
You are a Pakistani food recommendation assistant integrated into a personal nutrition tracking application called MealTrack.

The user lives in Lahore, Pakistan and wants practical, realistic food suggestions that fit within their remaining daily calorie budget.

Always recommend foods that are:
- Available in Pakistan (Pakistani cuisine, desi homemade food, local restaurant food, local fast food)
- Within or at most equal to the user's remaining calorie budget
- Priced in PKR (Pakistani Rupees) with realistic Lahore 2026 market prices
- Practical for everyday eating — not unnecessarily expensive or hard to find

Always suggest exactly 3 options in this order:
1. Budget option — affordable, simple, homemade or street food
2. Balanced everyday option — a satisfying everyday desi meal
3. Restaurant or fast-food option — suitable if eating out

Rules:
- Each suggestion's estimated_calories MUST be <= remaining_calories. Never exceed the budget.
- Price ranges should be realistic Lahore estimates, not exact amounts.
- Prefer portion sizes over vague descriptions — e.g. "150g grilled chicken" not just "chicken".
- Do not recommend foods that are unavailable in Pakistan or require imported ingredients.
- Consider what the user has already eaten today to avoid repetition or nutritional imbalance.
- Consider the time of day to recommend appropriately timed meals or snacks.
- The notes field should add useful context: e.g. macros, where to get it, or a tip.

Return valid JSON only, matching the exact schema provided.
"""


def _gemini_response_schema() -> dict:
    return {
        "type": "OBJECT",
        "properties": {
            "suggestions": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "name":                    {"type": "STRING"},
                        "description":             {"type": "STRING"},
                        "estimated_calories":      {"type": "INTEGER"},
                        "estimated_price_min_pkr": {"type": "INTEGER"},
                        "estimated_price_max_pkr": {"type": "INTEGER"},
                        "notes":                   {"type": "STRING"},
                    },
                    "required": [
                        "name", "description", "estimated_calories",
                        "estimated_price_min_pkr", "estimated_price_max_pkr", "notes",
                    ],
                },
            }
        },
        "required": ["suggestions"],
    }


def _time_of_day(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def _build_prompt(
    remaining: int,
    daily_goal: int,
    consumed: int,
    meal_names: list[str],
    time_label: str,
) -> str:
    meals_text = (
        "  - " + "\n  - ".join(meal_names) if meal_names else "  (nothing logged yet)"
    )
    return (
        f"Daily calorie goal: {daily_goal} kcal\n"
        f"Calories consumed today: {consumed} kcal\n"
        f"Remaining calorie budget: {remaining} kcal\n"
        f"Current time of day: {time_label}\n"
        f"\nFoods already eaten today:\n{meals_text}\n"
        f"\nSuggest 3 practical Pakistani/desi food options that fit within {remaining} kcal. "
        f"Each suggestion must have estimated_calories <= {remaining}."
    )


async def _call_gemini(prompt: str) -> list[dict]:
    """Call Gemini for food suggestions. Returns a list of suggestion dicts."""
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured (missing API key).",
        )
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key)
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=_gemini_response_schema(),
                temperature=0.6,
            ),
        )
    except Exception as exc:
        logger.error("Gemini API call failed for food suggestions: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI food suggestion service is temporarily unavailable. Please try again later.",
        )

    raw = response.text
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI returned an empty response. Please try again.",
        )

    try:
        data = json.loads(raw)
        return data.get("suggestions", [])
    except Exception as exc:
        logger.error("Failed to parse Gemini food suggestions response: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI response could not be parsed. Please try again.",
        )


async def _get_usage(db: AsyncSession, user_id: int, today: date) -> int:
    """Return today's request count for this user (0 if no row yet)."""
    result = await db.execute(
        select(AiFoodSuggestionUsage.request_count).where(
            AiFoodSuggestionUsage.user_id == user_id,
            AiFoodSuggestionUsage.date == today,
        )
    )
    row = result.scalar_one_or_none()
    return row or 0


async def _increment_usage(db: AsyncSession, user_id: int, today: date) -> int:
    """Upsert usage row, increment count, return new count."""
    stmt = sqlite_insert(AiFoodSuggestionUsage).values(
        user_id=user_id, date=today, request_count=1
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "date"],
        set_={"request_count": AiFoodSuggestionUsage.request_count + 1},
    )
    await db.execute(stmt)
    await db.commit()
    return await _get_usage(db, user_id, today)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/usage", response_model=SuggestionUsageResponse)
async def get_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today_pkt = datetime.now(PKT).date()
    used = await _get_usage(db, user.id, today_pkt)
    return SuggestionUsageResponse(
        requests_used_today=used,
        requests_limit=DAILY_LIMIT,
        remaining_requests=max(0, DAILY_LIMIT - used),
        date=today_pkt.isoformat(),
    )


@router.post("/generate", response_model=FoodSuggestionsResponse)
async def generate_suggestions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now_pkt = datetime.now(PKT)
    today_pkt = now_pkt.date()

    # Check daily limit
    used = await _get_usage(db, user.id, today_pkt)
    if used >= DAILY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily suggestion limit reached ({DAILY_LIMIT}/{DAILY_LIMIT}). Try again tomorrow.",
        )

    # Fetch today's consumed calories and meal names
    meals_result = await db.execute(
        select(MealEntry.name, MealEntry.calories).where(
            MealEntry.user_id == user.id,
            MealEntry.date == today_pkt,
        ).order_by(MealEntry.time.asc())
    )
    meals = meals_result.all()
    consumed_today = sum(m.calories for m in meals)
    meal_names = [m.name for m in meals]

    daily_goal = user.calorie_goal or 2000
    remaining = max(0, daily_goal - consumed_today)

    time_label = _time_of_day(now_pkt.hour)
    prompt = _build_prompt(remaining, daily_goal, consumed_today, meal_names, time_label)

    # Call Gemini
    raw_suggestions = await _call_gemini(prompt)

    # Validate and cap suggestions at remaining calories
    suggestions = []
    for s in raw_suggestions[:3]:
        cal = min(int(s.get("estimated_calories", 0)), remaining)
        suggestions.append(FoodSuggestionItem(
            name=s.get("name", ""),
            description=s.get("description", ""),
            estimated_calories=cal,
            estimated_price_min_pkr=int(s.get("estimated_price_min_pkr", 0)),
            estimated_price_max_pkr=int(s.get("estimated_price_max_pkr", 0)),
            notes=s.get("notes", ""),
        ))

    # Increment usage counter
    new_count = await _increment_usage(db, user.id, today_pkt)

    logger.info(
        "Food suggestions generated for user_id=%s: remaining=%s kcal, suggestions=%s, usage=%s/%s",
        user.id, remaining, len(suggestions), new_count, DAILY_LIMIT,
    )

    return FoodSuggestionsResponse(
        remaining_calories=remaining,
        daily_goal=daily_goal,
        consumed_today=consumed_today,
        suggestions=suggestions,
        requests_used_today=new_count,
        requests_limit=DAILY_LIMIT,
        generated_at=now_pkt.isoformat(),
    )
