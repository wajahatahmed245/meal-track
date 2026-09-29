"""
AI Food Suggestions router.

POST /api/ai-food-suggestions/generate       — ask Gemini for food ideas, persist session in DB.
GET  /api/ai-food-suggestions/usage          — return today's usage count.
GET  /api/ai-food-suggestions/sessions/today — return all saved sessions for today.
GET  /api/ai-food-suggestions/sessions/latest — return the single most-recent session.

Hard limit: 5 requests per user per PKT calendar day.
Each successful generation produces 5 suggestions and one persisted session.
Usage counter is only incremented AFTER a successful DB save (transactional).
"""
import json
import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import (
    AiFoodSuggestionItem,
    AiFoodSuggestionSession,
    AiFoodSuggestionUsage,
    MealEntry,
    User,
)
from ..schemas import (
    FoodSuggestionsResponse,
    FoodSuggestionSessionOut,
    SuggestionUsageResponse,
    TodaySessionsResponse,
)

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

Always suggest exactly 5 options covering a range of meal styles:
1. Budget option — affordable, simple, homemade or street food (category_tag: "budget")
2. Balanced everyday option — a satisfying everyday desi meal (category_tag: "balanced")
3. Restaurant or fast-food option — suitable if eating out (category_tag: "restaurant")
4. Light snack option — low-calorie snack or beverage (category_tag: "snack")
5. High-protein option — protein-focused meal or snack (category_tag: "protein")

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
                        "category_tag":            {"type": "STRING"},
                        "notes":                   {"type": "STRING"},
                    },
                    "required": [
                        "name", "description", "estimated_calories",
                        "estimated_price_min_pkr", "estimated_price_max_pkr",
                        "category_tag", "notes",
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
        f"\nSuggest 5 practical Pakistani/desi food options that fit within {remaining} kcal. "
        f"Each suggestion must have estimated_calories <= {remaining}. "
        f"Follow the category_tag values defined in your instructions exactly."
    )


async def _call_gemini(prompt: str) -> list[dict]:
    """Call Gemini for food suggestions. Returns a list of raw suggestion dicts."""
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
    """Upsert usage row, increment count (call only AFTER successful DB save), return new count."""
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


async def _load_session_with_items(db: AsyncSession, session_id: int) -> AiFoodSuggestionSession:
    """Eagerly load a session with its items by id."""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(AiFoodSuggestionSession)
        .options(selectinload(AiFoodSuggestionSession.items))
        .where(AiFoodSuggestionSession.id == session_id)
    )
    return result.scalar_one()


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


@router.get("/sessions/today", response_model=TodaySessionsResponse)
async def get_today_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload
    today_pkt = datetime.now(PKT).date()
    result = await db.execute(
        select(AiFoodSuggestionSession)
        .options(selectinload(AiFoodSuggestionSession.items))
        .where(
            AiFoodSuggestionSession.user_id == user.id,
            AiFoodSuggestionSession.date == today_pkt,
        )
        .order_by(AiFoodSuggestionSession.generated_at.desc())
    )
    sessions = result.scalars().all()
    used = await _get_usage(db, user.id, today_pkt)
    return TodaySessionsResponse(
        sessions=sessions,
        requests_used_today=used,
        requests_limit=DAILY_LIMIT,
    )


@router.get("/sessions/latest", response_model=FoodSuggestionSessionOut)
async def get_latest_session(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(AiFoodSuggestionSession)
        .options(selectinload(AiFoodSuggestionSession.items))
        .where(AiFoodSuggestionSession.user_id == user.id)
        .order_by(AiFoodSuggestionSession.generated_at.desc())
        .limit(1)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No sessions found.")
    return session


@router.post("/generate", response_model=FoodSuggestionsResponse)
async def generate_suggestions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now_pkt = datetime.now(PKT)
    today_pkt = now_pkt.date()

    # Check daily limit BEFORE calling Gemini
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

    # Call Gemini — may raise HTTPException; if so, we never touch the DB
    raw_suggestions = await _call_gemini(prompt)

    # Validate suggestions and cap calories to remaining budget
    raw_suggestions = raw_suggestions[:5]
    if not raw_suggestions:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI returned no suggestions. Please try again.",
        )

    # Transactional DB save — only after a successful AI response
    try:
        session_obj = AiFoodSuggestionSession(
            user_id=user.id,
            date=today_pkt,
            generated_at=now_pkt.replace(tzinfo=None),  # store as naive UTC+5
            daily_goal_snapshot=daily_goal,
            consumed_snapshot=consumed_today,
            remaining_snapshot=remaining,
            request_number=used + 1,
            model_name=settings.gemini_model,
        )
        db.add(session_obj)
        await db.flush()  # get session_obj.id without committing

        category_order = ["budget", "balanced", "restaurant", "snack", "protein"]
        for idx, s in enumerate(raw_suggestions):
            cal = min(int(s.get("estimated_calories", 0)), remaining)
            cat = s.get("category_tag", "").lower().strip()
            if cat not in category_order:
                cat = category_order[idx] if idx < len(category_order) else "balanced"
            item = AiFoodSuggestionItem(
                session_id=session_obj.id,
                display_order=idx + 1,
                name=s.get("name", ""),
                description=s.get("description", ""),
                estimated_calories=cal,
                price_min_pkr=int(s.get("estimated_price_min_pkr", 0)),
                price_max_pkr=int(s.get("estimated_price_max_pkr", 0)),
                calories_after=consumed_today + cal,
                category_tag=cat,
                notes=s.get("notes", ""),
            )
            db.add(item)

        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to save food suggestion session to DB: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save suggestions. Your daily count was NOT incremented.",
        )

    # Increment usage ONLY after a successful DB save
    new_count = await _increment_usage(db, user.id, today_pkt)

    # Reload with items eagerly loaded
    saved_session = await _load_session_with_items(db, session_obj.id)

    logger.info(
        "Food suggestions saved for user_id=%s: remaining=%s kcal, items=%s, usage=%s/%s",
        user.id, remaining, len(raw_suggestions), new_count, DAILY_LIMIT,
    )

    return FoodSuggestionsResponse(
        session=saved_session,
        requests_used_today=new_count,
        requests_limit=DAILY_LIMIT,
    )
