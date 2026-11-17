import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

from app.config import settings
from app.database import SessionLocal
from app.models import ViewLog, utcnow
from conftest import JPG, PNG, auth, create


# ---------- visualizações ----------
def test_view_counted_once_per_window_per_viewer(client):
    rid = create(client, 1)["id"]
    r = client.post(f"/recipes/{rid}/view", headers=auth(2))
    assert r.json() == {"counted": True, "view_count": 1}
    r = client.post(f"/recipes/{rid}/view", headers=auth(2))      # repetido (rebuild da UI)
    assert r.json() == {"counted": False, "view_count": 1}
    r = client.post(f"/recipes/{rid}/view", headers=auth(3))      # outro utilizador
    assert r.json() == {"counted": True, "view_count": 2}
    assert client.get(f"/recipes/{rid}").json()["view_count"] == 2


def test_author_views_not_counted_and_unknown_recipe(client):
    rid = create(client, 1)["id"]
    assert client.post(f"/recipes/{rid}/view", headers=auth(1)).json()["counted"] is False
    assert client.post("/recipes/999/view").status_code == 404


def test_anonymous_views_keyed_by_client_id(client):
    rid = create(client, 1)["id"]
    h1, h2 = {"X-Client-Id": "dispositivo-1"}, {"X-Client-Id": "dispositivo-2"}
    assert client.post(f"/recipes/{rid}/view", headers=h1).json()["counted"] is True
    assert client.post(f"/recipes/{rid}/view", headers=h1).json()["counted"] is False
    assert client.post(f"/recipes/{rid}/view", headers=h2).json()["counted"] is True


def test_view_counted_again_after_window(client):
    rid = create(client, 1)["id"]
    client.post(f"/recipes/{rid}/view", headers=auth(2))
    with SessionLocal() as db:
        log = db.get(ViewLog, (rid, "u:2"))
        log.last_counted_at = utcnow() - timedelta(minutes=settings.view_window_minutes + 1)
        db.commit()
    assert client.post(f"/recipes/{rid}/view", headers=auth(2)).json() == {"counted": True, "view_count": 2}


# ---------- imagens ----------
def upload(client, rid, data, name="foto.png", ctype="image/png", user=1):
    return client.post(f"/recipes/{rid}/image", files={"file": (name, data, ctype)}, headers=auth(user))


def test_image_upload_serve_and_replace(client):
    rid = create(client, 1)["id"]
    r = upload(client, rid, PNG)
    assert r.status_code == 200
    url = r.json()["image_url"]
    assert url.startswith("/images/") and url.endswith(".png")
    served = client.get(url)
    assert served.status_code == 200 and served.content == PNG
    assert served.headers["content-type"] == "image/png"
    assert served.headers["x-content-type-options"] == "nosniff"

    new_url = upload(client, rid, JPG, "outra.jpg", "image/jpeg").json()["image_url"]
    assert new_url != url and new_url.endswith(".jpg")
    assert client.get(url).status_code == 404       # a antiga foi removida do volume
    assert client.get(new_url).status_code == 200


def test_image_rules(client):
    rid = create(client, 1)["id"]
    assert upload(client, rid, PNG, user=2).status_code == 403                       # não é o autor
    assert client.post(f"/recipes/{rid}/image", files={"file": ("a.png", PNG, "image/png")}).status_code == 401
    assert upload(client, rid, b"<?php echo 1; ?>", "x.png", "image/png").status_code == 415  # conteúdo falso
    assert upload(client, rid, b"GIF89a" + b"\0" * 20, "x.gif", "image/gif").status_code == 415
    assert upload(client, 999, PNG).status_code == 404
    big = PNG + b"\x00" * settings.max_image_bytes
    assert upload(client, rid, big).status_code == 413


def test_image_name_ignores_client_filename_and_blocks_traversal(client):
    rid = create(client, 1)["id"]
    url = upload(client, rid, PNG, name="../../etc/passwd.png").json()["image_url"]
    assert ".." not in url and "passwd" not in url
    for bad in ("../secret.png", "..%2Fsecret.png", "abc.png", "x" * 32 + ".png", "a" * 32 + ".exe"):
        assert client.get(f"/images/{bad}").status_code == 404, bad


