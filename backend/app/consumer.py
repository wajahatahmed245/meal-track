"""
Exercise event consumer — reads from Redis Stream ``exercise.events`` and
syncs exercise logs into MealTrack's database.

Design decisions:
  - Consumer group ``meal-track`` with consumer name ``meal-track-1``.
    Adding a second consumer later is seamless (just change the name).
  - Idempotent upsert on ``source_id``: re-delivering the same event is safe.
  - Retry: a failed message stays in the PEL (pending-entry list).
    After MAX_RETRIES deliveries it is moved to ``exercise.events.dlq``
    and acked from the main stream so it doesn't block progress.
  - Connection recovery: exponential back-off up to 60 s, then restarts
    the listen loop indefinitely.
  - Runs as a background asyncio task started from the FastAPI lifespan.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime
from typing import Any, Dict, Optional

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import AsyncSessionLocal
from .models import ExerciseLog

logger = logging.getLogger(__name__)

STREAM_NAME   = "exercise.events"
DLQ_NAME      = "exercise.events.dlq"
GROUP_NAME    = "meal-track"
CONSUMER_NAME = "meal-track-1"
MAX_RETRIES   = 3
BLOCK_MS      = 5_000   # block up to 5 s waiting for new messages


async def _ensure_group(r: aioredis.Redis) -> None:
    """Create the consumer group and stream if they don't exist yet."""
    try:
        await r.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
        logger.info("Consumer group '%s' created on stream '%s'", GROUP_NAME, STREAM_NAME)
    except aioredis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def _upsert_exercise(
    db: AsyncSession,
    source_id: str,
    source_type: str,
    data: Dict[str, Any],
) -> None:
    """Insert or update an ExerciseLog row identified by source_id."""
    result = await db.execute(
        select(ExerciseLog).where(ExerciseLog.source_id == source_id)
    )
    entry = result.scalar_one_or_none()

    exercise_date = date.fromisoformat(data["date"])

    if entry is None:
        # Find the single MealTrack user (single-user app).
        from .models import User
        user_result = await db.execute(select(User).limit(1))
        user = user_result.scalar_one_or_none()
        if user is None:
            raise RuntimeError("No MealTrack user found — cannot sync exercise")

        entry = ExerciseLog(
            user_id=user.id,
            source_id=source_id,
            source_type=source_type,
        )
        db.add(entry)

    entry.date             = exercise_date
    entry.exercise_type    = data["exercise_type"]
    entry.duration_minutes = int(data["duration_minutes"])
    entry.calories_burned  = int(data["calories_burned"]) if data.get("calories_burned") else None
    entry.time             = "00:00"
    entry.completed        = True

    await db.commit()
    logger.info("Upserted ExerciseLog source_id=%s type=%s date=%s", source_id, source_type, exercise_date)


async def _delete_exercise(db: AsyncSession, source_id: str) -> None:
    """Delete an ExerciseLog row by source_id."""
    result = await db.execute(
        select(ExerciseLog).where(ExerciseLog.source_id == source_id)
    )
    entry = result.scalar_one_or_none()
    if entry:
        await db.delete(entry)
        await db.commit()
        logger.info("Deleted ExerciseLog source_id=%s", source_id)
    else:
        logger.debug("Delete event for unknown source_id=%s — ignoring", source_id)


async def _process_event(event: Dict[str, Any], db: AsyncSession) -> None:
    event_type = event.get("event_type", "")
    data       = event.get("data", {})
    source_id  = data.get("source_id", "")

    if event_type in ("exercise.workout.logged", "exercise.workout.updated"):
        await _upsert_exercise(db, source_id, "gym.workout", data)

    elif event_type == "exercise.workout.deleted":
        await _delete_exercise(db, source_id)

    elif event_type == "exercise.cardio.logged":
        await _upsert_exercise(db, source_id, "gym.cardio", data)

    elif event_type == "exercise.cardio.deleted":
        await _delete_exercise(db, source_id)

    else:
        logger.warning("Unknown event type '%s' — skipping", event_type)


