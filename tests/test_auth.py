from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.user import User

LOGIN_URL = "/api/v1/auth/login"
USERS_URL = "/api/v1/users"


@pytest.fixture
def user(client):
    """A registered user, created through the API."""
    response = client.post(
        USERS_URL, json={"email": "alice@example.com", "password": "secret123"}
    )
    assert response.status_code == 201
    return response.json()


def login(client, username="alice@example.com", password="secret123"):
    # OAuth2 login is a form, not JSON, so it uses data= instead of json=
    return client.post(LOGIN_URL, data={"username": username, "password": password})


def test_login_returns_token(client, user):
    response = login(client)

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)


def test_token_contains_user_id_and_expiry(client, user):
    token = login(client).json()["access_token"]

    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

    assert payload["sub"] == str(user["id"])
    expires = datetime.fromtimestamp(payload["exp"], UTC)
    expected = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    assert abs(expires - expected) < timedelta(minutes=1)


def test_token_is_signed_with_secret_key(client, user):
    token = login(client).json()["access_token"]

    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, "x" * 32, algorithms=[settings.algorithm])


def test_login_email_is_case_insensitive(client, user):
    response = login(client, username="ALICE@Example.com")

    assert response.status_code == 200


def test_login_wrong_password_returns_401(client, user):
    response = login(client, password="wrong-password")

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_login_unknown_email_returns_same_401(client, user):
    wrong_password = login(client, password="wrong-password")
    unknown_email = login(client, username="nobody@example.com")

    assert unknown_email.status_code == 401
    assert unknown_email.json() == wrong_password.json()


def test_login_inactive_user_returns_403(client, db, user):
    db_user = db.scalar(select(User).where(User.email == "alice@example.com"))
    db_user.is_active = False
    db.commit()

    response = login(client)

    assert response.status_code == 403
    assert response.json() == {"detail": "Inactive user"}


def test_login_with_json_body_returns_422(client, user):
    response = client.post(
        LOGIN_URL, json={"username": "alice@example.com", "password": "secret123"}
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "form", [{}, {"username": "alice@example.com"}, {"password": "x"}]
)
def test_login_missing_fields_returns_422(client, form):
    response = client.post(LOGIN_URL, data=form)

    assert response.status_code == 422
