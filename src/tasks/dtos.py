from datetime import date, datetime
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, StringConstraints

Priority = Literal["low", "medium", "high"]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


class TaskSchema(BaseModel):
    title: Title
    description: Description
    completed: bool = False
    priority: Priority = "medium"
    due_date: date | None = None


class TaskResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    completed: bool = False
    priority: Priority = "medium"
    due_date: date | None = None
    completed_at: datetime | None = None
    user_id: int | None = None


class DayCount(BaseModel):
    date: date
    count: int


class StatsResponse(BaseModel):
    completed_today: int
    completed_last_7_days: int
    last_7_days: list[DayCount]   # oldest first, ends with today
    current_streak: int           # consecutive days with at least one completed task
    best_streak: int
    total_completed: int          # completed tasks that have a completion time
