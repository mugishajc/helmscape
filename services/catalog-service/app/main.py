"""Catalog service: item lookup for the orders service."""
from __future__ import annotations

import os
from typing import Dict

from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel
from starlette.responses import Response

SERVICE_NAME = os.getenv("SERVICE_NAME", "catalog-service")

app = FastAPI(title="catalog-service")
item_lookups = Counter("catalog_item_lookups_total", "Catalog lookups", ["result"])


class Item(BaseModel):
    id: int
    name: str
    price: float


ITEMS: Dict[int, Item] = {
    1: Item(id=1, name="Enamel mug", price=7.5),
    2: Item(id=2, name="Notebook", price=4.0),
    3: Item(id=3, name="Mechanical pencil", price=2.25),
}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/readyz")
def readyz() -> dict:
    return {"status": "ready"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/items", response_model=list[Item])
def list_items() -> list[Item]:
    return list(ITEMS.values())


@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int) -> Item:
    item = ITEMS.get(item_id)
    if not item:
        item_lookups.labels(result="miss").inc()
        raise HTTPException(404, "item not found")
    item_lookups.labels(result="hit").inc()
    return item
