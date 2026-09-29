"""
AI Food Suggestions router.

POST /api/ai-food-suggestions/generate       — ask Gemini for meal combinations, persist session.
GET  /api/ai-food-suggestions/usage          — return today's usage count.
GET  /api/ai-food-suggestions/sessions/today — return all saved sessions for today.
GET  /api/ai-food-suggestions/sessions/latest — return the single most-recent session.

Hard limit: 5 requests per user per PKT calendar day.
Each suggestion is a COMPLETE MEAL COMBINATION targeting ~85-100% of remaining calories.
Usage counter only increments AFTER a successful DB save (transactional).
A single free retry fires if Gemini returns chronically under-utilised suggestions.
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

# ── Utilisation validation ────────────────────────────────────────────────────
# Suggestions below this threshold are considered "too low" when the remaining
# budget is substantial. Applied per-item; if the majority fail, one free retry
# fires (does NOT count against the daily limit).
_MIN_UTILISATION = 0.65          # 65% of remaining — below this is considered poor
_LOW_REMAINING_FLOOR = 120       # kcal — below this, any small snack is acceptable


def _is_poor(cal: int, remaining: int) -> bool:
    """True when a suggestion uses too little of the available budget."""
    if remaining <= _LOW_REMAINING_FLOOR:
        return False
    return cal < remaining * _MIN_UTILISATION


def _poor_count(suggestions: list[dict], remaining: int) -> int:
    return sum(1 for s in suggestions if _is_poor(int(s.get("estimated_calories", 0)), remaining))


# ── System instruction ────────────────────────────────────────────────────────

_SYSTEM_INSTRUCTION = """\
You are a Pakistani food recommendation assistant integrated into a personal nutrition tracking application called MealTrack.

The user lives in Lahore, Pakistan. They want COMPLETE MEAL COMBINATIONS — not individual foods — that intelligently use up their remaining daily calorie budget.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MOST IMPORTANT RULE — READ CAREFULLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Each of the 5 suggestions must be an INDEPENDENT, COMPLETE meal/snack combination that individually targets approximately 85–100% of the remaining_calories budget.

They are NOT 5 portions that add up together. Each one is a SEPARATE ALTERNATIVE way to spend the SAME calorie budget.

Example — if remaining = 550 kcal:
  ✅ CORRECT: Option 1 = chicken tikka + chapati + raita ≈ 510 kcal
  ✅ CORRECT: Option 2 = seekh kebabs + small rice + salad ≈ 520 kcal
  ✅ CORRECT: Option 3 = eggs + toast + yogurt + banana ≈ 490 kcal
  ❌ WRONG:   Option 1 = apple ≈ 95 kcal  (way too small when 550 remains)
  ❌ WRONG:   Option 1 = full biryani + dessert + juice ≈ 950 kcal  (exceeds limit)

The TARGET range for each suggestion is: 85%–100% of remaining_calories.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ALWAYS combine multiple foods to reach the target. Use realistic Pakistani portion sizes.

Exception: if remaining_calories is very small (≤ 120 kcal), a single small snack or drink is fine.

Component rules:
- Break each meal into its food components with individual calorie counts.
- Sum of component calories should approximately equal estimated_calories.
- Include realistic portion descriptions (e.g. "150g grilled chicken", "1 chapati", "1 cup dahi").

Pricing rules:
- All prices in PKR with realistic Lahore 2026 market rates.
- estimated_price_min_pkr and estimated_price_max_pkr should be total meal price.

Category tags (assign one per suggestion):
  budget     — affordable street food or homemade
  balanced   — satisfying everyday desi meal
  restaurant — suitable for eating out
  snack      — lighter option / tea-time
  protein    — high-protein focused

