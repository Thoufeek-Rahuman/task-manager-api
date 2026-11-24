import pytest
from sqlalchemy import select

from app.models.user import User

URL = "/api/v1/users"


def register(client, email="alice@example.com", password="secret123"):
    """Helper: register a user through the API and return the response."""
    return client.post(URL, json={"email": email, "password": password})


def test_register_user(client):
    response = register(client)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert data["is_active"] is True
    assert isinstance(data["id"], int)
    assert "created_at" in data


def test_register_response_has_no_password(client):
    response = register(client)

    data = response.json()
    assert "password" not in data
    assert "hashed_password" not in data


def test_password_is_stored_hashed(client, db):
    register(client, password="secret123")

    user = db.scalar(select(User).where(User.email == "alice@example.com"))

    assert user is not None
    assert user.hashed_password != "secret123"
    assert user.hashed_password.startswith("$argon2")


def test_email_is_stored_lowercase(client):
    response = register(client, email="Alice@Example.COM")

    assert response.json()["email"] == "alice@example.com"


def test_duplicate_email_returns_409(client):
    register(client)

    response = register(client)

    assert response.status_code == 409
    assert response.json() == {
        "error": {"code": "conflict", "message": "Email already registered"}
    }


def test_duplicate_email_different_case_returns_409(client):
    register(client, email="alice@example.com")

    response = register(client, email="ALICE@example.com")

    assert response.status_code == 409


@pytest.mark.parametrize(
    "body",
    [
        {},  # nothing sent
        {"email": "alice@example.com"},  # password missing
        {"password": "secret123"},  # email missing
        {"email": "not-an-email", "password": "secret123"},  # invalid email
        {"email": "alice@example.com", "password": "short"},  # under 8 characters
        {"email": "alice@example.com", "password": "x" * 129},  # over 128 characters
    ],
)
def test_register_invalid_body_returns_422(client, body):
    response = client.post(URL, json=body)

    assert response.status_code == 422


def test_password_with_8_characters_is_allowed(client):
    response = register(client, password="x" * 8)

    assert response.status_code == 201
