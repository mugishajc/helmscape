from fastapi.testclient import TestClient

import pytest

from app.main import app, _users, _next_id
import app.main as m


@pytest.fixture(autouse=True)
def reset_state():
    m._users.clear()
    m._next_id = 1
    yield


def test_healthz():
    client = TestClient(app)
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_and_get_user():
    client = TestClient(app)
    r = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Alice"
    assert body["email"] == "alice@example.com"
    assert body["id"] == 1

    got = client.get(f"/users/{body['id']}")
    assert got.status_code == 200
    assert got.json()["email"] == "alice@example.com"


def test_list_users():
    client = TestClient(app)
    client.post("/users", json={"name": "A", "email": "a@example.com"})
    client.post("/users", json={"name": "B", "email": "b@example.com"})
    users = client.get("/users").json()
    assert len(users) == 2


def test_duplicate_email_rejected():
    client = TestClient(app)
    client.post("/users", json={"name": "A", "email": "dup@example.com"})
    r = client.post("/users", json={"name": "B", "email": "dup@example.com"})
    assert r.status_code == 409


def test_invalid_email_rejected():
    client = TestClient(app)
    r = client.post("/users", json={"name": "Bad", "email": "not-an-email"})
    assert r.status_code == 422


def test_blank_name_rejected():
    client = TestClient(app)
    r = client.post("/users", json={"name": "  ", "email": "ok@example.com"})
    assert r.status_code == 422


def test_delete_user():
    client = TestClient(app)
    r = client.post("/users", json={"name": "Del", "email": "del@example.com"})
    uid = r.json()["id"]
    assert client.delete(f"/users/{uid}").status_code == 204
    assert client.get(f"/users/{uid}").status_code == 404


def test_get_nonexistent_user():
    client = TestClient(app)
    assert client.get("/users/999").status_code == 404
