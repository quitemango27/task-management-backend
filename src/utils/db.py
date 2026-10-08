from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
from src.utils.settings import settings

Base = declarative_base()

engine=create_engine(url=settings.DB_connection)

LocalSession=sessionmaker(bind=engine)

def get_db():
    Session=LocalSession()
    try:
        yield Session
    finally:
        Session.close()