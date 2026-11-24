from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User

ME_URL = "/api/v1/users/me"
UNAUTHORIZED = {
    "error": {"code": "unauthorized", "message": "Could not validate credentials"}
}


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- /users/me ----------


def test_me_returns_logged_in_user(auth_client):
    response = auth_client.get(ME_URL)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "owner@example.com"
    assert "hashed_password" not in data


def test_me_without_token_returns_401(client):
    response = client.get(ME_URL)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


# ---------- Bad tokens ----------


def test_garbage_token_returns_401(client):
    response = client.get(ME_URL, headers=bearer("not-a-jwt"))

    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED


def test_tampered_token_returns_401(auth_client):
    token = auth_client.headers["Authorization"].removeprefix("Bearer ")
    header, payload, signature = token.split(".")
    tampered = f"{header}.{payload}x.{signature}"

    response = auth_client.get(ME_URL, headers=bearer(tampered))

    assert response.status_code == 401


def test_token_signed_with_other_secret_returns_401(client):
    token = jwt.encode({"sub": "1"}, "x" * 32, algorithm="HS256")

    response = client.get(ME_URL, headers=bearer(token))

    assert response.status_code == 401


def test_expired_token_returns_401(auth_client):
    me = auth_client.get(ME_URL).json()
    expired = jwt.encode(
        {"sub": str(me["id"]), "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.secret_key,
        algorithm=settings.algorithm,
    )

    response = auth_client.get(ME_URL, headers=bearer(expired))

    assert response.status_code == 401


def test_token_for_deleted_user_returns_401(client):
    token = create_access_token("999999")

    response = client.get(ME_URL, headers=bearer(token))

    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED


def test_inactive_user_returns_403(auth_client, db):
    user = db.scalar(select(User).where(User.email == "owner@example.com"))
    user.is_active = False
    db.commit()

    response = auth_client.get(ME_URL)

    assert response.status_code == 403
    assert response.json() == {
        "error": {"code": "forbidden", "message": "Inactive user"}
    }


# ---------- Which routes are protected ----------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/v1/tasks"),
        ("post", "/api/v1/tasks"),
        ("get", "/api/v1/tasks/1"),
        ("put", "/api/v1/tasks/1"),
        ("patch", "/api/v1/tasks/1"),
        ("delete", "/api/v1/tasks/1"),
    ],
)
def test_task_routes_require_token(client, method, path):
    response = getattr(client, method)(path)

    assert response.status_code == 401


def test_public_routes_need_no_token(client):
    assert client.get("/api/v1/health").status_code == 200
    register = client.post(
        "/api/v1/users", json={"email": "new@example.com", "password": "secret123"}
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "new@example.com", "password": "secret123"},
    )
    assert login.status_code == 200
