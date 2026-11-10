"""Users service: account management for the shop platform."""
from __future__ import annotations

import os
import re
from typing import Dict

from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel, field_validator
from starlette.responses import Response

SERVICE_NAME = os.getenv("SERVICE_NAME", "users-service")

app = FastAPI(title="users-service")
users_created = Counter("users_created_total", "Users created")

_users: Dict[int, dict] = {}
_next_id = 1

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserIn(BaseModel):
    name: str
    email: str

    @field_validator("email")
    @classmethod
    def email_format(cls, v: str) -> str:
        if not EMAIL_RE.match(v):
            raise ValueError("invalid email format")
        return v.lower()

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v.strip()


class User(BaseModel):
    id: int
    name: str
    email: str


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/readyz")
def readyz() -> dict:
    return {"status": "ready"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/users", response_model=list[User])
def list_users() -> list[User]:
    return [User(**u) for u in _users.values()]


@app.post("/users", response_model=User, status_code=201)
def create_user(payload: UserIn) -> User:
    global _next_id

    # Reject duplicate emails.
    for u in _users.values():
        if u["email"] == payload.email:
            raise HTTPException(409, "email already registered")

    user_id = _next_id
    _next_id += 1
    user = {"id": user_id, "name": payload.name, "email": payload.email}
    _users[user_id] = user
    users_created.inc()
    return User(**user)


@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int) -> User:
    if user_id not in _users:
        raise HTTPException(404, "user not found")
    return User(**_users[user_id])


@app.delete("/users/{user_id}", status_code=204, response_model=None)
def delete_user(user_id: int):
    if user_id not in _users:
        raise HTTPException(404, "user not found")
    del _users[user_id]
