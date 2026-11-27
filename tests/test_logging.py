import logging
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def capture_info_logs(caplog):
    """Record INFO and above for every test in this file."""
    caplog.set_level(logging.INFO)


def app_records(caplog):
    """Only the records written by our own code (loggers named app.*).

    caplog also captures the test client's own logs (httpx), which print full URLs.
    Those are not part of the application, so they must not count here.
    """
    return [r for r in caplog.records if r.name.startswith("app")]


def app_log_text(caplog):
    return "\n".join(r.getMessage() for r in app_records(caplog))


def request_lines(caplog):
    return [r.getMessage() for r in caplog.records if r.name == "app.requests"]


# ---------- Request logging ----------


def test_request_is_logged_with_method_path_status_and_duration(client, caplog):
    client.get("/api/v1/health")

    lines = request_lines(caplog)
    assert len(lines) == 1
    assert re.fullmatch(r"GET /api/v1/health -> 200 \(\d+ ms\)", lines[0])


def test_error_responses_are_logged_with_their_status(auth_client, caplog):
    caplog.clear()

    auth_client.get("/api/v1/tasks/999999")

    lines = request_lines(caplog)
    assert len(lines) == 1
    assert re.fullmatch(r"GET /api/v1/tasks/999999 -> 404 \(\d+ ms\)", lines[0])


def test_each_request_gets_its_own_line(client, caplog):
    client.get("/api/v1/health")
    client.get("/api/v1/health")
    client.get("/nope")

    lines = request_lines(caplog)
    assert len(lines) == 3
    assert lines[2].startswith("GET /nope -> 404")


# ---------- Nothing sensitive in the logs ----------


def test_query_string_is_not_logged(auth_client, caplog):
    caplog.clear()

    auth_client.get("/api/v1/tasks", params={"limit": 5, "token": "abc123"})

    assert "abc123" not in app_log_text(caplog)
    assert "limit=5" not in app_log_text(caplog)
    assert request_lines(caplog)[0].startswith("GET /api/v1/tasks -> 200")


def test_passwords_and_tokens_never_reach_the_logs(client, caplog):
    client.post(
        "/api/v1/users", json={"email": "alice@example.com", "password": "secret123"}
    )
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@example.com", "password": "secret123"},
    )
    token = login.json()["access_token"]
    client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})

    logs = app_log_text(caplog)
    assert login.status_code == 200
    assert len(request_lines(caplog)) == 3  # the requests really were logged
    assert "secret123" not in logs
    assert token not in logs
    assert "argon2" not in logs
    assert "Bearer" not in logs


def test_wrong_password_attempt_is_not_logged_in_clear(client, caplog):
    client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@example.com", "password": "wrong-password-xyz"},
    )

    assert len(request_lines(caplog)) == 1
    assert "wrong-password-xyz" not in app_log_text(caplog)


# ---------- Unexpected errors ----------


@pytest.fixture
def crashing_route():
    @app.get("/test-crash")
    def crash():
        raise RuntimeError("secret internal detail")

    yield
    app.router.routes = [
        r for r in app.router.routes if getattr(r, "path", None) != "/test-crash"
    ]


def test_crash_is_logged_with_traceback(crashing_route, caplog):
    client = TestClient(app, raise_server_exceptions=False)

    client.get("/test-crash")

    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 1
    assert errors[0].getMessage() == "Unhandled error on GET /test-crash"
    assert errors[0].exc_info is not None
    assert "RuntimeError: secret internal detail" in caplog.text


def test_crash_details_reach_the_log_but_not_the_client(crashing_route, caplog):
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/test-crash")

    assert "secret internal detail" in caplog.text
    assert "secret internal detail" not in response.text
    assert response.json()["error"]["code"] == "internal_error"
