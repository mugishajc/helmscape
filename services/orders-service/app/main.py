"""Orders service: creates orders by looking up items in the catalog service."""
from __future__ import annotations

import os
from typing import Dict

import httpx
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel
from starlette.responses import Response

CATALOG_URL = os.getenv("CATALOG_URL", "http://catalog-service:8000")
SERVICE_NAME = os.getenv("SERVICE_NAME", "orders-service")

app = FastAPI(title="orders-service")
orders_created = Counter("orders_created_total", "Orders created")
orders_failed = Counter("orders_failed_total", "Orders rejected", ["reason"])

_orders: Dict[int, dict] = {}
_next_id = 1


class OrderIn(BaseModel):
    item_id: int
    quantity: int


class Order(BaseModel):
    id: int
    item_id: int
    quantity: int
    unit_price: float
    total: float


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/readyz")
async def readyz() -> dict:
    # Readiness checks the catalog dependency is reachable.
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            r = await client.get(f"{CATALOG_URL}/healthz")
            r.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(503, f"catalog not ready: {exc}") from exc
    return {"status": "ready"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/orders", response_model=Order, status_code=201)
async def create_order(payload: OrderIn) -> Order:
    global _next_id
    if payload.quantity <= 0:
        orders_failed.labels(reason="bad_quantity").inc()
        raise HTTPException(400, "quantity must be positive")

    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            r = await client.get(f"{CATALOG_URL}/items/{payload.item_id}")
        except httpx.HTTPError as exc:
            orders_failed.labels(reason="catalog_unreachable").inc()
            raise HTTPException(502, f"catalog call failed: {exc}") from exc
        if r.status_code == 404:
            orders_failed.labels(reason="unknown_item").inc()
            raise HTTPException(404, "item not found")
        r.raise_for_status()
        item = r.json()

    order_id = _next_id
    _next_id += 1
    total = round(item["price"] * payload.quantity, 2)
    order = {
        "id": order_id,
        "item_id": payload.item_id,
        "quantity": payload.quantity,
        "unit_price": item["price"],
        "total": total,
    }
    _orders[order_id] = order
    orders_created.inc()
    return Order(**order)


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: int) -> Order:
    if order_id not in _orders:
        raise HTTPException(404, "order not found")
    return Order(**_orders[order_id])
