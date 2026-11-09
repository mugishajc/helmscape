from fastapi.testclient import TestClient

from app.main import app


def test_healthz():
    assert TestClient(app).get("/healthz").json()["status"] == "ok"


def test_list_items():
    body = TestClient(app).get("/items").json()
    assert len(body) >= 3
    assert {i["id"] for i in body} >= {1, 2, 3}


def test_get_item_hit_and_miss():
    client = TestClient(app)
    assert client.get("/items/1").status_code == 200
    assert client.get("/items/999").status_code == 404
