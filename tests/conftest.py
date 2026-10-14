"""Shared setup for every test file.

THE MOST IMPORTANT RULE: tests must never touch your real database.

So before the app is imported, we point it at a throw-away SQLite file in the
computer's temp folder. Environment variables beat the values in your .env file,
so your real PostgreSQL settings are never used while tests run.
"""
import os
import tempfile
from pathlib import Path

_DB_FILE = Path(tempfile.gettempdir()) / "taskflow_pytest.db"
try:
    _DB_FILE.unlink()
except FileNotFoundError:
    pass

# check_same_thread=false lets the test client use SQLite from its own thread
os.environ["DB_connection"] = f"sqlite:///{_DB_FILE.as_posix()}?check_same_thread=false"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"
os.environ["ALGORITHM"] = "HS256"
os.environ["EXP_TIME"] = "60"

import pytest  # noqa: E402  (must come after the environment is set)
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from src.utils.db import Base, engine  # noqa: E402


@pytest.fixture
def client():
    """A fake browser that talks to your API. Every test starts with empty tables."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user(client):
    """Registers a user, logs in, and returns the Authorization header for them."""

    def _make(username="alice", password="password123"):
        client.post(
            "/users/register",
            json={
                "name": username.title(),
                "username": username,
                "email": f"{username}@example.com",
                "password": password,
            },
        )
        token = client.post("/users/login", json={"username": username, "password": password}).json()["token"]
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture
def alice(make_user):
    return make_user("alice")


@pytest.fixture
def bob(make_user):
    return make_user("bob")


@pytest.fixture
def create_task(client):
    """Creates a task for the given user. Pass any field to override the defaults."""

    def _create(headers, **overrides):
        body = {"title": "Write report", "description": "Quarterly numbers", **overrides}
        return client.post("/tasks/create", json=body, headers=headers)

    return _create
