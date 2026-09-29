"""
Tests for AI Food Suggestions endpoints.
Gemini is mocked — no real API calls made.

Key behavioural invariants tested:
- 5 suggestions per generation
- Each suggestion targets ~85-100% of remaining (not tiny random amounts)
- Each suggestion calories <= remaining
- Components list is stored and returned
- Usage counter increments correctly
- Daily limit enforced
- Session persisted in DB
- Retry fires when suggestions are chronically under-utilised
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, call

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models import AiFoodSuggestionSession, AiFoodSuggestionUsage, MealEntry, MealType
from app.routers.ai_food_suggestions import _is_poor, _poor_count

PKT = timezone(timedelta(hours=5))
TODAY_PKT = datetime.now(PKT).date()

# ── Mock raw suggestions (good — close to a 550 kcal budget) ──────────────────

def _make_suggestions(remaining: int = 550) -> list[dict]:
    """Build 5 mock suggestions that each target ~90% of `remaining`."""
    target = int(remaining * 0.90)
    return [
        {
            "name": "Chicken Tikka Meal",
            "components": [
                {"item": "Chicken tikka", "calories": int(target * 0.53)},
                {"item": "1 chapati",      "calories": int(target * 0.24)},
                {"item": "Raita",          "calories": int(target * 0.14)},
                {"item": "Salad",          "calories": int(target * 0.09)},
            ],
            "estimated_calories": target,
            "estimated_price_min_pkr": 400,
            "estimated_price_max_pkr": 550,
            "category_tag": "restaurant",
            "notes": "Good protein source.",
        },
        {
            "name": "Seekh Kebab Meal",
            "components": [
                {"item": "2 seekh kebabs",     "calories": int(target * 0.62)},
                {"item": "Small rice portion", "calories": int(target * 0.31)},
                {"item": "Salad",              "calories": int(target * 0.07)},
            ],
            "estimated_calories": target,
            "estimated_price_min_pkr": 450,
            "estimated_price_max_pkr": 600,
            "category_tag": "balanced",
            "notes": "Available at BBQ restaurants.",
        },
        {
            "name": "Egg & Toast Combo",
            "components": [
                {"item": "2 boiled eggs", "calories": int(target * 0.39)},
                {"item": "2 brown toast", "calories": int(target * 0.30)},
                {"item": "Dahi 1 cup",    "calories": int(target * 0.20)},
                {"item": "Banana",        "calories": int(target * 0.11)},
            ],
            "estimated_calories": target,
            "estimated_price_min_pkr": 200,
            "estimated_price_max_pkr": 320,
            "category_tag": "budget",
            "notes": "Budget-friendly, high-protein.",
        },
        {
            "name": "Grilled Chicken Sandwich",
            "components": [
                {"item": "Grilled chicken breast", "calories": int(target * 0.55)},
                {"item": "Sandwich bun",           "calories": int(target * 0.25)},
                {"item": "Dahi sauce",             "calories": int(target * 0.20)},
            ],
            "estimated_calories": target,
            "estimated_price_min_pkr": 350,
            "estimated_price_max_pkr": 500,
            "category_tag": "snack",
            "notes": "High protein.",
        },
        {
            "name": "Daal Chawal",
            "components": [
                {"item": "Daal makhani 1 cup", "calories": int(target * 0.50)},
                {"item": "Rice 1 cup",         "calories": int(target * 0.38)},
                {"item": "Raita",              "calories": int(target * 0.12)},
            ],
            "estimated_calories": target,
            "estimated_price_min_pkr": 250,
            "estimated_price_max_pkr": 380,
            "category_tag": "protein",
            "notes": "Classic desi combination.",
        },
    ]


# Target 2000 kcal — test user has no meals pre-loaded so remaining == daily_goal == 2000
MOCK_SUGGESTIONS_RAW = _make_suggestions(2000)

# Under-utilised mock — each suggestion ~27% of a 550 kcal budget
MOCK_SUGGESTIONS_POOR = [
    {
        "name": "Apple",
        "components": [{"item": "Apple", "calories": 150}],
        "estimated_calories": 150,
        "estimated_price_min_pkr": 50,
        "estimated_price_max_pkr": 80,
        "category_tag": "snack",
        "notes": "Light snack.",
    }
] * 5


@pytest.fixture
def mock_gemini():
    """Patch _call_gemini so tests never hit the real API."""
    with patch("app.routers.ai_food_suggestions.settings") as mock_settings, \
         patch("app.routers.ai_food_suggestions._call_gemini") as mock_call:
        mock_settings.gemini_api_key = "test-key"
        mock_settings.gemini_model = "gemini-flash-lite-latest"
        mock_call.return_value = MOCK_SUGGESTIONS_RAW
        yield mock_call


@pytest.fixture
def mock_gemini_poor_then_good():
    """First call returns under-utilised suggestions; second call returns good ones."""
    good = _make_suggestions(2000)  # test user has no meals → remaining == 2000
    with patch("app.routers.ai_food_suggestions.settings") as mock_settings, \
         patch("app.routers.ai_food_suggestions._call_gemini") as mock_call:
        mock_settings.gemini_api_key = "test-key"
        mock_settings.gemini_model = "gemini-flash-lite-latest"
        mock_call.side_effect = [MOCK_SUGGESTIONS_POOR, good]
        yield mock_call


# ── Unit tests for utilisation helpers ───────────────────────────────────────

def test_is_poor_above_floor():
    # 150 kcal when 550 remain → 27% < 65% threshold → poor
    assert _is_poor(150, 550) is True

def test_is_poor_good_utilisation():
    # 490 kcal when 550 remain → 89% > 65% → not poor
    assert _is_poor(490, 550) is False

def test_is_poor_below_floor():
    # Even tiny amount is fine when only 80 kcal remain
    assert _is_poor(50, 80) is False

def test_poor_count_all_good():
    good = _make_suggestions(550)
    assert _poor_count(good, 550) == 0

def test_poor_count_all_bad():
    assert _poor_count(MOCK_SUGGESTIONS_POOR, 550) == 5


# ── API endpoint tests ────────────────────────────────────────────────────────

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
async def test_generate_returns_five_suggestions(auth_client: AsyncClient, mock_gemini):
    resp = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code == 200
    data = resp.json()
    assert "session" in data
    assert len(data["session"]["items"]) == 5
    assert data["requests_limit"] == 5


@pytest.mark.asyncio
async def test_generate_response_structure(auth_client: AsyncClient, mock_gemini):
    resp = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code == 200
    data = resp.json()

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
        assert "estimated_calories" in item
        assert "price_min_pkr" in item
        assert "price_max_pkr" in item
        assert "calories_after" in item
        assert "category_tag" in item
        assert "components" in item
        assert isinstance(item["components"], list)
        assert item["estimated_calories"] >= 0


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
    await auth_client.post("/api/ai-food-suggestions/generate")
    await auth_client.post("/api/ai-food-suggestions/generate")

    resp = await auth_client.get("/api/ai-food-suggestions/usage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["requests_used_today"] >= 2
    assert data["remaining_requests"] == max(0, 5 - data["requests_used_today"])


@pytest.mark.asyncio
async def test_generate_respects_daily_limit(
    auth_client: AsyncClient, db_session, test_user, mock_gemini
):
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
    auth_client: AsyncClient, mock_gemini
):
    resp = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code == 200
    sess = resp.json()["session"]
    remaining = sess["remaining_snapshot"]
    for item in sess["items"]:
        assert item["estimated_calories"] <= remaining, (
            f"'{item['name']}': {item['estimated_calories']} kcal > remaining {remaining} kcal"
        )


@pytest.mark.asyncio
async def test_get_usage_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/ai-food-suggestions/usage")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_generate_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code in (401, 403)


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
    assert db_sess.daily_goal_snapshot > 0


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
    assert len(data["sessions"]) >= 2
    if len(data["sessions"]) >= 2:
        assert data["sessions"][0]["generated_at"] >= data["sessions"][1]["generated_at"]


@pytest.mark.asyncio
async def test_get_latest_session(auth_client: AsyncClient, mock_gemini):
    resp1 = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp1.status_code == 200

    resp2 = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp2.status_code == 200
    newer_id = resp2.json()["session"]["id"]

    resp_latest = await auth_client.get("/api/ai-food-suggestions/sessions/latest")
    assert resp_latest.status_code == 200
    assert resp_latest.json()["id"] == newer_id


# ── Target-utilisation tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_suggestions_target_close_to_remaining(
    auth_client: AsyncClient, mock_gemini
):
    """Each suggestion should use >= 65% of remaining (good suggestions mock)."""
    resp = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code == 200
    sess = resp.json()["session"]
    remaining = sess["remaining_snapshot"]
    if remaining > 120:
        for item in sess["items"]:
            pct = item["estimated_calories"] / remaining
            assert pct >= 0.65, (
                f"'{item['name']}' uses only {pct:.0%} of {remaining} kcal remaining"
            )


@pytest.mark.asyncio
async def test_components_are_stored_and_returned(
    auth_client: AsyncClient, mock_gemini
):
    """Components list must be non-empty and each component must have item+calories."""
    resp = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code == 200
    for item in resp.json()["session"]["items"]:
        assert len(item["components"]) > 0, f"'{item['name']}' has no components"
        for comp in item["components"]:
            assert "item" in comp
            assert "calories" in comp
            assert comp["calories"] >= 0


@pytest.mark.asyncio
async def test_retry_fires_on_poor_suggestions(
    auth_client: AsyncClient, mock_gemini_poor_then_good
):
    """
    When first Gemini call returns chronically under-utilised suggestions,
    _call_gemini should be invoked a second time (free retry), and the
    better result should be used.
    """
    resp = await auth_client.post("/api/ai-food-suggestions/generate")
    assert resp.status_code == 200

    # Verify _call_gemini was called twice
    assert mock_gemini_poor_then_good.call_count == 2, (
        f"Expected 2 calls (original + retry), got {mock_gemini_poor_then_good.call_count}"
    )

    # The saved suggestions should be from the good (second) call
    sess = resp.json()["session"]
    remaining = sess["remaining_snapshot"]
    if remaining > 120:
        for item in sess["items"]:
            pct = item["estimated_calories"] / remaining
            assert pct >= 0.65, (
                f"After retry, '{item['name']}' still only uses {pct:.0%}"
            )


@pytest.mark.asyncio
async def test_retry_does_not_double_increment_usage(
    auth_client: AsyncClient, mock_gemini_poor_then_good
):
    """A retry must not count as an extra daily request."""
    before_resp = await auth_client.get("/api/ai-food-suggestions/usage")
    before = before_resp.json()["requests_used_today"]

    await auth_client.post("/api/ai-food-suggestions/generate")

    after_resp = await auth_client.get("/api/ai-food-suggestions/usage")
    after = after_resp.json()["requests_used_today"]

    assert after == before + 1, "Retry must not double-count usage"