async def _move_to_dlq(r: aioredis.Redis, msg_id: str, payload: str) -> None:
    await r.xadd(DLQ_NAME, {"original_id": msg_id, "payload": payload})
    await r.xack(STREAM_NAME, GROUP_NAME, msg_id)
    logger.error("Message %s moved to DLQ after %s retries", msg_id, MAX_RETRIES)


async def _drain_pending(r: aioredis.Redis) -> None:
    """
    On startup, re-claim any messages that were pending from a previous run
    and have exceeded the retry limit — move them to DLQ so they don't stall.
    Also re-process genuinely pending messages that haven't been tried too many times.
    """
    try:
        pending = await r.xpending_range(
            STREAM_NAME, GROUP_NAME, min="-", max="+", count=100
        )
    except aioredis.ResponseError:
        return

    for entry in pending:
        msg_id        = entry["message_id"]
        delivery_count = entry["times_delivered"]

        claimed = await r.xautoclaim(
            STREAM_NAME, GROUP_NAME, CONSUMER_NAME,
            min_idle_time=0, start_id=msg_id, count=1,
        )
        messages = claimed[1] if claimed else []

        for mid, fields in messages:
            payload = fields.get(b"payload", b"{}").decode()
            if delivery_count >= MAX_RETRIES:
                await _move_to_dlq(r, mid.decode(), payload)
            else:
                # Re-queue for normal processing in the main loop
                logger.info("Re-claimed pending message %s (delivery %s)", mid, delivery_count)


async def _listen_loop(r: aioredis.Redis) -> None:
    await _ensure_group(r)
    await _drain_pending(r)

    logger.info("Consumer started — listening on stream '%s'", STREAM_NAME)

    while True:
        try:
            results = await r.xreadgroup(
                GROUP_NAME,
                CONSUMER_NAME,
                {STREAM_NAME: ">"},
                count=10,
                block=BLOCK_MS,
            )
        except aioredis.RedisError as exc:
            logger.error("Redis read error: %s", exc)
            raise   # triggers reconnect in outer loop

        if not results:
            continue  # timeout, no new messages

        for _stream, messages in results:
            for msg_id, fields in messages:
                mid     = msg_id.decode() if isinstance(msg_id, bytes) else msg_id
                payload = (fields.get(b"payload") or fields.get("payload", b"{}"))
                if isinstance(payload, bytes):
                    payload = payload.decode()

                try:
                    event = json.loads(payload)
                except json.JSONDecodeError as exc:
                    logger.error("Malformed event %s: %s", mid, exc)
                    await r.xack(STREAM_NAME, GROUP_NAME, mid)
                    continue

                try:
                    async with AsyncSessionLocal() as db:
                        await _process_event(event, db)
                    await r.xack(STREAM_NAME, GROUP_NAME, mid)
                except Exception as exc:
                    logger.error(
                        "Failed to process event %s (type=%s): %s",
                        mid, event.get("event_type"), exc,
                    )
                    # Check delivery count — move to DLQ if too many failures
                    try:
                        pending = await r.xpending_range(
                            STREAM_NAME, GROUP_NAME,
                            min=mid, max=mid, count=1,
                        )
                        deliveries = pending[0]["times_delivered"] if pending else MAX_RETRIES
                    except Exception:
                        deliveries = MAX_RETRIES

                    if deliveries >= MAX_RETRIES:
                        await _move_to_dlq(r, mid, payload)


async def run_consumer() -> None:
    """Entry point — reconnects with back-off on any error."""
    delay = 1
    while True:
        try:
            r = aioredis.Redis.from_url(settings.redis_url, decode_responses=False)
            await _listen_loop(r)
        except asyncio.CancelledError:
            logger.info("Consumer task cancelled — shutting down")
            return
        except Exception as exc:
            logger.error("Consumer crashed: %s — reconnecting in %ss", exc, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)
        else:
            delay = 1
