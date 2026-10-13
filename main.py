from src.utils.db import Base, engine
from fastapi import FastAPI
from src.tasks.router import task_routes
from src.users.router import user_router


from fastapi.middleware.cors import CORSMiddleware



Base.metadata.create_all(bind=engine)

app=FastAPI(title="Task Management System")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(task_routes)
app.include_router(user_router)