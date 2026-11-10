import os
import subprocess
import sys
from pathlib import Path

from app import clients
from conftest import auth


# ---------- favoritos ----------
def make_col(client, name="Sobremesas", user=2):
    r = client.post("/favorite-collections", json={"name": name}, headers=auth(user))
    assert r.status_code == 201, r.text
    return r.json()


def test_collections_crud_and_isolation(client):
    assert client.get("/favorite-collections").status_code == 401
    col = make_col(client, "Sobremesas")
    assert (col["name"], col["recipe_count"], col["recipe_ids"]) == ("Sobremesas", 0, [])
    make_col(client, "Jantares rápidos")
    assert [c["name"] for c in client.get("/favorite-collections", headers=auth(2)).json()] == ["Sobremesas", "Jantares rápidos"]
    assert client.get("/favorite-collections", headers=auth(3)).json() == []   # cada um vê só as suas

    assert client.post("/favorite-collections", json={"name": "sobremesas"}, headers=auth(2)).status_code == 409
    assert make_col(client, "Sobremesas", user=3)["id"]                            # outro utilizador pode repetir o nome
    for bad in ("", "  ", "x" * 61):
        assert client.post("/favorite-collections", json={"name": bad}, headers=auth(2)).status_code == 422


def test_add_remove_recipes(client):
    cid = make_col(client)["id"]
    r = client.post(f"/favorite-collections/{cid}/recipes/10", headers=auth(2))
    assert r.status_code == 201 and r.json()["recipe_ids"] == [10]
    client.post(f"/favorite-collections/{cid}/recipes/11", headers=auth(2))
    assert client.get(f"/favorite-collections/{cid}", headers=auth(2)).json()["recipe_ids"] == [11, 10]
    assert client.post(f"/favorite-collections/{cid}/recipes/10", headers=auth(2)).status_code == 409
    assert client.post(f"/favorite-collections/{cid}/recipes/999", headers=auth(2)).status_code == 404
    assert client.delete(f"/favorite-collections/{cid}/recipes/10", headers=auth(2)).status_code == 204
    assert client.delete(f"/favorite-collections/{cid}/recipes/10", headers=auth(2)).status_code == 404
    assert client.get("/favorite-collections", headers=auth(2)).json()[0]["recipe_count"] == 1


def test_cannot_touch_other_users_collections(client):
    cid = make_col(client, user=2)["id"]
    h = auth(3)
    assert client.get(f"/favorite-collections/{cid}", headers=h).status_code == 403
    assert client.post(f"/favorite-collections/{cid}/recipes/10", headers=h).status_code == 403
    assert client.delete(f"/favorite-collections/{cid}/recipes/10", headers=h).status_code == 403
    assert client.delete(f"/favorite-collections/{cid}", headers=h).status_code == 403
    assert client.get("/favorite-collections/999", headers=h).status_code == 404
    assert client.get("/favorite-collections", headers=auth(2)).json()[0]["id"] == cid


def test_delete_collection_removes_entries(client):
    cid = make_col(client)["id"]
    client.post(f"/favorite-collections/{cid}/recipes/10", headers=auth(2))
    assert client.delete(f"/favorite-collections/{cid}", headers=auth(2)).status_code == 204
    assert client.get(f"/favorite-collections/{cid}", headers=auth(2)).status_code == 404
    assert client.get("/favorite-collections", headers=auth(2)).json() == []
    make_col(client)  # nome libertado


def test_adding_favorite_returns_503_if_recipe_service_down(client, world):
    cid = make_col(client)["id"]
    world.down.add("recipes")
    clients.reset()
    assert client.post(f"/favorite-collections/{cid}/recipes/10", headers=auth(2)).status_code == 503
    assert client.get("/favorite-collections", headers=auth(2)).status_code == 200  # leitura continua


# ---------- partilhas ----------
def test_share_flow(client, world):
    assert client.post("/recipes/10/share", json={"recipient_username": "eva"}).status_code == 401
    r = client.post("/recipes/10/share", json={"recipient_username": "EVA"}, headers=auth(2))
    assert r.status_code == 201
    assert r.json()["recipient_id"] == 3 and r.json()["recipe_title"] == "Bolo de chocolate"

    got = client.get("/shares/received", headers=auth(3)).json()
    assert len(got) == 1
    assert (got[0]["sender_username"], got[0]["recipe_id"], got[0]["recipe_title"]) == ("rui", 10, "Bolo de chocolate")
    assert client.get("/shares/received", headers=auth(2)).json() == []
    assert client.get("/shares/received").status_code == 401

    ev = world.events()[-1]
    assert (ev["event_type"], ev["actor_id"], ev["recipe_id"], ev["recipe_owner_id"], ev["target_user_id"]) == ("share", 2, 10, 1, 3)


def test_share_rules(client, world):
    assert client.post("/recipes/10/share", json={"recipient_username": "rui"}, headers=auth(2)).status_code == 400
    assert client.post("/recipes/10/share", json={"recipient_username": "ninguem"}, headers=auth(2)).status_code == 404
    assert client.post("/recipes/999/share", json={"recipient_username": "eva"}, headers=auth(2)).status_code == 404
    assert client.post("/recipes/10/share", json={"recipient_username": ""}, headers=auth(2)).status_code == 422
    world.down.add("users")
    clients.reset()
    assert client.post("/recipes/10/share", json={"recipient_username": "eva"}, headers=auth(2)).status_code == 503
    assert client.get("/shares/received", headers=auth(3)).status_code == 200


