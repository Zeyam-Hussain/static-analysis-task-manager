def register_user(client, username="test"):
    response = client.post(
        "/api/v1/register/",
        json={
            "username": username,
            "password": "test",
            "email": f"{username}@test.com",
        },
    )
    assert response.status_code == 200


def auth_header(client, username="test"):
    register_user(client, username)
    response = client.post(
        "/api/v1/login/",
        data={"username": username, "password": "test"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Real-Time Task Manager API"}


def test_create_user(client):
    response = client.post("/api/v1/register/", json={"username": "test", "password": "test", "email": "test@test.com"})
    assert response.status_code == 200
    assert "id" in response.json()
    assert "username" in response.json()
    assert "email" in response.json()


def test_login(client):
    register_user(client)
    response = client.post(
        "/api/v1/login/",
        data={"username": "test", "password": "test"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json().get("token_type") == "bearer"


def test_create_task(client):
    response = client.post(
        "/api/v1/tasks/",
        json={"title": "New Task", "description": "some_text"},
        headers=auth_header(client),
    )
    assert response.status_code == 200
    task = response.json()
    assert "id" in task
    assert task["title"] == "New Task"
    assert task["completed"] is False


def test_read_tasks(client):
    headers = auth_header(client)
    client.post(
        "/api/v1/tasks/",
        json={"title": "New Task", "description": "some_text"},
        headers=headers,
    )
    response = client.get("/api/v1/tasks/", headers=headers)
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    assert len(tasks) > 0


def test_read_task(client):
    headers = auth_header(client)
    created = client.post(
        "/api/v1/tasks/",
        json={"title": "New Task", "description": "some_text"},
        headers=headers,
    )
    task_id = created.json()["id"]
    response = client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert response.status_code == 200
    task = response.json()
    assert task["id"] == task_id


def test_read_invalid_task(client):
    invalid_task_id = 999
    response = client.get(
        f"/api/v1/tasks/{invalid_task_id}",
        headers=auth_header(client),
    )
    assert response.status_code == 404


def test_task_ownership_is_enforced(client):
    owner_headers = auth_header(client)
    created = client.post(
        "/api/v1/tasks/",
        json={"title": "Private task", "description": "Owner only"},
        headers=owner_headers,
    )
    task_id = created.json()["id"]
    other_headers = auth_header(client, "other")

    assert client.get("/api/v1/tasks/", headers=other_headers).json() == []
    assert client.get(f"/api/v1/tasks/{task_id}", headers=other_headers).status_code == 404
    assert client.put(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Changed", "description": "No access", "completed": True},
        headers=other_headers,
    ).status_code == 404
    assert client.delete(
        f"/api/v1/tasks/{task_id}",
        headers=other_headers,
    ).status_code == 404
    assert client.get(f"/api/v1/tasks/{task_id}", headers=owner_headers).status_code == 200


def test_task_creation_notifies_websocket_client(client):
    headers = auth_header(client)
    with client.websocket_connect("/api/v1/ws/tasks/1", headers=headers) as websocket:
        response = client.post(
            "/api/v1/tasks/",
            json={"title": "Live task", "description": "Notify clients"},
            headers=headers,
        )
        assert response.status_code == 200
        assert websocket.receive_text() == "New task created: Live task"
