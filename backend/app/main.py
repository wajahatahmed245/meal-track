from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import get_db, init_db
from .routers import auth, drinks, exercise, food, meals, summary, user
from .seed import seed_default_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async for db in get_db():
        await seed_default_user(db)
        break
    yield


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


@app.get("/api/health")
async def health():
    return {"status": "ok"}
