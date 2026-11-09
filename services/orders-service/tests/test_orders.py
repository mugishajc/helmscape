from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app


class FakeTransport(httpx.AsyncBaseTransport):
    """Stands in for the catalog service during tests."""

    def __init__(self, items: dict[int, dict]):
        self.items = items

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/healthz":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path.startswith("/items/"):
            item_id = int(request.url.path.rsplit("/", 1)[-1])
            if item_id in self.items:
                return httpx.Response(200, json=self.items[item_id])
            return httpx.Response(404)
        return httpx.Response(404)


@pytest.fixture(autouse=True)
def patch_httpx(monkeypatch):
    transport = FakeTransport({1: {"id": 1, "name": "Mug", "price": 7.5}})
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr("app.main.httpx.AsyncClient", factory)
    # Reset in-memory state between tests.
    from app import main as m
    m._orders.clear()
    m._next_id = 1


def test_healthz():
    client = TestClient(app)
    assert client.get("/healthz").json()["status"] == "ok"


def test_create_order_rejects_zero_quantity():
    client = TestClient(app)
    r = client.post("/orders", json={"item_id": 1, "quantity": 0})
    assert r.status_code == 400


def test_create_order_computes_total():
    client = TestClient(app)
    r = client.post("/orders", json={"item_id": 1, "quantity": 3})
    assert r.status_code == 201
    body = r.json()
    assert body["unit_price"] == 7.5
    assert body["total"] == 22.5

    got = client.get(f"/orders/{body['id']}")
    assert got.status_code == 200
    assert got.json()["quantity"] == 3


def test_create_order_unknown_item():
    client = TestClient(app)
    r = client.post("/orders", json={"item_id": 999, "quantity": 1})
    assert r.status_code == 404
