from datetime import date
from typing import Annotated, Literal
from pydantic import BaseModel, Field, StringConstraints

Reason = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


class PlanPick(BaseModel):
    """One task the AI wants the user to do today (this is the shape we ask the AI for)."""
    task_id: int = Field(description="The id of one of the listed tasks, exactly as given")
    reason: Reason = Field(description="One short, friendly sentence on why this task is on today's list")


class AIPlan(BaseModel):
    """What the AI must return."""
    summary: Reason = Field(description="One or two encouraging sentences about the day ahead")
    picks: list[PlanPick] = Field(description="3 to 5 tasks in the order the user should do them")


class PlanItem(BaseModel):
    task_id: int
    title: str
    priority: Literal["low", "medium", "high"]
    due_date: date | None
    reason: str


class DailyPlanResponse(BaseModel):
    """What our API sends to the frontend."""
    summary: str
    items: list[PlanItem]
