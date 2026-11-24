import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

# Debug mode makes Starlette print tracebacks instead of calling the 500 handler.
# Real environment variables beat .env, so tests always run with debug off.
os.environ["DEBUG"] = "false"

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

TEST_DATABASE_URL = make_url(settings.database_url).set(database="task_manager_test")


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
        autoflush=False,
    )
    yield session
    session.close()
    transaction.rollback()
    connection.close()


def _make_client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client(db):
    """A client that sends no token (an anonymous visitor)."""
    yield from _make_client(db)


def _register_and_login(client, email, password="secret123"):
    """Register a user and return the Authorization header for them."""
    client.post("/api/v1/users", json={"email": email, "password": password})
    response = client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def auth_client(db):
    """A client logged in as owner@example.com; every request sends its token."""
    for c in _make_client(db):
        c.headers.update(_register_and_login(c, "owner@example.com"))
        yield c


@pytest.fixture
def other_user_headers(auth_client):
    """Authorization header for a second user, other@example.com.

    Pass it per request: auth_client.get(url, headers=other_user_headers)
    """
    return _register_and_login(auth_client, "other@example.com")