def test_delete_recipe_removes_image_file(client):
    rid = create(client, 1)["id"]
    name = upload(client, rid, PNG).json()["image_url"].split("/")[-1]
    path = Path(settings.image_dir) / name
    assert path.exists()
    assert client.delete(f"/recipes/{rid}", headers=auth(1)).status_code == 204
    assert not path.exists()


# ---------- endpoints internos ----------
def test_internal_requires_token(client, internal):
    rid = create(client, 1)["id"]
    assert client.get(f"/internal/recipes/{rid}").status_code == 401
    assert client.get(f"/internal/recipes/{rid}", headers={"X-Internal-Token": "x"}).status_code == 403
    assert client.get(f"/internal/recipes/{rid}", headers=auth(1)).status_code == 401  # JWT não serve
    assert client.put(f"/internal/recipes/{rid}/counters", json={"like_count": 1}).status_code == 401
    assert client.get(f"/internal/recipes/{rid}", headers=internal).json() == {
        "id": rid, "author_id": 1, "title": "Bolo de chocolate"}


def test_internal_lookup_many_and_errors(client, internal):
    a, b = create(client, 1)["id"], create(client, 2)["id"]
    got = client.get("/internal/recipes", params={"ids": f"{a},{b},999"}, headers=internal).json()
    assert sorted(x["id"] for x in got) == sorted([a, b])
    assert client.get("/internal/recipes", params={"ids": "x"}, headers=internal).status_code == 400
    assert client.get("/internal/recipes/999", headers=internal).status_code == 404


def test_counters_are_absolute_and_idempotent(client, internal):
    rid = create(client, 1)["id"]
    body = {"like_count": 3, "comment_count": 2, "rating_count": 4, "rating_avg": 4.25}
    for _ in range(2):  # repetir não acumula
        assert client.put(f"/internal/recipes/{rid}/counters", json=body, headers=internal).status_code == 204
    d = client.get(f"/recipes/{rid}").json()
    assert (d["like_count"], d["comment_count"], d["rating_count"], d["rating_avg"]) == (3, 2, 4, 4.25)

    # sem avaliações volta a "não classificada"
    client.put(f"/internal/recipes/{rid}/counters", json={"rating_count": 0, "rating_avg": None}, headers=internal)
    d = client.get(f"/recipes/{rid}").json()
    assert d["rating_count"] == 0 and d["rating_avg"] is None

    for bad in ({"like_count": -1}, {"rating_avg": 6}, {"rating_avg": 0.5}):
        assert client.put(f"/internal/recipes/{rid}/counters", json=bad, headers=internal).status_code == 422
    assert client.put("/internal/recipes/999/counters", json={}, headers=internal).status_code == 404


# ---------- eventos e degradação ----------
def test_events_emitted_for_create_and_view(client, monkeypatch):
    sent = []
    monkeypatch.setattr("app.clients.httpx.post", lambda url, **kw: sent.append((url, kw["json"], kw["headers"])))
    monkeypatch.setattr(settings, "activity_service_url", "http://activity.test")
    rid = create(client, 1)["id"]
    client.post(f"/recipes/{rid}/view", headers=auth(2))
    client.post(f"/recipes/{rid}/view", headers=auth(2))  # repetida: sem evento
    types = [(j["event_type"], j["actor_id"], j["recipe_id"], j["recipe_owner_id"]) for _, j, _ in sent]
    assert types == [("recipe_created", 1, rid, 1), ("view", 2, rid, 1)]
    assert all(u == "http://activity.test/internal/events" for u, _, _ in sent)
    assert all(h["X-Internal-Token"] == settings.internal_token for _, _, h in sent)


def test_activity_service_down_does_not_break_recipes(client, monkeypatch):
    monkeypatch.setattr(settings, "activity_service_url", "http://127.0.0.1:9")
    monkeypatch.setattr(settings, "http_timeout", 0.5)
    rid = create(client, 1)["id"]
    assert client.post(f"/recipes/{rid}/view", headers=auth(2)).json()["counted"] is True
    assert client.get(f"/recipes/{rid}").json()["view_count"] == 1


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok", "service": "recipe"}


# ---------- migração ----------
def test_migration_matches_models(tmp_path):
    """A migração Alembic tem de produzir exatamente o esquema dos modelos."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine

    from app.database import Base

    db_file = tmp_path / "mig.db"
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_file}"}
    res = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root, env=env,
                         capture_output=True, text=True)
    assert res.returncode == 0, res.stderr

    engine = create_engine(f"sqlite:///{db_file}")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == [], diff
