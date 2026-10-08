from sqlalchemy import Column, ForeignKey,Integer,String,Boolean,ForeignKey
from src.utils.db import Base

class TaskModel(Base):
    __tablename__="user_tasks"
    id=Column(Integer,primary_key=True,index=True)
    title=Column(String(100),nullable=False)
    description=Column(String(200),nullable=False)
    completed=Column(Boolean,default=False)

    user_id = Column(Integer,ForeignKey("users.id",ondelete="CASCADE"),nullable=True)