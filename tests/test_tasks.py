"""Create, read, update and delete tasks, plus who is allowed to touch what."""


def update(client, headers, task_id, **fields):
    """Sends a full update (the API expects every field, like the frontend does)."""
    body = {"title": "Write report", "description": "Quarterly numbers", "completed": False, **fields}
    return client.put(f"/tasks/update_task/{task_id}", json=body, headers=headers)


# ---------- create ----------
def test_create_task_fills_in_defaults(create_task, alice):
    response = create_task(alice)

    assert response.status_code == 201
    task = response.json()
    assert task["title"] == "Write report"
    assert task["completed"] is False
    assert task["priority"] == "medium"
    assert task["due_date"] is None
    assert task["completed_at"] is None
    assert task["user_id"] is not None


def test_create_task_with_priority_and_due_date(create_task, alice):
    task = create_task(alice, priority="high", due_date="2030-01-31").json()

    assert task["priority"] == "high"
    assert task["due_date"] == "2030-01-31"


def test_creating_a_task_requires_login(client):
    response = client.post("/tasks/create", json={"title": "x", "description": "y"})
    assert response.status_code == 401


# ---------- input validation (limits match the database columns) ----------
def test_title_of_exactly_100_characters_is_accepted(create_task, alice):
    assert create_task(alice, title="a" * 100).status_code == 201


def test_title_over_100_characters_is_rejected(create_task, alice):
    assert create_task(alice, title="a" * 101).status_code == 422


def test_empty_title_is_rejected(create_task, alice):
    assert create_task(alice, title="").status_code == 422


def test_whitespace_only_title_is_rejected(create_task, alice):
    assert create_task(alice, title="    ").status_code == 422


def test_description_over_200_characters_is_rejected(create_task, alice):
    assert create_task(alice, description="a" * 201).status_code == 422


def test_unknown_priority_is_rejected(create_task, alice):
    assert create_task(alice, priority="urgent").status_code == 422


def test_invalid_due_date_is_rejected(create_task, alice):
    assert create_task(alice, due_date="tomorrow").status_code == 422


def test_missing_title_is_rejected(client, alice):
    response = client.post("/tasks/create", json={"description": "no title"}, headers=alice)
    assert response.status_code == 422


# ---------- read ----------
def test_list_returns_only_my_tasks(client, create_task, alice, bob):
    create_task(alice, title="Alice 1")
    create_task(alice, title="Alice 2")
    create_task(bob, title="Bob 1")

    alice_titles = {t["title"] for t in client.get("/tasks/all_tasks", headers=alice).json()}
    bob_titles = {t["title"] for t in client.get("/tasks/all_tasks", headers=bob).json()}

    assert alice_titles == {"Alice 1", "Alice 2"}
    assert bob_titles == {"Bob 1"}


def test_get_one_task(client, create_task, alice):
    task_id = create_task(alice).json()["id"]
    response = client.get(f"/tasks/one_task/{task_id}", headers=alice)

    assert response.status_code == 200
    assert response.json()["id"] == task_id


def test_get_missing_task_is_404(client, alice):
    assert client.get("/tasks/one_task/9999", headers=alice).status_code == 404


# ---------- update ----------
def test_update_changes_the_fields_and_returns_200(client, create_task, alice):
    task_id = create_task(alice).json()["id"]

    response = update(client, alice, task_id, title="New title", priority="low", due_date="2030-05-05")

    assert response.status_code == 200
    task = response.json()
    assert task["title"] == "New title"
    assert task["priority"] == "low"
    assert task["due_date"] == "2030-05-05"


def test_completed_at_is_set_kept_and_cleared(client, create_task, alice):
    task_id = create_task(alice).json()["id"]

    # Tick it: the completion time appears
    done = update(client, alice, task_id, completed=True).json()
    assert done["completed"] is True
    stamp = done["completed_at"]
    assert stamp is not None

    # Edit the title of an already-completed task: the completion time must not move
    edited = update(client, alice, task_id, completed=True, title="Renamed").json()
    assert edited["completed_at"] == stamp

    # Un-tick it: the completion time disappears
    undone = update(client, alice, task_id, completed=False).json()
    assert undone["completed_at"] is None


def test_task_created_as_completed_gets_a_completion_time(create_task, alice):
    task = create_task(alice, completed=True).json()
    assert task["completed_at"] is not None


# ---------- delete ----------
def test_delete_removes_the_task(client, create_task, alice):
    task_id = create_task(alice).json()["id"]

    assert client.delete(f"/tasks/delete_task/{task_id}", headers=alice).status_code == 204
    assert client.get(f"/tasks/one_task/{task_id}", headers=alice).status_code == 404


# ---------- privacy: nobody touches someone else's task ----------
def test_other_users_cannot_read_update_or_delete_my_task(client, create_task, alice, bob):
    task_id = create_task(alice, title="Private").json()["id"]

    assert client.get(f"/tasks/one_task/{task_id}", headers=bob).status_code == 404
    assert update(client, bob, task_id, title="Hacked").status_code == 404
    assert client.delete(f"/tasks/delete_task/{task_id}", headers=bob).status_code == 404

    # ...and the task is unchanged
    task = client.get(f"/tasks/one_task/{task_id}", headers=alice).json()
    assert task["title"] == "Private"
