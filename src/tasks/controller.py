from src.tasks.dtos import TaskSchema
from sqlalchemy.orm import Session
from src.tasks.model import TaskModel
from fastapi import HTTPException
from src.users.model import UserModel


def create_task(body: TaskSchema,db: Session,user:UserModel):

    data=body.model_dump()
    new_task=TaskModel(title=data["title"],
                       description=data["description"],
                       completed=data["completed"],
                       user_id=user.id
                       )
    db.add(new_task)
    db.commit() 
    db.refresh(new_task)


    return new_task


def get_all_tasks(db: Session,user:UserModel):
    tasks=db.query(TaskModel).filter(TaskModel.user_id == user.id).all()
    return tasks

def get_task_by_id(task_id:int,db: Session):
    one_task=db.query(TaskModel).get(task_id)
    if not one_task:
        raise HTTPException(status_code=404,detail="Task not found")
    return one_task

def update_task(task_id:int,body:TaskSchema,db: Session,user:UserModel):
    one_task=db.query(TaskModel).get(task_id)
    if not one_task:
        raise HTTPException(status_code=404,detail="Task not found")

    if one_task.user_id != user.id:
        raise HTTPException(status_code=403,detail="Unauthorized to update this task")

    # one_task.title=body.title
    # one_task.description=body.description   
    # one_task.completed=body.completed
    body=body.model_dump()
    for feild ,value in body.items():
        setattr(one_task,feild,value)

    db.add(one_task)
    db.commit()
    db.refresh(one_task)

    return one_task


def delete_task(task_id:int,db: Session,user:UserModel):
    one_task=db.query(TaskModel).get(task_id)
    if not one_task:
        raise HTTPException(status_code=404,detail="Task not found")
    if one_task.user_id != user.id:
            raise HTTPException(status_code=403,detail="Unauthorized to delete this task")
    
    db.delete(one_task)
    db.commit()

    return None