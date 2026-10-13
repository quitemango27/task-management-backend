from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict

Priority = Literal["low", "medium", "high"]


class TaskSchema(BaseModel):
    title: str
    description: str
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
    last_7_days: list[DayCount]  
    current_streak: int           
    best_streak: int
    total_completed: int          