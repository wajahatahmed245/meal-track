import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai_evaluation_service import generate_evaluation, get_evaluation, parse_evaluation
from ..database import get_db
from ..deps import get_current_user
from ..gemini import GeminiError
from ..models import User
from ..schemas import AiEvaluationDetail

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-evaluation", tags=["ai-evaluation"])


@router.get("", response_model=AiEvaluationDetail)
async def get_ai_evaluation(
    day: date = Query(..., description="Date in YYYY-MM-DD format"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the stored AI evaluation for a date.
    Does NOT call Gemini — 404 if no evaluation exists yet.
    """
    row = await get_evaluation(db, user, day)
    if row is None:
        raise HTTPException(status_code=404, detail="No evaluation found for this date")
    return parse_evaluation(row)


@router.post("", response_model=AiEvaluationDetail, status_code=status.HTTP_201_CREATED)
async def generate_ai_evaluation(
    day: date = Query(..., description="Date in YYYY-MM-DD format"),
    force: bool = Query(False, description="Re-evaluate even if evaluation already exists"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate (or re-generate) an AI evaluation for a date.

    - Zero meals → 422, Gemini not called.
    - Existing evaluation + force=false → returns existing, Gemini not called.
    - force=true → calls Gemini, updates existing row.
    """
    try:
        row = await generate_evaluation(
            db=db,
            user=user,
            day=day,
            trigger_source="manual",
            force=force,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except GeminiError as exc:
        logger.error("Gemini failure in manual evaluation for %s: %s", day.isoformat(), exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI evaluation service is currently unavailable. Please try again later.",
        )
    except IntegrityError:
        # Race condition: concurrent request already inserted the row.
        # Rollback and re-fetch. Both steps are guarded — if the session is
        # already in a bad state (e.g. during tests with mocked service calls)
        # we fall through to the 500 rather than raising an uncaught exception.
        try:
            await db.rollback()
        except Exception:
            pass
        try:
            row = await get_evaluation(db, user, day)
        except Exception:
            row = None
        if row is None:
            raise HTTPException(status_code=500, detail="Unexpected database error")
    return parse_evaluation(row)
