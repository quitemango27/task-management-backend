from sqlalchemy import Column,  Integer, String, Boolean, DateTime
from src.utils.db import Base

class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    username = Column(String(50), unique=True, nullable=False)
    hash_password = Column(String(200), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    