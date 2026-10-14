"""Register, login and "who am I" tests."""
from datetime import datetime, timedelta, timezone

import jwt

from src.users.model import UserModel
from src.utils.db import LocalSession
from src.utils.settings import settings

USER = {"name": "Alice Doe", "username": "alice", "email": "alice@example.com", "password": "password123"}


# ---------- register ----------
def test_register_creates_user_without_leaking_the_password(client):
    response = client.post("/users/register", json=USER)

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    assert "password" not in body and "hash_password" not in body


def test_password_is_stored_hashed_not_as_plain_text(client):
    client.post("/users/register", json=USER)

    with LocalSession() as db:
        user = db.query(UserModel).filter_by(username="alice").one()

    assert user.hash_password != "password123"
    assert user.hash_password.startswith("$")  # real password hashes look like $argon2id$...


def test_register_rejects_duplicate_username(client):
    client.post("/users/register", json=USER)
    second = client.post("/users/register", json={**USER, "email": "other@example.com"})

    assert second.status_code == 400
    assert second.json()["detail"] == "Username already exists"


def test_register_rejects_duplicate_email(client):
    client.post("/users/register", json=USER)
    second = client.post("/users/register", json={**USER, "username": "alice2"})

    assert second.status_code == 400
    assert second.json()["detail"] == "Email already exists"


def test_register_requires_every_field(client):
    incomplete = {k: v for k, v in USER.items() if k != "email"}
    assert client.post("/users/register", json=incomplete).status_code == 422


# ---------- login ----------
def test_login_returns_a_token(client):
    client.post("/users/register", json=USER)
    response = client.post("/users/login", json={"username": "alice", "password": "password123"})

    assert response.status_code == 200
    assert response.json()["token"]


def test_wrong_password_and_unknown_user_give_the_same_error(client):
    """If the messages differed, attackers could discover which usernames exist."""
    client.post("/users/register", json=USER)

    wrong_password = client.post("/users/login", json={"username": "alice", "password": "nope"})
    unknown_user = client.post("/users/login", json={"username": "ghost", "password": "password123"})

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()


# ---------- is_auth ("who am I") ----------
def test_is_auth_returns_the_logged_in_user(client, alice):
    response = client.get("/users/is_auth", headers=alice)

    assert response.status_code == 200
    assert response.json()["username"] == "alice"


def test_is_auth_without_a_token_is_rejected(client):
    assert client.get("/users/is_auth").status_code == 401


def test_is_auth_with_a_garbage_token_is_rejected(client):
    response = client.get("/users/is_auth", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_token_signed_with_another_secret_is_rejected(client, alice):
    user_id = client.get("/users/is_auth", headers=alice).json()["id"]
    forged = jwt.encode(
        {"_id": user_id, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "a-different-secret-key-used-by-an-attacker",
        algorithm=settings.ALGORITHM,
    )

    response = client.get("/users/is_auth", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_expired_token_is_rejected(client, alice):
    user_id = client.get("/users/is_auth", headers=alice).json()["id"]
    expired = jwt.encode(
        {"_id": user_id, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    response = client.get("/users/is_auth", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