Do not recommend foods unavailable in Pakistan.
Consider time of day and what the user already ate to avoid repetition.
The notes field should add a useful tip (macros, where to get it, cooking hint).

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
                        "name": {"type": "STRING"},
                        "components": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "item":     {"type": "STRING"},
                                    "calories": {"type": "INTEGER"},
                                },
                                "required": ["item", "calories"],
                            },
                        },
                        "estimated_calories":      {"type": "INTEGER"},
                        "estimated_price_min_pkr": {"type": "INTEGER"},
                        "estimated_price_max_pkr": {"type": "INTEGER"},
                        "category_tag":            {"type": "STRING"},
                        "notes":                   {"type": "STRING"},
                    },
                    "required": [
                        "name", "components", "estimated_calories",
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
    is_retry: bool = False,
) -> str:
    target_min = int(remaining * 0.85)
    target_max = remaining

    meals_text = (
        "  - " + "\n  - ".join(meal_names) if meal_names else "  (nothing logged yet)"
    )

    base = (
        f"Daily calorie goal: {daily_goal} kcal\n"
        f"Calories consumed today: {consumed} kcal\n"
        f"Remaining calorie budget: {remaining} kcal\n"
        f"Current time of day: {time_label}\n"
        f"\nFoods already eaten today:\n{meals_text}\n"
        f"\nTARGET per suggestion: {target_min}–{target_max} kcal each.\n"
        f"Generate 5 COMPLETE Pakistani meal combinations that each independently "
        f"use approximately {target_min}–{target_max} kcal.\n"
        f"Each option is a separate alternative — they do NOT add up together.\n"
        f"Every combination's estimated_calories MUST be <= {remaining}."
    )

    if is_retry:
        base += (
            f"\n\nATTENTION: Your previous response contained suggestions that were "
            f"far too low in calories for a {remaining} kcal budget. "
            f"Please build proper meal COMBINATIONS this time. "
            f"Each suggestion must be at least {target_min} kcal. "
            f"Do NOT suggest a single small food item when {remaining} kcal are available."
        )

    return base


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
                temperature=0.7,
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
    result = await db.execute(
        select(AiFoodSuggestionUsage.request_count).where(
            AiFoodSuggestionUsage.user_id == user_id,
            AiFoodSuggestionUsage.date == today,
        )
    )
    row = result.scalar_one_or_none()
    return row or 0


async def _increment_usage(db: AsyncSession, user_id: int, today: date) -> int:
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

    # ── Call Gemini (with one free retry if suggestions are chronically under-utilised) ──
    prompt = _build_prompt(remaining, daily_goal, consumed_today, meal_names, time_label)
    raw_suggestions = await _call_gemini(prompt)
    raw_suggestions = raw_suggestions[:5]

    if not raw_suggestions:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI returned no suggestions. Please try again.",
        )

    # Retry once (free — does not cost a request) if majority are too low
    if _poor_count(raw_suggestions, remaining) > len(raw_suggestions) // 2:
        logger.warning(
            "Suggestions under-utilised for remaining=%s kcal (%s/%s poor) — retrying",
            remaining, _poor_count(raw_suggestions, remaining), len(raw_suggestions),
        )
        retry_prompt = _build_prompt(
            remaining, daily_goal, consumed_today, meal_names, time_label, is_retry=True
        )
        try:
            retry_raw = await _call_gemini(retry_prompt)
            retry_raw = retry_raw[:5]
            if retry_raw and _poor_count(retry_raw, remaining) < _poor_count(raw_suggestions, remaining):
                raw_suggestions = retry_raw
                logger.info("Retry produced better suggestions (poor: %s)", _poor_count(retry_raw, remaining))
        except Exception:
            # Retry failed — use original suggestions, don't surface the error
            pass

    # ── Transactional DB save ──────────────────────────────────────────────────
    try:
        session_obj = AiFoodSuggestionSession(
            user_id=user.id,
            date=today_pkt,
            generated_at=now_pkt.replace(tzinfo=None),
            daily_goal_snapshot=daily_goal,
            consumed_snapshot=consumed_today,
            remaining_snapshot=remaining,
            request_number=used + 1,
            model_name=settings.gemini_model,
        )
        db.add(session_obj)
        await db.flush()

        category_order = ["budget", "balanced", "restaurant", "snack", "protein"]
        for idx, s in enumerate(raw_suggestions):
            # Cap calories to remaining budget
            cal = min(int(s.get("estimated_calories", 0)), remaining)
            cat = s.get("category_tag", "").lower().strip()
            if cat not in category_order:
                cat = category_order[idx] if idx < len(category_order) else "balanced"

            # Cap each component's calories too, then store as JSON
            raw_components = s.get("components", [])
            components = [
                {"item": c.get("item", ""), "calories": int(c.get("calories", 0))}
                for c in raw_components
                if c.get("item")
            ]

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
                components_json=json.dumps(components, ensure_ascii=False),
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
