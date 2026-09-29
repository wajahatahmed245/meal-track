"""
Tests for dashboard date-rollover correctness.

Verifies that /api/summary/today always returns the current PKT calendar date,
not the UTC date, so the dashboard rolls over at midnight PKT rather than
midnight UTC (which would be 5 AM PKT).

Patch target: app.routers.summary.today_pkt
"""
from datetime import date
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.models import MealEntry, MealType


# ── Helpers ───────────────────────────────────────────────────────────────────

SEP_29 = date(2026, 9, 29)
SEP_30 = date(2026, 9, 30)


def _patch_today(d: date):
    return patch("app.routers.summary.today_pkt", return_value=d)


async def _insert_meal(db_session, test_user, target_date, name="Test Meal", calories=500):
    meal = MealEntry(
        user_id=test_user.id,
        date=target_date,
        time="12:00",
        meal_type=MealType.lunch,
        name=name,
        calories=calories,
        emoji="🍚",
        note="",
    )
    db_session.add(meal)
    await db_session.commit()
    return meal


# ── Test 1: /today returns Sep 29 data at 23:59 PKT ──────────────────────────

@pytest.mark.asyncio
async def test_today_returns_correct_date_at_2359_pkt(
    auth_client: AsyncClient, db_session, test_user
):
    await _insert_meal(db_session, test_user, SEP_29, "Late Night Snack", 300)

    with _patch_today(SEP_29):
        resp = await auth_client.get("/api/summary/today")

    assert resp.status_code == 200
    data = resp.json()
    assert data["date"] == "2026-09-29"
    assert data["total_calories"] == 300
    assert any(m["name"] == "Late Night Snack" for m in data["meals"])


# ── Test 2: /today returns Sep 30 at exactly midnight PKT ────────────────────

@pytest.mark.asyncio
async def test_today_rolls_over_to_sep30_at_midnight_pkt(
    auth_client: AsyncClient, db_session, test_user
):
    # Insert a meal on Sep 29 — it must NOT appear on Sep 30
    await _insert_meal(db_session, test_user, SEP_29, "Sep 29 Lunch", 700)

    with _patch_today(SEP_30):
        resp = await auth_client.get("/api/summary/today")

    assert resp.status_code == 200
    data = resp.json()
    assert data["date"] == "2026-09-30", "At midnight PKT, date must flip to Sep 30"
    assert data["total_calories"] == 0
    assert data["meals"] == []


# ── Test 3: Sep 30 dashboard shows empty state when no meals logged ──────────

@pytest.mark.asyncio
async def test_today_is_empty_when_no_meals_on_new_day(
    auth_client: AsyncClient, db_session, test_user
):
    with _patch_today(SEP_30):
        resp = await auth_client.get("/api/summary/today")

    assert resp.status_code == 200
    data = resp.json()
    assert data["date"] == "2026-09-30"
    assert data["meals"] == []
    assert data["total_calories"] == 0
    assert data["meals_logged"] == 0


# ── Test 4: Sep 29 meals remain accessible through /day endpoint ─────────────

@pytest.mark.asyncio
async def test_sep29_meals_accessible_via_day_endpoint(
    auth_client: AsyncClient, db_session, test_user
):
    await _insert_meal(db_session, test_user, SEP_29, "History Meal", 650)

    # /today shows Sep 30 (new day)
    with _patch_today(SEP_30):
        today_resp = await auth_client.get("/api/summary/today")
    assert today_resp.json()["date"] == "2026-09-30"
    assert today_resp.json()["total_calories"] == 0

    # /day?day=2026-09-29 still returns Sep 29 data
    hist_resp = await auth_client.get("/api/summary/day?day=2026-09-29")
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert hist["date"] == "2026-09-29"
    assert any(m["name"] == "History Meal" for m in hist["meals"])


# ── Test 5: Sep 29 meals do NOT bleed into Sep 30 today summary ──────────────

@pytest.mark.asyncio
async def test_sep29_meals_do_not_appear_in_sep30_summary(
    auth_client: AsyncClient, db_session, test_user
):
    await _insert_meal(db_session, test_user, SEP_29, "Biryani", 800)
    await _insert_meal(db_session, test_user, SEP_29, "Lassi",  150)

    with _patch_today(SEP_30):
        resp = await auth_client.get("/api/summary/today")

    assert resp.status_code == 200
    names = [m["name"] for m in resp.json()["meals"]]
    assert "Biryani" not in names
    assert "Lassi"   not in names
    assert resp.json()["total_calories"] == 0


# ── Test 6: adding a meal without explicit date uses PKT today ────────────────

@pytest.mark.asyncio
async def test_add_meal_without_date_uses_pkt_today(
    auth_client: AsyncClient, db_session, test_user
):
    with patch("app.routers.meals.today_pkt", return_value=SEP_30):
        resp = await auth_client.post("/api/meals", json={
            "time": "09:00",
            "meal_type": "Breakfast",
            "name": "PKT Breakfast",
            "calories": 400,
        })

    assert resp.status_code == 201
    assert resp.json()["date"] == "2026-09-30"


# ── Test 7: weekly summary respects PKT today (is_today flag) ────────────────

@pytest.mark.asyncio
async def test_weekly_summary_is_today_flag_uses_pkt(
    auth_client: AsyncClient, db_session, test_user
):
    with _patch_today(SEP_30):
        resp = await auth_client.get("/api/summary/weekly")

    assert resp.status_code == 200
    days = resp.json()["days"]
    today_days = [d for d in days if d["is_today"]]
    assert len(today_days) == 1
    assert today_days[0]["date"] == "2026-09-30"
