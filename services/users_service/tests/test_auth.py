import time

import jwt
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import User
from conftest import login, make_user


def test_register_ok_does_not_leak_password(client):
    data = make_user(client, "ana")
    assert data["username"] == "ana" and data["email"] == "ana@example.com"
    assert "password" not in data and "password_hash" not in data


def test_password_is_hashed_in_db(client):
    make_user(client, "ana", password="segredo123")
    with SessionLocal() as db:
        user = db.scalar(select(User))
        assert user.password_hash != "segredo123"
        assert user.password_hash.startswith("$2")


def test_duplicate_username_case_insensitive_and_email(client):
    make_user(client, "ana")
    r = client.post("/auth/register", json={"username": "ANA", "email": "outra@example.com", "password": "segredo123"})
    assert r.status_code == 409
    r = client.post("/auth/register", json={"username": "ana2", "email": "ANA@example.com", "password": "segredo123"})
    assert r.status_code == 409


def test_register_validation(client):
    bad = [
        {"username": "a", "email": "a@example.com", "password": "segredo123"},
        {"username": "ana!", "email": "a@example.com", "password": "segredo123"},
        {"username": "ana", "email": "nao-e-email", "password": "segredo123"},
        {"username": "ana", "email": "a@example.com", "password": "curta"},
        {"username": "ana", "email": "a@example.com", "password": "x" * 100},
    ]
    for body in bad:
        assert client.post("/auth/register", json=body).status_code == 422, body


def test_login_by_username_and_email(client):
    make_user(client, "ana")
    assert login(client, "ana")
    assert login(client, "ANA@example.com")


def test_login_invalid_credentials_same_message(client):
    make_user(client, "ana")
    wrong_pw = client.post("/auth/login", json={"identifier": "ana", "password": "errada123"})
    unknown = client.post("/auth/login", json={"identifier": "ninguem", "password": "errada123"})
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json()


def test_me_requires_valid_token(client, ana):
    assert client.get("/users/me").status_code == 401
    assert client.get("/users/me", headers={"Authorization": "Bearer lixo"}).status_code == 401
    r = client.get("/users/me", headers=ana[1])
    assert r.status_code == 200 and r.json()["username"] == "ana"


def test_expired_and_forged_tokens_rejected(client, ana):
    uid = ana[0]["id"]
    now = int(time.time())
    expired = jwt.encode({"sub": str(uid), "exp": now - 10}, settings.jwt_secret, algorithm="HS256")
    forged = jwt.encode({"sub": str(uid), "exp": now + 600}, "outro-segredo-com-pelo-menos-32-bytes-x", algorithm="HS256")
    for tok in (expired, forged):
        assert client.get("/users/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_token_of_unknown_user_rejected(client):
    tok = jwt.encode({"sub": "999", "exp": int(time.time()) + 600}, settings.jwt_secret, algorithm="HS256")
    assert client.get("/users/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
