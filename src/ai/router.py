import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.ai import planner
from src.ai.dtos import AIBreakdown, BreakdownRequest, BreakdownResponse, DailyPlanResponse
from src.ai.limiter import check_rate_limit
from src.tasks.model import TaskModel
from src.tasks.stats import _to_local_date
from src.users.model import UserModel
from src.utils.db import get_db
from src.utils.helpers import is_authenticated
from src.utils.settings import settings

logger = logging.getLogger(__name__)

ai_router = APIRouter(prefix="/ai")


def get_plan_model():
    """Dependency that gives the AI model. Tests replace this with a fake one."""
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="The AI assistant isn't set up yet.")
    return planner.build_model()


def get_breakdown_model():
    """Same idea as get_plan_model, but asks Groq for the breakdown shape. Tests replace this too."""
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="The AI assistant isn't set up yet.")
    return planner.build_model(AIBreakdown)


@ai_router.post("/daily-plan", response_model=DailyPlanResponse, status_code=status.HTTP_200_OK)
def daily_plan(
    tz_offset: int = Query(0, ge=-840, le=840, description="Browser's getTimezoneOffset(), in minutes"),
    db: Session = Depends(get_db),
    user: UserModel = Depends(is_authenticated),
    model=Depends(get_plan_model),
):
    check_rate_limit(user.id)

    today = _to_local_date(datetime.now(timezone.utc), tz_offset)
    pending = (
        db.query(TaskModel)
        .filter(TaskModel.user_id == user.id, TaskModel.completed.is_(False))
        .all()
    )
    try:
        return planner.generate_daily_plan(pending, today, model)
    except Exception:
        # Groq down, quota hit, bad reply... never show raw errors to the user
        logger.exception("AI daily plan failed")
        raise HTTPException(status_code=503, detail="Mia is taking a short break. Please try again in a minute.")


@ai_router.post("/breakdown", response_model=BreakdownResponse, status_code=status.HTTP_200_OK)
def breakdown(
    body: BreakdownRequest,
    user: UserModel = Depends(is_authenticated),
    model=Depends(get_breakdown_model),
):
    check_rate_limit(user.id, "breakdown")
    try:
        return planner.generate_breakdown(body.title, body.details, model)
    except Exception:
        logger.exception("AI breakdown failed")
        raise HTTPException(status_code=503, detail="Mia is taking a short break. Please try again in a minute.")
