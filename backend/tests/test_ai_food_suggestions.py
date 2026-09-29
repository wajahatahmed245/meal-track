"""
Tests for AI Food Suggestions endpoints.
Gemini is mocked — no real API calls made.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models import AiFoodSuggestionSession, AiFoodSuggestionUsage, MealEntry, MealType

PKT = timezone(timedelta(hours=5))
TODAY_PKT = datetime.now(PKT).date()

MOCK_SUGGESTIONS_RAW = [
    {
        "name": "Chicken Tikka + Roti",
        "description": "1 piece chicken tikka with 1 chapati",
        "estimated_calories": 420,
        "estimated_price_min_pkr": 350,
        "estimated_price_max_pkr": 500,
        "category_tag": "budget",
        "notes": "Good protein source.",
    },
    {
        "name": "2 Boiled Eggs + Brown Bread + Dahi",
        "description": "2 boiled eggs, 2 slices brown bread, cup of dahi",
        "estimated_calories": 360,
        "estimated_price_min_pkr": 200,
        "estimated_price_max_pkr": 320,
        "category_tag": "balanced",
        "notes": "Budget-friendly, high-protein.",
    },
    {
        "name": "Seekh Kebab Meal",
        "description": "2 seekh kebabs with salad and mint chutney",
        "estimated_calories": 450,
        "estimated_price_min_pkr": 400,
        "estimated_price_max_pkr": 600,
        "category_tag": "restaurant",
        "notes": "Available at local BBQ restaurants.",
    },
    {
        "name": "Lassi + Fruit Chaat",
        "description": "Plain lassi and a small cup of fruit chaat",
        "estimated_calories": 220,
        "estimated_price_min_pkr": 150,
        "estimated_price_max_pkr": 250,
        "category_tag": "snack",
        "notes": "Light and refreshing.",
    },
    {
        "name": "Grilled Chicken Breast + Salad",
        "description": "150g grilled chicken with green salad",
        "estimated_calories": 330,
        "estimated_price_min_pkr": 450,
        "estimated_price_max_pkr": 600,
        "category_tag": "protein",
        "notes": "High protein, low fat.",
    },
]


@pytest.fixture
def mock_gemini():
    """Patch _call_gemini so tests never hit the real API."""
    with patch("app.routers.ai_food_suggestions.settings") as mock_settings, \
         patch("app.routers.ai_food_suggestions._call_gemini") as mock_call:
        mock_settings.gemini_api_key = "test-key"
        mock_settings.gemini_model = "gemini-flash-lite-latest"
        mock_call.return_value = MOCK_SUGGESTIONS_RAW
        yield mock_call


# ── 1. Usage starts at zero ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_usage_returns_zero_initially(auth_client: AsyncClient):
    resp = await auth_client.get("/api/ai-food-suggestions/usage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["requests_used_today"] == 0
    assert data["requests_limit"] == 5
    assert data["remaining_requests"] == 5
    assert "date" in data


# ── 2. Generate returns exactly 5 suggestions ────────────────────────────────

@pytest.mark.asyncio
async def test_generate_returns_five_suggestions(auth_client: AsyncClient, mock_gemini):
    resp = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code == 200
    data = resp.json()
    assert "session" in data
    assert len(data["session"]["items"]) == 5
    assert data["requests_limit"] == 5


# ── 3. Response structure is correct ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_response_structure(auth_client: AsyncClient, mock_gemini):
    resp = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code == 200
    data = resp.json()

    assert "session" in data
    assert "requests_used_today" in data
    assert "requests_limit" in data

    sess = data["session"]
    assert "id" in sess
    assert "date" in sess
    assert "generated_at" in sess
    assert "daily_goal_snapshot" in sess
    assert "consumed_snapshot" in sess
    assert "remaining_snapshot" in sess
    assert "request_number" in sess

    for item in sess["items"]:
        assert "name" in item
        assert "description" in item
        assert "estimated_calories" in item
        assert "price_min_pkr" in item
        assert "price_max_pkr" in item
        assert "calories_after" in item
        assert "category_tag" in item
        assert item["estimated_calories"] >= 0


# ── 4. Usage counter increments after each successful generation ──────────────

@pytest.mark.asyncio
async def test_generate_increments_usage(auth_client: AsyncClient, mock_gemini):
    resp1 = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp1.status_code == 200
    count_after_1 = resp1.json()["requests_used_today"]

    resp2 = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp2.status_code == 200
    count_after_2 = resp2.json()["requests_used_today"]

    assert count_after_2 == count_after_1 + 1


# ── 5. GET /usage reflects previous generates ────────────────────────────────

@pytest.mark.asyncio
async def test_usage_endpoint_reflects_requests(
    auth_client: AsyncClient, db_session, test_user, mock_gemini
):
    await auth_client.post("/api/ai-food-suggestions/generate")
    await auth_client.post("/api/ai-food-suggestions/generate")

    resp = await auth_client.get("/api/ai-food-suggestions/usage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["requests_used_today"] >= 2
    assert data["remaining_requests"] == max(0, 5 - data["requests_used_today"])


# ── 6. Daily limit is enforced ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_respects_daily_limit(
    auth_client: AsyncClient, db_session, test_user, mock_gemini
):
    """Sixth request must return 429."""
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    stmt = sqlite_insert(AiFoodSuggestionUsage).values(
        user_id=test_user.id, date=TODAY_PKT, request_count=5
    ).on_conflict_do_update(
        index_elements=["user_id", "date"],
        set_={"request_count": 5},
    )
    await db_session.execute(stmt)
    await db_session.commit()

    resp = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code == 429
    assert "limit" in resp.json()["detail"].lower()


# ── 7. Item calories never exceed remaining budget ────────────────────────────

@pytest.mark.asyncio
async def test_suggestions_calories_do_not_exceed_remaining(
    auth_client: AsyncClient, mock_gemini
):
    resp = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code == 200
    sess = resp.json()["session"]
    remaining = sess["remaining_snapshot"]
    for item in sess["items"]:
        assert item["estimated_calories"] <= remaining, (
            f"Item '{item['name']}' has {item['estimated_calories']} kcal "
            f"but remaining snapshot is only {remaining} kcal"
        )


# ── 8. Unauthenticated /usage returns 401/403 ────────────────────────────────

@pytest.mark.asyncio
async def test_get_usage_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/ai-food-suggestions/usage")
    assert resp.status_code in (401, 403)


# ── 9. Unauthenticated /generate returns 401/403 ─────────────────────────────

@pytest.mark.asyncio
async def test_generate_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code in (401, 403)


# ── 10. Session is persisted in DB after generation ──────────────────────────

@pytest.mark.asyncio
async def test_session_persisted_in_db(
    auth_client: AsyncClient, db_session, test_user, mock_gemini
):
    resp = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code == 200
    session_id = resp.json()["session"]["id"]

    from sqlalchemy.orm import selectinload
    result = await db_session.execute(
        select(AiFoodSuggestionSession)
        .options(selectinload(AiFoodSuggestionSession.items))
        .where(AiFoodSuggestionSession.id == session_id)
    )
    db_sess = result.scalar_one_or_none()
    assert db_sess is not None
    assert db_sess.user_id == test_user.id
    assert len(db_sess.items) == 5
    # Snapshot values must be frozen
    assert db_sess.daily_goal_snapshot > 0
    assert db_sess.consumed_snapshot >= 0
    assert db_sess.remaining_snapshot >= 0


# ── 11. GET /sessions/today returns all sessions for today ────────────────────

@pytest.mark.asyncio
async def test_get_today_sessions_returns_all(
    auth_client: AsyncClient, mock_gemini
):
    await auth_client.post("/api/ai-food-suggestions/generate")
    await auth_client.post("/api/ai-food-suggestions/generate")

    resp = await auth_client.get("/api/ai-food-suggestions/sessions/today")
    assert resp.status_code == 200
    data = resp.json()
    assert "sessions" in data
    assert "requests_used_today" in data
    assert len(data["sessions"]) >= 2
    # Most recent first
    if len(data["sessions"]) >= 2:
        assert data["sessions"][0]["generated_at"] >= data["sessions"][1]["generated_at"]


# ── 12. GET /sessions/latest returns most recent session ─────────────────────

@pytest.mark.asyncio
async def test_get_latest_session(auth_client: AsyncClient, mock_gemini):
    resp1 = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp1.status_code == 200
    latest_id = resp1.json()["session"]["id"]

    # Second generation should become the new latest
    resp2 = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp2.status_code == 200
    newer_id = resp2.json()["session"]["id"]

    resp_latest = await auth_client.get("/api/ai-food-suggestions/sessions/latest")
    assert resp_latest.status_code == 200
    assert resp_latest.json()["id"] == newer_id
    assert newer_id != latest_id
