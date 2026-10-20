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


# ---------- Task breakdown ("Prepare for exam" -> small steps) ----------

class AIStep(BaseModel):
    """One step as the AI writes it. Kept loose on purpose: we clean it up ourselves afterwards."""
    title: str = Field(description="A short, concrete action starting with a verb, under 80 characters")
    priority: str = Field(description="One of: low, medium, high")


class AIBreakdown(BaseModel):
    """What the AI must return for a breakdown."""
    steps: list[AIStep] = Field(description="3 to 6 steps, in the order they should be done")


class BreakdownRequest(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    details: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""


class BreakdownStep(BaseModel):
    title: str
    priority: Literal["low", "medium", "high"]


class BreakdownResponse(BaseModel):
    steps: list[BreakdownStep]
