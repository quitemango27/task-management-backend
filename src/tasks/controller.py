from datetime import datetime, timezone
from src.tasks.dtos import TaskSchema
from src.tasks.stats import compute_stats
from sqlalchemy.orm import Session
from src.tasks.model import TaskModel
from fastapi import HTTPException
from src.users.model import UserModel


def get_owned_task(task_id: int, db: Session, user: UserModel) -> TaskModel:
    """Find a task by id and make sure it belongs to this user."""
    task = db.get(TaskModel, task_id)
    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def create_task(body: TaskSchema, db: Session, user: UserModel):
    data = body.model_dump()
    new_task = TaskModel(
        title=data["title"],
        description=data["description"],
        completed=data["completed"],
        priority=data["priority"],
        due_date=data["due_date"],
        # A task created already-completed gets its completion time right away
        completed_at=datetime.now(timezone.utc) if data["completed"] else None,
        user_id=user.id,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


def get_all_tasks(db: Session, user: UserModel):
    return db.query(TaskModel).filter(TaskModel.user_id == user.id).all()


def get_task_by_id(task_id: int, db: Session, user: UserModel):
    return get_owned_task(task_id, db, user)


def update_task(task_id: int, body: TaskSchema, db: Session, user: UserModel):
    one_task = get_owned_task(task_id, db, user)
    was_completed = bool(one_task.completed)

    for field, value in body.model_dump().items():
        setattr(one_task, field, value)

    # Record WHEN it became completed. Only on the change pending -> completed,
    # so editing an already-completed task doesn't move its completion time.
    if body.completed and not was_completed:
        one_task.completed_at = datetime.now(timezone.utc)
    elif not body.completed:
        one_task.completed_at = None

    db.commit()
    db.refresh(one_task)
    return one_task


def delete_task(task_id: int, db: Session, user: UserModel):
    one_task = get_owned_task(task_id, db, user)
    db.delete(one_task)
    db.commit()
    return None


def get_stats(db: Session, user: UserModel, tz_offset_minutes: int):
    rows = (
        db.query(TaskModel.completed_at)
        .filter(TaskModel.user_id == user.id, TaskModel.completed_at.isnot(None))
        .all()
    )
    return compute_stats([row[0] for row in rows], tz_offset_minutes)