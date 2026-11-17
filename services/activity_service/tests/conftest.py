import os

os.environ.update(
    DATABASE_URL="sqlite://",
    JWT_SECRET="test-secret-with-at-least-32-bytes-length",
    INTERNAL_SERVICE_TOKEN="test-internal",
    USERS_SERVICE_URL="http://users.test",
    RECIPE_SERVICE_URL="http://recipes.test",
)

import re
import time
from urllib.parse import urlparse

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from app import clients
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Event

USERS = {1: "ana", 2: "rui", 3: "eva"}
RECIPES = {10: {"id": 10, "author_id": 1, "title": "Bolo de chocolate"},
           11: {"id": 11, "author_id": 1, "title": "Sopa de legumes"},
           12: {"id": 12, "author_id": 2, "title": "Arroz de pato"}}


class World:
    """Simula Users e Recipe Service ao nível do HTTP."""

    def __init__(self):
        self.calls: list[str] = []
        self.down: set[str] = set()  # "users" | "recipes"
        self.followers = {1: [2, 3], 2: [3], 3: []}

    def __call__(self, method, url, headers=None, timeout=None, params=None, **kw):
        service = urlparse(url).netloc.split(".")[0]
        path = urlparse(url).path
        self.calls.append(url)
        if service in self.down:
            raise httpx.ConnectError("down")
        assert method == "GET"
        assert headers and headers["X-Internal-Token"] == settings.internal_token
        ok = lambda body=None, code=200: httpx.Response(code, json=body)
        if service == "users":
            if m := re.fullmatch(r"/internal/users/(\d+)/follower-ids", path):
                return ok(self.followers.get(int(m.group(1)), []))
            if path == "/internal/users":
                ids = {int(x) for x in params["ids"].split(",")}
                return ok([{"id": i, "username": USERS[i], "interests": []} for i in ids if i in USERS])
        if service == "recipes" and path == "/internal/recipes":
            ids = {int(x) for x in params["ids"].split(",")}
            return ok([r for i, r in RECIPES.items() if i in ids])
        raise AssertionError(f"pedido inesperado {method} {url}")


def auth(user_id: int) -> dict:
    token = jwt.encode({"sub": str(user_id), "username": USERS[user_id], "exp": int(time.time()) + 600},
                       settings.jwt_secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def world(monkeypatch):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    clients.reset()
    w = World()
    monkeypatch.setattr("app.clients.httpx.request", w)
    return w


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def internal():
    return {"X-Internal-Token": settings.internal_token}


@pytest.fixture
def send(client, internal):
    """Envia um evento como faria outro serviço."""
    def _send(event_type, actor_id=None, recipe_id=None, recipe_owner_id=None, target_user_id=None):
        r = client.post("/internal/events", headers=internal, json={
            "event_type": event_type, "actor_id": actor_id, "recipe_id": recipe_id,
            "recipe_owner_id": recipe_owner_id, "target_user_id": target_user_id,
        })
        assert r.status_code == 201, r.text
        return r.json()
    return _send


def backdate(days: int, event_type: str | None = None) -> None:
    """Recua a data dos eventos (para testar janelas de tempo)."""
    from datetime import timedelta
    with SessionLocal() as db:
        for ev in db.query(Event).all():
            if event_type is None or ev.event_type == event_type:
                ev.created_at = ev.created_at - timedelta(days=days)
        db.commit()
