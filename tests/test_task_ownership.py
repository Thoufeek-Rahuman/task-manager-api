from sqlalchemy import select

from app.models.task import Task
from app.models.user import User

URL = "/api/v1/tasks"


def create_task(client, title="Owner's task", headers=None):
    response = client.post(URL, json={"title": title}, headers=headers)
    assert response.status_code == 201
    return response.json()


# ---------- Creating sets the owner ----------


def test_new_task_belongs_to_current_user(auth_client, db):
    task = create_task(auth_client)

    row = db.get(Task, task["id"])
    owner = db.scalar(select(User).where(User.email == "owner@example.com"))
    assert row.user_id == owner.id


def test_client_cannot_choose_owner(auth_client, db, other_user_headers):
    other = db.scalar(select(User).where(User.email == "other@example.com"))

    response = auth_client.post(URL, json={"title": "Sneaky", "user_id": other.id})

    row = db.get(Task, response.json()["id"])
    assert row.user_id != other.id


def test_response_does_not_include_user_id(auth_client):
    task = create_task(auth_client)

    assert "user_id" not in task


# ---------- Other users can't see or change it ----------


def test_list_shows_only_own_tasks(auth_client, other_user_headers):
    mine = create_task(auth_client, "Mine")
    create_task(auth_client, "Theirs", headers=other_user_headers)

    data = auth_client.get(URL).json()

    assert [t["id"] for t in data["items"]] == [mine["id"]]
    assert data["total"] == 1


def test_total_counts_only_own_tasks(auth_client, other_user_headers):
    for i in range(3):
        create_task(auth_client, f"Mine {i}")
    create_task(auth_client, "Theirs", headers=other_user_headers)

    data = auth_client.get(URL, headers=other_user_headers).json()

    assert data["total"] == 1


def test_other_user_cannot_get_task(auth_client, other_user_headers):
    task = create_task(auth_client)

    response = auth_client.get(f"{URL}/{task['id']}", headers=other_user_headers)

    assert response.status_code == 404


def test_other_user_cannot_put_task(auth_client, other_user_headers):
    task = create_task(auth_client, "Original")

    response = auth_client.put(
        f"{URL}/{task['id']}", json={"title": "Hacked"}, headers=other_user_headers
    )

    assert response.status_code == 404
    assert auth_client.get(f"{URL}/{task['id']}").json()["title"] == "Original"


def test_other_user_cannot_patch_task(auth_client, other_user_headers):
    task = create_task(auth_client, "Original")

    response = auth_client.patch(
        f"{URL}/{task['id']}", json={"completed": True}, headers=other_user_headers
    )

    assert response.status_code == 404
    assert auth_client.get(f"{URL}/{task['id']}").json()["completed"] is False


def test_other_user_cannot_delete_task(auth_client, other_user_headers):
    task = create_task(auth_client)

    response = auth_client.delete(f"{URL}/{task['id']}", headers=other_user_headers)

    assert response.status_code == 404
    assert auth_client.get(f"{URL}/{task['id']}").status_code == 200


def test_foreign_task_looks_the_same_as_missing_task(auth_client, other_user_headers):
    task = create_task(auth_client)

    foreign = auth_client.get(f"{URL}/{task['id']}", headers=other_user_headers)
    missing = auth_client.get(f"{URL}/999999", headers=other_user_headers)

    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()


# ---------- Deleting a user ----------


def test_deleting_user_deletes_their_tasks(auth_client, db):
    task = create_task(auth_client)
    owner = db.scalar(select(User).where(User.email == "owner@example.com"))

    db.delete(owner)
    db.commit()
    db.expire_all()

    assert db.get(Task, task["id"]) is None
