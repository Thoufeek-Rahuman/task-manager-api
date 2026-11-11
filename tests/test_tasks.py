import pytest

URL = "/api/v1/tasks"


def create_task(client, title="Task", completed=False):
    """Helper: create a task through the API and return its JSON."""
    response = client.post(URL, json={"title": title, "completed": completed})
    assert response.status_code == 201
    return response.json()


# ---------- POST /tasks (create) ----------


def test_create_task(client):
    response = client.post(URL, json={"title": "Milk"})

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Milk"
    assert data["completed"] is False
    assert isinstance(data["id"], int)


def test_create_completed_task(client):
    response = client.post(URL, json={"title": "Done already", "completed": True})

    assert response.status_code == 201
    assert response.json()["completed"] is True


def test_create_ignores_client_id(client):
    response = client.post(URL, json={"id": 12345, "title": "Sneaky"})

    assert response.status_code == 201
    assert response.json()["id"] != 12345


def test_create_title_with_200_characters_is_allowed(client):
    response = client.post(URL, json={"title": "x" * 200})

    assert response.status_code == 201


@pytest.mark.parametrize(
    "body",
    [
        {},  # title missing
        {"title": ""},  # empty title
        {"title": "x" * 201},  # title too long
        {"title": None},  # title is null
        {"title": "Ok", "completed": "maybe"},  # completed is not a bool
    ],
)
def test_create_invalid_body_returns_422(client, body):
    response = client.post(URL, json=body)

    assert response.status_code == 422


# ---------- GET /tasks (list) ----------


def test_list_tasks_empty(client):
    response = client.get(URL)

    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_ordered_by_id(client):
    first = create_task(client, "First")
    second = create_task(client, "Second")

    response = client.get(URL)

    ids = [task["id"] for task in response.json()]
    assert ids == [first["id"], second["id"]]


def test_list_tasks_filter_completed_true(client):
    create_task(client, "Open", completed=False)
    done = create_task(client, "Done", completed=True)

    response = client.get(URL, params={"completed": True})

    assert response.json() == [done]


def test_list_tasks_filter_completed_false(client):
    open_task = create_task(client, "Open", completed=False)
    create_task(client, "Done", completed=True)

    response = client.get(URL, params={"completed": False})

    assert response.json() == [open_task]


def test_list_tasks_default_limit_is_5(client):
    for i in range(7):
        create_task(client, f"Task {i}")

    response = client.get(URL)

    assert len(response.json()) == 5


def test_list_tasks_custom_limit(client):
    for i in range(3):
        create_task(client, f"Task {i}")

    response = client.get(URL, params={"limit": 2})

    assert len(response.json()) == 2


@pytest.mark.parametrize("limit", [0, -1, 101, "abc"])
def test_list_tasks_invalid_limit_returns_422(client, limit):
    response = client.get(URL, params={"limit": limit})

    assert response.status_code == 422


# ---------- GET /tasks/{id} (read one) ----------


def test_get_existing_task(client):
    task = create_task(client, "Bread")

    response = client.get(f"{URL}/{task['id']}")

    assert response.status_code == 200
    assert response.json() == task


def test_get_missing_task_returns_404(client):
    response = client.get(f"{URL}/98898")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not Found"}


def test_get_task_with_non_integer_id_returns_422(client):
    response = client.get(f"{URL}/abc")

    assert response.status_code == 422


# ---------- PUT /tasks/{id} (update) ----------


def test_update_task(client):
    task = create_task(client, "Old title")

    response = client.put(
        f"{URL}/{task['id']}", json={"title": "New title", "completed": True}
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": task["id"],
        "title": "New title",
        "completed": True,
    }


def test_update_task_is_saved(client):
    task = create_task(client, "Old title")
    client.put(f"{URL}/{task['id']}", json={"title": "New title", "completed": True})

    response = client.get(f"{URL}/{task['id']}")

    assert response.json()["title"] == "New title"
    assert response.json()["completed"] is True


def test_update_replaces_completed_with_default(client):
    task = create_task(client, "Task", completed=True)

    response = client.put(f"{URL}/{task['id']}", json={"title": "Only title"})

    assert response.json()["completed"] is False


def test_update_missing_task_returns_404(client):
    response = client.put(f"{URL}/98898", json={"title": "x"})

    assert response.status_code == 404


def test_update_invalid_body_returns_422(client):
    task = create_task(client, "Task")

    response = client.put(f"{URL}/{task['id']}", json={"title": ""})

    assert response.status_code == 422


# ---------- PATCH /tasks/{id} (partial update) ----------


def test_patch_only_title_keeps_completed(client):
    task = create_task(client, "Old title", completed=True)

    response = client.patch(f"{URL}/{task['id']}", json={"title": "New title"})

    assert response.status_code == 200
    assert response.json() == {
        "id": task["id"],
        "title": "New title",
        "completed": True,
    }


def test_patch_only_completed_keeps_title(client):
    task = create_task(client, "Keep me", completed=False)

    response = client.patch(f"{URL}/{task['id']}", json={"completed": True})

    assert response.json()["title"] == "Keep me"
    assert response.json()["completed"] is True


@pytest.mark.parametrize("body", [{"title": None}, {"completed": None}])
def test_patch_null_value_is_ignored(client, body):
    # Regression: an explicit null must not reach the NOT NULL column (was a 500).
    task = create_task(client, "Keep me", completed=True)

    response = client.patch(f"{URL}/{task['id']}", json=body)

    assert response.status_code == 200
    assert response.json() == {"id": task["id"], "title": "Keep me", "completed": True}


def test_patch_missing_task_returns_404(client):
    response = client.patch(f"{URL}/98898", json={"title": "x"})

    assert response.status_code == 404


# ---------- DELETE /tasks/{id} ----------


def test_delete_task(client):
    task = create_task(client, "To delete")

    response = client.delete(f"{URL}/{task['id']}")

    assert response.status_code == 204
    assert response.content == b""


def test_deleted_task_is_gone(client):
    task = create_task(client, "To delete")
    client.delete(f"{URL}/{task['id']}")

    response = client.get(f"{URL}/{task['id']}")

    assert response.status_code == 404


def test_delete_missing_task_returns_404(client):
    response = client.delete(f"{URL}/98898")

    assert response.status_code == 404


def test_delete_twice_returns_404_second_time(client):
    task = create_task(client, "To delete")
    client.delete(f"{URL}/{task['id']}")

    response = client.delete(f"{URL}/{task['id']}")

    assert response.status_code == 404


def test_ids_are_not_reused_after_delete(client):
    task = create_task(client, "Will be deleted")
    client.delete(f"{URL}/{task['id']}")

    new_task = create_task(client, "New")

    assert new_task["id"] > task["id"]
