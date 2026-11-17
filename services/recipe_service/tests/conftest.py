import os
import tempfile

_IMG_DIR = tempfile.mkdtemp(prefix="tastelume-img-")
os.environ.update(
    DATABASE_URL="sqlite://",
    JWT_SECRET="test-secret-with-at-least-32-bytes-length",
    INTERNAL_SERVICE_TOKEN="test-internal",
    USERS_SERVICE_URL="http://users.test",
    ACTIVITY_SERVICE_URL="",
    IMAGE_DIR=_IMG_DIR,
)

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.categories import ensure_categories
from app.clients import users_client
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.main import app

USERS = {
    1: {"id": 1, "username": "ana", "interests": ["Sobremesas"]},
    2: {"id": 2, "username": "rui", "interests": []},
    3: {"id": 3, "username": "eva", "interests": []},
}

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def auth(user_id: int) -> dict:
    token = jwt.encode(
        {"sub": str(user_id), "username": USERS[user_id]["username"], "exp": int(time.time()) + 600},
        settings.jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def fresh_state(monkeypatch):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_categories(db)
    users_client.reset()
    monkeypatch.setattr(users_client, "_fetch", lambda ids: {i: USERS[i] for i in ids if i in USERS})
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def internal():
    return {"X-Internal-Token": settings.internal_token}


def recipe_body(**over) -> dict:
    body = {
        "title": "Bolo de chocolate",
        "description": "Fofo e húmido",
        "category": "sobremesas",
        "ingredients": [
            {"name": "Farinha", "quantity": 200, "unit": "g"},
            {"name": "Chocolate negro", "quantity": 150, "unit": "g"},
            {"name": "Ovos", "quantity": 3, "unit": None},
        ],
        "preparation_steps": ["Pré-aquecer o forno.", "Misturar tudo.", "Cozer 35 minutos."],
        "preparation_time": 50,
        "servings": 8,
        "difficulty": "facil",
        "tags": ["Chocolate", "forno"],
    }
    body.update(over)
    return body


def create(client, user_id=1, **over) -> dict:
    r = client.post("/recipes", json=recipe_body(**over), headers=auth(user_id))
    assert r.status_code == 201, r.text
    return r.json()