def test_received_shares_degrade_without_other_services(client, world):
    client.post("/recipes/10/share", json={"recipient_username": "eva"}, headers=auth(2))
    world.down |= {"users", "recipes"}
    clients.reset()
    got = client.get("/shares/received", headers=auth(3)).json()
    assert got[0]["sender_username"] is None and got[0]["recipe_title"] is None and got[0]["recipe_id"] == 10


# ---------- mensagens ----------
def test_messages_flow_read_receipts_and_polling(client, world):
    assert client.post("/messages/3", json={"text": "olá"}).status_code == 401
    m1 = client.post("/messages/3", json={"text": " Olá Eva! "}, headers=auth(2))
    assert m1.status_code == 201 and m1.json()["text"] == "Olá Eva!" and m1.json()["read_at"] is None
    client.post("/messages/3", json={"text": "Viste o meu bolo?"}, headers=auth(2))

    convs = client.get("/messages/conversations", headers=auth(3)).json()
    assert len(convs) == 1
    assert (convs[0]["user_id"], convs[0]["username"], convs[0]["unread_count"]) == (2, "rui", 2)
    assert convs[0]["last_message"]["text"] == "Viste o meu bolo?"
    assert client.get("/messages/conversations", headers=auth(2)).json()[0]["unread_count"] == 0

    msgs = client.get("/messages/2", headers=auth(3)).json()                    # ler marca como lidas
    assert [m["text"] for m in msgs] == ["Olá Eva!", "Viste o meu bolo?"]
    assert client.get("/messages/conversations", headers=auth(3)).json()[0]["unread_count"] == 0
    assert all(m["read_at"] for m in client.get("/messages/3", headers=auth(2)).json())

    client.post("/messages/2", json={"text": "Vi! Parece ótimo"}, headers=auth(3))
    last = msgs[-1]["id"]
    new = client.get("/messages/3", params={"after_id": last}, headers=auth(2)).json()
    assert [m["text"] for m in new] == ["Vi! Parece ótimo"]                     # polling incremental

    ev = world.events()[-1]
    assert (ev["event_type"], ev["actor_id"], ev["target_user_id"], ev["recipe_id"]) == ("message", 3, 2, None)


def test_messages_are_private(client):
    client.post("/messages/3", json={"text": "segredo"}, headers=auth(2))
    assert client.get("/messages/2", headers=auth(1)).json() == []
    assert client.get("/messages/3", headers=auth(1)).json() == []
    assert client.get("/messages/conversations", headers=auth(1)).json() == []
    assert client.get("/messages/conversations", headers=auth(3)).json()[0]["unread_count"] == 1  # nada foi marcado


def test_message_rules_and_conversation_order(client):
    assert client.post("/messages/2", json={"text": "eu"}, headers=auth(2)).status_code == 400
    assert client.post("/messages/99", json={"text": "olá"}, headers=auth(2)).status_code == 404
    for bad in ("", "  ", "x" * 1001):
        assert client.post("/messages/3", json={"text": bad}, headers=auth(2)).status_code == 422
    client.post("/messages/3", json={"text": "para a eva"}, headers=auth(2))
    client.post("/messages/1", json={"text": "para a ana"}, headers=auth(2))
    assert [c["username"] for c in client.get("/messages/conversations", headers=auth(2)).json()] == ["ana", "eva"]
    assert client.get("/messages/3", params={"limit": 0}, headers=auth(2)).status_code == 422


# ---------- internos ----------
def test_internal_requires_token(client):
    assert client.delete("/internal/recipes/10/data").status_code == 401
    assert client.delete("/internal/recipes/10/data", headers={"X-Internal-Token": "x"}).status_code == 403
    assert client.delete("/internal/recipes/10/data", headers=auth(1)).status_code == 401  # JWT não serve


def test_purge_recipe_data(client, internal):
    cid = make_col(client)["id"]
    client.post(f"/favorite-collections/{cid}/recipes/10", headers=auth(2))
    client.post(f"/favorite-collections/{cid}/recipes/11", headers=auth(2))
    client.post("/recipes/10/comments", json={"text": "x"}, headers=auth(2))
    client.post("/recipes/10/like", headers=auth(2))
    client.post("/recipes/10/ratings", json={"score": 4}, headers=auth(2))
    client.post("/recipes/10/share", json={"recipient_username": "eva"}, headers=auth(2))

    assert client.delete("/internal/recipes/10/data", headers=internal).status_code == 204
    assert client.delete("/internal/recipes/10/data", headers=internal).status_code == 204  # idempotente
    s = client.get("/recipes/10/interactions", headers=auth(2)).json()
    assert (s["like_count"], s["comment_count"], s["rating"]["count"]) == (0, 0, 0)
    assert client.get(f"/favorite-collections/{cid}", headers=auth(2)).json()["recipe_ids"] == [11]
    assert client.get("/shares/received", headers=auth(3)).json() == []


def test_resync_counters_repairs_missed_push(client, world, internal):
    client.post("/recipes/10/like", headers=auth(2))
    client.post("/recipes/10/like", headers=auth(3))
    world.calls.clear()
    assert client.post("/internal/recipes/10/resync-counters", headers=internal).status_code == 204
    assert world.counter_pushes(10) == [{"like_count": 2, "comment_count": 0, "rating_count": 0, "rating_avg": None}]


def test_migration_matches_models(tmp_path):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine

    from app.database import Base

    db_file = tmp_path / "mig.db"
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_file}"}
    res = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root, env=env, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    with create_engine(f"sqlite:///{db_file}").connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == [], diff
