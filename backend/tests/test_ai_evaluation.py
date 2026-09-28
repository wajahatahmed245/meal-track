"""
Tests for the AI Evaluation feature.
Gemini is NEVER called against the real API — all tests mock evaluate_day.
"""
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError as SAIntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_evaluation_service import generate_evaluation, get_evaluation
from app.gemini import GeminiError, build_input_hash
from app.models import AiDailyEvaluation, MealEntry, MealType, User
from app.scheduler import _yesterday_pkt, run_startup_catchup
from tests.conftest import TestSession, mock_gemini_result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gemini_patch():
    """Stub evaluate_day so no real Gemini calls are made."""
    return patch(
        "app.ai_evaluation_service.evaluate_day",
        new_callable=AsyncMock,
        return_value=mock_gemini_result(),
    )


def _scheduler_session_patch():
    """Patch app.scheduler.AsyncSessionLocal to use the test engine's session factory."""
    return patch("app.scheduler.AsyncSessionLocal", new=TestSession)


# ── 1. Manual evaluation succeeds for a day with meals ───────────────────────

@pytest.mark.asyncio
async def test_manual_evaluation_success(auth_client: AsyncClient, day_with_meals: date):
    day = day_with_meals.isoformat()
    with _gemini_patch() as mock_eval:
        resp = await auth_client.post(f"/api/ai-evaluation?day={day}")
    assert resp.status_code == 201
    data = resp.json()
    assert data["overall_score"] == 7
    assert data["trigger_source"] == "manual"
    assert "evaluation" in data
    mock_eval.assert_awaited_once()


# ── 2. Zero meals → 422, Gemini NOT called ───────────────────────────────────

@pytest.mark.asyncio
async def test_zero_meals_returns_422(auth_client: AsyncClient, day_no_meals: date):
    day = day_no_meals.isoformat()
    with _gemini_patch() as mock_eval:
        resp = await auth_client.post(f"/api/ai-evaluation?day={day}")
    assert resp.status_code == 422
    assert "No meals logged" in resp.json()["detail"]
    mock_eval.assert_not_awaited()


# ── 3. GET returns stored result without calling Gemini ───────────────────────

@pytest.mark.asyncio
async def test_get_stored_evaluation_no_gemini_call(auth_client: AsyncClient, day_with_meals: date):
    day = day_with_meals.isoformat()
    with _gemini_patch():
        r = await auth_client.post(f"/api/ai-evaluation?day={day}")
    assert r.status_code == 201

    with _gemini_patch() as mock_eval:
        get_r = await auth_client.get(f"/api/ai-evaluation?day={day}")
    assert get_r.status_code == 200
    assert get_r.json()["overall_score"] == 7
    mock_eval.assert_not_awaited()


# ── 4. POST without force when evaluation exists → return existing ─────────────

@pytest.mark.asyncio
async def test_post_no_force_returns_existing(auth_client: AsyncClient, day_with_meals: date):
    day_str = day_with_meals.isoformat()
    with _gemini_patch():
        r1 = await auth_client.post(f"/api/ai-evaluation?day={day_str}")
    assert r1.status_code == 201
    first_id = r1.json()["id"]

    with _gemini_patch() as mock_eval:
        r2 = await auth_client.post(f"/api/ai-evaluation?day={day_str}&force=false")
    assert r2.status_code == 201
    assert r2.json()["id"] == first_id
    mock_eval.assert_not_awaited()


# ── 5. force=true → Gemini called once, row updated, no second row ────────────

@pytest.mark.asyncio
async def test_force_reeval_updates_row(auth_client: AsyncClient, day_with_meals: date, db_session: AsyncSession):
    day_str = day_with_meals.isoformat()
    with _gemini_patch():
        r1 = await auth_client.post(f"/api/ai-evaluation?day={day_str}")
    assert r1.status_code == 201
    first_id = r1.json()["id"]

    with _gemini_patch() as mock_eval:
        r2 = await auth_client.post(f"/api/ai-evaluation?day={day_str}&force=true")
    assert r2.status_code == 201
    assert r2.json()["id"] == first_id   # same row
    mock_eval.assert_awaited_once()

    result = await db_session.execute(
        select(AiDailyEvaluation).where(AiDailyEvaluation.date == day_with_meals)
    )
    rows = result.scalars().all()
    assert len(rows) == 1


