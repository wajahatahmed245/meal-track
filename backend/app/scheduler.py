"""
APScheduler — daily AI evaluation at 01:00 Asia/Karachi.

WARNING: This is an in-process scheduler tied to a single uvicorn worker.
If production later moves to multiple uvicorn workers or multiple backend
replicas, this scheduler must be moved to a singleton worker or external
scheduler, or protected by a distributed lock.
"""
import logging
from datetime import date, timedelta
from typing import Optional

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from .ai_evaluation_service import generate_evaluation, get_evaluation
from .config import settings
from .database import AsyncSessionLocal
from .gemini import GeminiError
from .models import User
from .routers.summary import _build_daily

logger = logging.getLogger(__name__)

_PKT = pytz.timezone("Asia/Karachi")


def _yesterday_pkt() -> date:
    return date.today() - timedelta(days=1)


async def _run_scheduled_evaluation(target_date: Optional[date] = None) -> None:
    """
    Core scheduler job. Evaluates the previous PKT calendar day.
    Safe to call at startup for catch-up (pass explicit target_date).
    """
    day = target_date or _yesterday_pkt()
    logger.info("Scheduled evaluation started for %s", day.isoformat())

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            logger.warning("Scheduler: no user found — skipping evaluation for %s", day.isoformat())
            return

        # Check for existing evaluation first
        existing = await get_evaluation(db, user, day)
        if existing:
            logger.info("Scheduler: evaluation already exists for %s — skipping", day.isoformat())
            return

        # Check for zero meals
        summary = await _build_daily(db, user, day)
        if not summary.meals:
            logger.info("Scheduler: zero meals for %s — skipping Gemini call", day.isoformat())
            return

        try:
            await generate_evaluation(
                db=db,
                user=user,
                day=day,
                trigger_source="scheduled",
                force=False,
            )
            logger.info("Scheduled evaluation completed for %s", day.isoformat())
        except ValueError:
            # Zero meals — already logged inside generate_evaluation
            pass
        except GeminiError as exc:
            logger.error("Gemini failure in scheduled job for %s: %s", day.isoformat(), exc)


async def run_startup_catchup() -> None:
    """
    At startup: if yesterday has meals but no evaluation, generate one.
    Idempotent — does nothing if evaluation already exists or no meals.
    """
    day = _yesterday_pkt()
    logger.info("Startup catch-up check for %s", day.isoformat())

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            return

        existing = await get_evaluation(db, user, day)
        if existing:
            logger.info("Startup catch-up: evaluation already exists for %s", day.isoformat())
            return

        summary = await _build_daily(db, user, day)
        if not summary.meals:
            logger.info("Startup catch-up: zero meals for %s — skipping", day.isoformat())
            return

        logger.info("Startup catch-up: triggering missed evaluation for %s", day.isoformat())
        try:
            await generate_evaluation(
                db=db,
                user=user,
                day=day,
                trigger_source="scheduled",
                force=False,
            )
        except (ValueError, GeminiError) as exc:
            logger.error("Startup catch-up failed for %s: %s", day.isoformat(), exc)


def create_scheduler() -> AsyncIOScheduler:
    tz = pytz.timezone(settings.scheduler_timezone)
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(
        _run_scheduled_evaluation,
        trigger=CronTrigger(hour=1, minute=0, timezone=tz),
        id="daily_ai_evaluation",
        name="Daily AI food evaluation",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,  # 1 hour — catches brief downtime windows
    )
    return scheduler
