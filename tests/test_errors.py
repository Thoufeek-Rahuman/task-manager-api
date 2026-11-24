import pytest
from fastapi.testclient import TestClient

from app.main import app


def assert_error_shape(response, status_code, code):
    """Every error must look like {"error": {"code": ..., "message": ...}}."""
    assert response.status_code == status_code
    body = response.json()
    assert list(body) == ["error"]
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)
    return body["error"]


# ---------- One format for every kind of error ----------


@pytest.mark.parametrize(
    ("method", "path", "status_code", "code"),
    [
        ("get", "/api/v1/tasks/999999", 404, "not_found"),  # raised by a service
        ("get", "/nope", 404, "not_found"),  # no such route
        ("delete", "/api/v1/health", 405, "method_not_allowed"),  # wrong method
        ("get", "/api/v1/tasks", 401, "unauthorized"),  # no token (checked below)
    ],
)
def test_errors_share_one_shape(client, auth_client, method, path, status_code, code):
    # The 404 for a task needs a logged-in user; the 401 case needs an anonymous one.
    used = client if status_code == 401 else auth_client

    response = getattr(used, method)(path)

    assert_error_shape(response, status_code, code)


def test_conflict_error_shape(client):
    body = {"email": "alice@example.com", "password": "secret123"}
    client.post("/api/v1/users", json=body)

    response = client.post("/api/v1/users", json=body)

    assert_error_shape(response, 409, "conflict")


# ---------- 401 keeps its header ----------


def test_missing_token_keeps_www_authenticate_header(client):
    response = client.get("/api/v1/tasks")

    error = assert_error_shape(response, 401, "unauthorized")
    assert error["message"] == "Not authenticated"
    assert response.headers["WWW-Authenticate"] == "Bearer"


# ---------- Validation errors (422) ----------


def test_validation_error_names_the_field(auth_client):
    response = auth_client.post("/api/v1/tasks", json={"title": ""})

    error = assert_error_shape(response, 422, "validation_error")
    assert error["message"] == "request validation failed"
    assert error["details"] == [
        {"field": "body.title", "message": "String should have at least 1 character"}
    ]


def test_validation_error_for_query_parameter(auth_client):
    response = auth_client.get("/api/v1/tasks", params={"limit": 0})

    error = assert_error_shape(response, 422, "validation_error")
    assert [d["field"] for d in error["details"]] == ["query.limit"]


def test_validation_error_lists_every_problem(client):
    response = client.post("/api/v1/users", json={})

    error = assert_error_shape(response, 422, "validation_error")
    assert {d["field"] for d in error["details"]} == {"body.email", "body.password"}


def test_other_errors_have_no_details(auth_client):
    response = auth_client.get("/api/v1/tasks/999999")

    assert "details" not in response.json()["error"]


# ---------- Unexpected crashes (500) ----------


@pytest.fixture
def crashing_route():
    """Temporarily add a route that raises an unexpected exception."""

    @app.get("/test-crash")
    def crash():
        raise RuntimeError("secret internal detail")

    yield
    app.router.routes = [
        r for r in app.router.routes if getattr(r, "path", None) != "/test-crash"
    ]


def test_unexpected_error_returns_generic_500(crashing_route):
    # raise_server_exceptions=False lets the test see the 500 response
    # instead of re-raising the exception inside the test.
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/test-crash")

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Internal server error"}
    }


def test_unexpected_error_does_not_leak_details(crashing_route):
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/test-crash")

    assert "secret" not in response.text
    assert "RuntimeError" not in response.text
    assert "Traceback" not in response.text
