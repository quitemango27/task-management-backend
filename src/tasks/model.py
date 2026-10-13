from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, Date, DateTime
from src.utils.db import Base


class TaskModel(Base):
    __tablename__ = "user_tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(String(200), nullable=False)
    completed = Column(Boolean, default=False)

    priority = Column(String(10), nullable=False, default="medium", server_default="medium")
    due_date = Column(Date, nullable=True)


    completed_at = Column(DateTime(timezone=True), nullable=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)