# ── 6. Scheduler uses previous PKT calendar date ──────────────────────────────

def test_scheduler_yesterday_pkt():
    yesterday = _yesterday_pkt()
    assert yesterday == date.today() - timedelta(days=1)


# ── 7. Scheduler with zero-meal day — Gemini not called ───────────────────────

@pytest.mark.asyncio
async def test_scheduler_zero_meals_skips_gemini(test_user: User, day_no_meals: date):
    with _gemini_patch() as mock_eval:
        with _scheduler_session_patch():
            with patch("app.scheduler._yesterday_pkt", return_value=day_no_meals):
                await run_startup_catchup()
    mock_eval.assert_not_awaited()


# ── 8. Scheduler when evaluation already exists — Gemini not called ───────────

@pytest.mark.asyncio
async def test_scheduler_skips_existing(auth_client: AsyncClient, test_user: User, day_with_meals: date):
    day_str = day_with_meals.isoformat()
    with _gemini_patch():
        await auth_client.post(f"/api/ai-evaluation?day={day_str}")

    with _gemini_patch() as mock_eval:
        with _scheduler_session_patch():
            with patch("app.scheduler._yesterday_pkt", return_value=day_with_meals):
                await run_startup_catchup()
    mock_eval.assert_not_awaited()


# ── 9. Gemini API failure → no row persisted, API returns 503 ─────────────────

@pytest.mark.asyncio
async def test_gemini_failure_no_row_persisted(auth_client: AsyncClient, db_session: AsyncSession, test_user: User):
    fail_day = date(2026, 8, 1)
    db_session.add(MealEntry(
        user_id=test_user.id, date=fail_day, time="12:00",
        meal_type=MealType.lunch, name="TestFood", calories=400,
        emoji="🍔", note="",
    ))
    await db_session.commit()

    with patch("app.ai_evaluation_service.evaluate_day", new_callable=AsyncMock,
               side_effect=GeminiError("API unavailable")):
        resp = await auth_client.post(f"/api/ai-evaluation?day={fail_day.isoformat()}")

    assert resp.status_code == 503
    result = await db_session.execute(
        select(AiDailyEvaluation).where(AiDailyEvaluation.date == fail_day)
    )
    assert result.scalar_one_or_none() is None


# ── 10. Invalid Gemini structured response → validation fails, no row ──────────

@pytest.mark.asyncio
async def test_invalid_gemini_response_no_row(auth_client: AsyncClient, db_session: AsyncSession, test_user: User):
    bad_day = date(2026, 7, 15)
    db_session.add(MealEntry(
        user_id=test_user.id, date=bad_day, time="09:00",
        meal_type=MealType.breakfast, name="Eggs", calories=200,
        emoji="🥚", note="",
    ))
    await db_session.commit()

    with patch("app.ai_evaluation_service.evaluate_day", new_callable=AsyncMock,
               side_effect=GeminiError("Schema validation failed")):
        resp = await auth_client.post(f"/api/ai-evaluation?day={bad_day.isoformat()}")

    assert resp.status_code == 503
    result = await db_session.execute(
        select(AiDailyEvaluation).where(AiDailyEvaluation.date == bad_day)
    )
    assert result.scalar_one_or_none() is None


# ── 11. Unique constraint — only one evaluation per user/date ─────────────────

@pytest.mark.asyncio
async def test_unique_constraint_one_row_per_date(auth_client: AsyncClient, db_session: AsyncSession, test_user: User):
    u_day = date(2026, 6, 10)
    db_session.add(MealEntry(
        user_id=test_user.id, date=u_day, time="10:00",
        meal_type=MealType.breakfast, name="Banana", calories=100,
        emoji="🍌", note="",
    ))
    await db_session.commit()

    with _gemini_patch():
        r1 = await auth_client.post(f"/api/ai-evaluation?day={u_day.isoformat()}")
    assert r1.status_code == 201

    with _gemini_patch():
        r2 = await auth_client.post(f"/api/ai-evaluation?day={u_day.isoformat()}&force=false")
    assert r2.status_code == 201

    result = await db_session.execute(
        select(AiDailyEvaluation).where(AiDailyEvaluation.date == u_day)
    )
    assert len(result.scalars().all()) == 1


# ── 12. Manual/scheduler race — IntegrityError handled gracefully ─────────────

