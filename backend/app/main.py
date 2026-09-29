import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .consumer import run_consumer
from .database import get_db, init_db
from .routers import auth, drinks, exercise, food, meals, summary, user
from .routers import ai_evaluation, ai_food_suggestions
from .scheduler import create_scheduler, run_startup_catchup
from .seed import seed_default_user

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async for db in get_db():
        await seed_default_user(db)
        break

    # Redis consumer — reads exercise events from gym_tracker
    consumer_task = asyncio.create_task(run_consumer(), name="exercise-consumer")
    logger.info("Exercise event consumer started")

    # Startup catch-up: generate evaluation for yesterday if missed
    await run_startup_catchup()

    # Daily scheduler — fires at 01:00 Asia/Karachi
    # WARNING: in-process scheduler tied to a single uvicorn worker.
    # If production later uses multiple workers or replicas, move to an
    # external scheduler or protect with a distributed lock.
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("APScheduler started — daily evaluation at 01:00 Asia/Karachi")

    yield

    scheduler.shutdown(wait=False)
    logger.info("APScheduler stopped")

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    logger.info("Exercise event consumer stopped")


app = FastAPI(title="MealTrack API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(meals.router)
app.include_router(drinks.router)
app.include_router(exercise.router)
app.include_router(summary.router)
app.include_router(food.router)
app.include_router(ai_evaluation.router)
app.include_router(ai_food_suggestions.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
