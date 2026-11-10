import os

# Tem de ser definido antes de importar a app.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret-with-at-least-32-bytes-length"
os.environ["INTERNAL_SERVICE_TOKEN"] = "test-internal"
os.environ["ACTIVITY_SERVICE_URL"] = ""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


def make_user(client, username="ana", email=None, password="segredo123"):
    email = email or f"{username}@example.com"
    r = client.post("/auth/register", json={"username": username, "email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()


def login(client, identifier="ana", password="segredo123"):
    r = client.post("/auth/login", json={"identifier": identifier, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def ana(client):
    user = make_user(client, "ana")
    return user, login(client, "ana")


@pytest.fixture
def rui(client):
    user = make_user(client, "rui")
    return user, login(client, "rui")


@pytest.fixture
def internal_headers():
    return {"X-Internal-Token": settings.internal_token}