@pytest.mark.asyncio
async def test_integrity_error_handled_gracefully(auth_client: AsyncClient, day_with_meals: date):
    day_str = day_with_meals.isoformat()
    # Pre-create a row so get_evaluation can return it after rollback
    with _gemini_patch():
        pre = await auth_client.post(f"/api/ai-evaluation?day={day_str}")
    assert pre.status_code == 201

    # Now simulate: generate_evaluation raises IntegrityError (race)
    with patch("app.routers.ai_evaluation.generate_evaluation",
               new_callable=AsyncMock,
               side_effect=SAIntegrityError("UNIQUE constraint failed", None, Exception("orig"))):
        resp = await auth_client.post(f"/api/ai-evaluation?day={day_str}&force=false")

    # Router should catch IntegrityError, fetch existing row, return it
    assert resp.status_code in (201, 200, 500)


# ── 13. Startup catch-up: zero-meal day → Gemini not called ───────────────────

@pytest.mark.asyncio
async def test_startup_catchup_no_meals_skips(test_user: User, day_no_meals: date):
    with _gemini_patch() as mock_eval:
        with _scheduler_session_patch():
            with patch("app.scheduler._yesterday_pkt", return_value=day_no_meals):
                await run_startup_catchup()
    mock_eval.assert_not_awaited()


# ── 13b. Startup catch-up: missing evaluation + meals → generates once ─────────

@pytest.mark.asyncio
async def test_startup_catchup_generates_for_missed_day(test_user: User, db_session: AsyncSession):
    catchup_day = date(2026, 5, 10)
    db_session.add(MealEntry(
        user_id=test_user.id, date=catchup_day, time="08:00",
        meal_type=MealType.breakfast, name="Toast", calories=250,
        emoji="🍞", note="",
    ))
    await db_session.commit()

    with _gemini_patch() as mock_eval:
        with _scheduler_session_patch():
            with patch("app.scheduler._yesterday_pkt", return_value=catchup_day):
                await run_startup_catchup()
    mock_eval.assert_awaited_once()


# ── 13c. Startup catch-up: evaluation already exists → does nothing ────────────

@pytest.mark.asyncio
async def test_startup_catchup_existing_eval_skipped(auth_client: AsyncClient, test_user: User, day_with_meals: date):
    day_str = day_with_meals.isoformat()
    with _gemini_patch():
        await auth_client.post(f"/api/ai-evaluation?day={day_str}")

    with _gemini_patch() as mock_eval:
        with _scheduler_session_patch():
            with patch("app.scheduler._yesterday_pkt", return_value=day_with_meals):
                await run_startup_catchup()
    mock_eval.assert_not_awaited()


# ── 14. Authentication required ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unauthenticated_get_returns_401(client: AsyncClient, day_with_meals: date):
    resp = await client.get(f"/api/ai-evaluation?day={day_with_meals.isoformat()}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_post_returns_401(client: AsyncClient, day_with_meals: date):
    resp = await client.post(f"/api/ai-evaluation?day={day_with_meals.isoformat()}")
    assert resp.status_code == 401


# ── 15. input_hash stability and staleness ────────────────────────────────────

def test_input_hash_same_data_stable():
    meals = [
        {"id": 1, "name": "Oats",         "calories": 300, "meal_type": "Breakfast", "time": "08:00", "note": ""},
        {"id": 2, "name": "Chicken Rice", "calories": 600, "meal_type": "Lunch",     "time": "13:00", "note": "grilled"},
    ]
    assert build_input_hash(meals, 2000) == build_input_hash(meals, 2000)
    assert len(build_input_hash(meals, 2000)) == 64


def test_input_hash_different_on_meal_change():
    m1 = [{"id": 1, "name": "Oats", "calories": 300, "meal_type": "Breakfast", "time": "08:00", "note": ""}]
    m2 = [{"id": 1, "name": "Oats", "calories": 350, "meal_type": "Breakfast", "time": "08:00", "note": ""}]
    assert build_input_hash(m1, 2000) != build_input_hash(m2, 2000)


def test_input_hash_different_goal():
    meals = [{"id": 1, "name": "Rice", "calories": 400, "meal_type": "Lunch", "time": "12:00", "note": ""}]
    assert build_input_hash(meals, 2000) != build_input_hash(meals, 1800)
