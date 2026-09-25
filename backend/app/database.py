from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Inline migration for existing deployments.
        # SQLite ALTER TABLE ADD COLUMN does not support UNIQUE — add the
        # unique constraint as a partial index instead (NULL rows are excluded).
        for stmt in (
            "ALTER TABLE exercise_logs ADD COLUMN source_id TEXT",
            "ALTER TABLE exercise_logs ADD COLUMN source_type TEXT",
            (
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_exercise_logs_source_id "
                "ON exercise_logs(source_id) WHERE source_id IS NOT NULL"
            ),
        ):
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # column / index already exists
