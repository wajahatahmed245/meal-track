"""
Test fixtures — shared in-memory SQLite via StaticPool, per-test data cleanup.
"""
import asyncio
from datetime import date

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import AiDailyEvaluation, AiFoodSuggestionUsage, MealEntry, MealType, User
from app.schemas import GeminiEvaluationResult, MealEvaluationItem
from app.security import hash_password

# StaticPool = single underlying connection so all sessions share the same in-memory DB
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
engine_test = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = async_sessionmaker(engine_test, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="session")
async def test_user() -> User:
    """Single user created once for the whole session."""
    async with TestSession() as s:
        user = User(
            name="Test User",
            email="test@example.com",
            hashed_password=hash_password("testpass"),
            calorie_goal=2000,
            water_goal_ml=2500,
            exercise_goal_days=5,
        )
        s.add(user)
        await s.commit()
        await s.refresh(user)
        return user


@pytest_asyncio.fixture
async def db_session(test_user) -> AsyncSession:
    """
    Per-test session. Deletes all evaluation and meal rows (not user)
    after each test to keep tests isolated.
    """
    async with TestSession() as session:
        yield session
        # Clean up per-test data
        from sqlalchemy import delete
        await session.execute(delete(AiDailyEvaluation))
        await session.execute(delete(AiFoodSuggestionUsage))
        await session.execute(delete(MealEntry))
        await session.commit()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    resp = await client.post("/api/auth/login", json={"email": "test@example.com", "password": "testpass"})
    assert resp.status_code == 200, resp.text
    client.headers.update({"Authorization": f"Bearer {resp.json()['access_token']}"})
    return client


@pytest_asyncio.fixture
async def day_with_meals(db_session: AsyncSession, test_user: User) -> date:
    target = date(2026, 9, 27)
    db_session.add(MealEntry(
        user_id=test_user.id, date=target, time="08:00",
        meal_type=MealType.breakfast, name="Oats", calories=300,
        emoji="🥣", note="",
    ))
    db_session.add(MealEntry(
        user_id=test_user.id, date=target, time="13:00",
        meal_type=MealType.lunch, name="Chicken Rice", calories=600,
        emoji="🍚", note="grilled",
    ))
    await db_session.commit()
    return target


@pytest_asyncio.fixture
def day_no_meals() -> date:
    return date(2026, 9, 1)


def mock_gemini_result() -> GeminiEvaluationResult:
    return GeminiEvaluationResult(
        overall_score=7,
        overall_assessment="A solid day overall with good protein sources.",
        what_went_well=["Good protein intake", "Reasonable calorie balance"],
        things_to_watch=["Could add more vegetables"],
        meal_evaluations=[
            MealEvaluationItem(
                food_name="Oats",
                meal_type="Breakfast",
                time="08:00",
                logged_calories=300,
                assessment="Good fibre source.",
                likely_benefits=["Sustained energy"],
                things_to_watch=[],
            ),
            MealEvaluationItem(
                food_name="Chicken Rice",
                meal_type="Lunch",
                time="13:00",
                logged_calories=600,
                assessment="Good protein, moderate calories.",
                likely_benefits=["Protein for muscle repair"],
                things_to_watch=["Portion size"],
            ),
        ],
        daily_benefits=["Adequate protein", "Moderate calorie intake"],
        daily_concerns=["Low vegetable variety"],
        improve_tomorrow=["Add a salad or vegetables"],
        reduce_or_avoid_repeating_tomorrow=["Consider varying carb sources"],
        final_recommendation="Good day — add more vegetables tomorrow.",
        confidence="Medium",
    )
