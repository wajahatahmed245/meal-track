"""
Tests for AI Food Suggestions endpoints.
Gemini is mocked — no real API calls made.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models import AiFoodSuggestionUsage, MealEntry, MealType

PKT = timezone(timedelta(hours=5))
TODAY_PKT = datetime.now(PKT).date()

MOCK_SUGGESTIONS_RAW = [
    {
        "name": "Chicken Tikka + Roti",
        "description": "1 piece chicken tikka with 1 chapati",
        "estimated_calories": 420,
        "estimated_price_min_pkr": 350,
        "estimated_price_max_pkr": 500,
        "notes": "Good protein source. Available at any local dhaba or restaurant.",
    },
    {
        "name": "2 Boiled Eggs + Brown Bread + Dahi",
        "description": "2 boiled eggs, 2 slices brown bread, small cup of dahi",
        "estimated_calories": 360,
        "estimated_price_min_pkr": 200,
        "estimated_price_max_pkr": 320,
        "notes": "Budget-friendly, high-protein option. Easy to make at home.",
    },
    {
        "name": "Seekh Kebab Meal",
        "description": "2 seekh kebabs with salad and mint chutney",
        "estimated_calories": 450,
        "estimated_price_min_pkr": 400,
        "estimated_price_max_pkr": 600,
        "notes": "Available at local BBQ restaurants and food streets.",
    },
]


@pytest.fixture
def mock_gemini():
    """Patch Gemini so tests never hit the real API."""
    import json
    mock_response = AsyncMock()
    mock_response.text = json.dumps({"suggestions": MOCK_SUGGESTIONS_RAW})

    mock_client = AsyncMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    with patch("app.routers.ai_food_suggestions.settings") as mock_settings, \
         patch("app.routers.ai_food_suggestions._call_gemini") as mock_call:
        mock_settings.gemini_api_key = "test-key"
        mock_settings.gemini_model = "gemini-flash-lite-latest"
        mock_call.return_value = MOCK_SUGGESTIONS_RAW
        yield mock_call


@pytest.mark.asyncio
async def test_get_usage_returns_zero_initially(auth_client: AsyncClient):
    resp = await auth_client.get("/api/ai-food-suggestions/usage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["requests_used_today"] == 0
    assert data["requests_limit"] == 5
    assert data["remaining_requests"] == 5
    assert "date" in data


@pytest.mark.asyncio
async def test_generate_returns_three_suggestions(auth_client: AsyncClient, mock_gemini):
    resp = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data
    assert len(data["suggestions"]) == 3
    assert data["requests_limit"] == 5


@pytest.mark.asyncio
async def test_generate_response_structure(auth_client: AsyncClient, mock_gemini):
    resp = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code == 200
    data = resp.json()

    assert "remaining_calories" in data
    assert "daily_goal" in data
    assert "consumed_today" in data
    assert "requests_used_today" in data
    assert "generated_at" in data

    for suggestion in data["suggestions"]:
        assert "name" in suggestion
        assert "description" in suggestion
        assert "estimated_calories" in suggestion
        assert "estimated_price_min_pkr" in suggestion
        assert "estimated_price_max_pkr" in suggestion
        assert suggestion["estimated_calories"] >= 0


@pytest.mark.asyncio
async def test_generate_increments_usage(auth_client: AsyncClient, mock_gemini):
    resp1 = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp1.status_code == 200
    count_after_1 = resp1.json()["requests_used_today"]

    resp2 = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp2.status_code == 200
    count_after_2 = resp2.json()["requests_used_today"]

    assert count_after_2 == count_after_1 + 1


@pytest.mark.asyncio
async def test_usage_endpoint_reflects_requests(
    auth_client: AsyncClient, db_session, test_user, mock_gemini
):
    # Make 2 requests
    await auth_client.post("/api/ai-food-suggestions/generate")
    await auth_client.post("/api/ai-food-suggestions/generate")

    resp = await auth_client.get("/api/ai-food-suggestions/usage")
    assert resp.status_code == 200
    data = resp.json()
    # count is cumulative across all tests in session — just verify it's an int >= 2
    assert data["requests_used_today"] >= 2
    assert data["remaining_requests"] == max(0, 5 - data["requests_used_today"])


@pytest.mark.asyncio
async def test_generate_respects_daily_limit(
    auth_client: AsyncClient, db_session, test_user, mock_gemini
):
    """After 5 requests, the 6th must return 429."""
    # Insert 5 usage rows directly so we don't have to make 5 real requests
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


@pytest.mark.asyncio
async def test_suggestions_calories_do_not_exceed_remaining(
    auth_client: AsyncClient, db_session, test_user, mock_gemini
):
    """Each suggestion must have estimated_calories <= remaining_calories."""
    resp = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code == 200
    data = resp.json()
    remaining = data["remaining_calories"]
    for s in data["suggestions"]:
        assert s["estimated_calories"] <= remaining, (
            f"Suggestion '{s['name']}' has {s['estimated_calories']} kcal "
            f"but remaining is only {remaining} kcal"
        )


@pytest.mark.asyncio
async def test_get_usage_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/ai-food-suggestions/usage")
    assert resp.status_code in (401, 403)  # HTTPBearer raises 401


@pytest.mark.asyncio
async def test_generate_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code in (401, 403)
