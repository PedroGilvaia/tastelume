import os

os.environ.update(
    DATABASE_URL="sqlite://",
    JWT_SECRET="test-secret-with-at-least-32-bytes-length",
    INTERNAL_SERVICE_TOKEN="test-internal",
    USERS_SERVICE_URL="http://users.test",
    RECIPE_SERVICE_URL="http://recipes.test",
    ACTIVITY_SERVICE_URL="http://activity.test",
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
from app.database import Base, engine
from app.main import app

USERS = {1: "ana", 2: "rui", 3: "eva"}
RECIPES = {10: {"id": 10, "author_id": 1, "title": "Bolo de chocolate"},
           11: {"id": 11, "author_id": 2, "title": "Sopa de legumes"}}


class World:
    """Simula Users, Recipe e Activity Service ao nível do HTTP."""

    def __init__(self):
        self.calls: list[tuple[str, str, dict | None]] = []
        self.down: set[str] = set()      # "users" | "recipes" | "activity"
        self.recipes = {k: dict(v) for k, v in RECIPES.items()}

    def events(self):
        return [j for m, u, j in self.calls if u.endswith("/internal/events")]

    def counter_pushes(self, rid):
        return [j for m, u, j in self.calls if m == "PUT" and u.endswith(f"/recipes/{rid}/counters")]

    def __call__(self, method, url, headers=None, timeout=None, json=None, params=None, **kw):
        service = urlparse(url).netloc.split(".")[0]
        path = urlparse(url).path
        self.calls.append((method, url, json))
        if service in self.down:
            raise httpx.ConnectError("down")
        assert headers and headers["X-Internal-Token"] == settings.internal_token
        ok = lambda body=None, code=200: httpx.Response(code, json=body)
        if service == "activity":
            return ok({})
        if service == "users":
            if m := re.fullmatch(r"/internal/users/by-username/(.+)", path):
                for i, n in USERS.items():
                    if n == m.group(1).lower():
                        return ok({"id": i, "username": n, "interests": []})
                return ok({"detail": "x"}, 404)
            if m := re.fullmatch(r"/internal/users/(\d+)", path):
                i = int(m.group(1))
                return ok({"id": i, "username": USERS[i], "interests": []}) if i in USERS else ok({}, 404)
            if path == "/internal/users":
                ids = {int(x) for x in params["ids"].split(",")}
                return ok([{"id": i, "username": USERS[i], "interests": []} for i in ids if i in USERS])
        if service == "recipes":
            if method == "PUT":
                return httpx.Response(204)
            if m := re.fullmatch(r"/internal/recipes/(\d+)", path):
                r = self.recipes.get(int(m.group(1)))
                return ok(r) if r else ok({}, 404)
            if path == "/internal/recipes":
                ids = {int(x) for x in params["ids"].split(",")}
                return ok([r for i, r in self.recipes.items() if i in ids])
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
