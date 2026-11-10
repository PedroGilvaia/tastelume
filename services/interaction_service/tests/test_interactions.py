from app import clients
from conftest import auth


# ---------- comentários ----------
def test_comments_flow(client, world):
    assert client.post("/recipes/10/comments", json={"text": "Boa!"}).status_code == 401
    r = client.post("/recipes/10/comments", json={"text": "  Ficou ótimo  "}, headers=auth(2))
    assert r.status_code == 201
    body = r.json()
    assert body["text"] == "Ficou ótimo" and body["username"] == "rui" and body["user_id"] == 2
    client.post("/recipes/10/comments", json={"text": "Também gostei"}, headers=auth(3))

    r = client.get("/recipes/10/comments")  # público
    assert r.status_code == 200 and r.headers["X-Total-Count"] == "2"
    assert [(c["username"], c["text"]) for c in r.json()] == [("eva", "Também gostei"), ("rui", "Ficou ótimo")]
    assert len(client.get("/recipes/10/comments", params={"limit": 1, "offset": 1}).json()) == 1
    assert client.get("/recipes/10/comments", params={"limit": 0}).status_code == 422
    assert world.counter_pushes(10)[-1]["comment_count"] == 2


def test_comment_validation_and_unknown_recipe(client):
    for text in ("", "   ", "x" * 1001):
        assert client.post("/recipes/10/comments", json={"text": text}, headers=auth(2)).status_code == 422
    assert client.post("/recipes/999/comments", json={"text": "olá"}, headers=auth(2)).status_code == 404


def test_only_author_edits_or_deletes_comment(client, world):
    cid = client.post("/recipes/10/comments", json={"text": "original"}, headers=auth(2)).json()["id"]
    assert client.patch(f"/comments/{cid}", json={"text": "x"}, headers=auth(3)).status_code == 403
    assert client.delete(f"/comments/{cid}", headers=auth(3)).status_code == 403
    assert client.patch(f"/comments/{cid}", json={"text": "x"}).status_code == 401
    r = client.patch(f"/comments/{cid}", json={"text": "editado"}, headers=auth(2))
    assert r.status_code == 200 and r.json()["text"] == "editado" and r.json()["updated_at"] is not None
    assert client.delete(f"/comments/{cid}", headers=auth(2)).status_code == 204
    assert client.get("/recipes/10/comments").json() == []
    assert world.counter_pushes(10)[-1]["comment_count"] == 0
    assert client.delete(f"/comments/{cid}", headers=auth(2)).status_code == 404


# ---------- likes ----------
def test_like_unlike_rules(client, world):
    assert client.post("/recipes/10/like").status_code == 401
    assert client.post("/recipes/999/like", headers=auth(2)).status_code == 404
    assert client.post("/recipes/10/like", headers=auth(2)).status_code == 204
    assert client.post("/recipes/10/like", headers=auth(2)).status_code == 409   # sem duplicados
    assert client.post("/recipes/10/like", headers=auth(3)).status_code == 204

    s = client.get("/recipes/10/interactions", headers=auth(2)).json()
    assert s["like_count"] == 2 and s["my_like"] is True
    assert client.get("/recipes/10/interactions").json()["my_like"] is None   # visitante
    assert world.counter_pushes(10)[-1]["like_count"] == 2

    assert client.delete("/recipes/10/like", headers=auth(2)).status_code == 204
    assert client.delete("/recipes/10/like", headers=auth(2)).status_code == 404
    assert client.get("/recipes/10/interactions", headers=auth(2)).json()["like_count"] == 1
    assert world.counter_pushes(10)[-1]["like_count"] == 1


# ---------- avaliações ----------
def test_ratings_one_per_user_updatable(client, world):
    assert client.get("/recipes/10/ratings").json() == {
        "average": None, "count": 0, "distribution": {str(i): 0 for i in range(1, 6)}, "my_score": None}

    r = client.post("/recipes/10/ratings", json={"score": 4}, headers=auth(2))
    assert r.status_code == 201 and r.json()["my_score"] == 4
    r = client.post("/recipes/10/ratings", json={"score": 2}, headers=auth(2))   # atualiza, não duplica
    assert r.status_code == 200 and r.json()["count"] == 1 and r.json()["average"] == 2.0
    client.post("/recipes/10/ratings", json={"score": 5}, headers=auth(3))
    client.post("/recipes/10/ratings", json={"score": 5}, headers=auth(1))

    s = client.get("/recipes/10/ratings", headers=auth(2)).json()
    assert s["count"] == 3 and s["average"] == 4.0 and s["my_score"] == 2
    assert s["distribution"] == {"1": 0, "2": 1, "3": 0, "4": 0, "5": 2}
    assert client.get("/recipes/10/ratings").json()["my_score"] is None
    assert world.counter_pushes(10)[-1] == {"like_count": 0, "comment_count": 0, "rating_count": 3, "rating_avg": 4.0}


def test_rating_validation(client):
    for bad in (0, 6, -1, "x", 4.5, None):
        assert client.post("/recipes/10/ratings", json={"score": bad}, headers=auth(2)).status_code == 422, bad
    assert client.post("/recipes/10/ratings", json={"score": 3}).status_code == 401
    assert client.post("/recipes/999/ratings", json={"score": 3}, headers=auth(2)).status_code == 404


# ---------- eventos e degradação ----------
def test_events_payloads(client, world):
    client.post("/recipes/10/comments", json={"text": "olá"}, headers=auth(2))
    client.post("/recipes/10/like", headers=auth(2))
    client.post("/recipes/10/ratings", json={"score": 5}, headers=auth(2))
    got = [(e["event_type"], e["actor_id"], e["recipe_id"], e["recipe_owner_id"], e["target_user_id"]) for e in world.events()]
    assert got == [("comment", 2, 10, 1, 1), ("like", 2, 10, 1, 1), ("rating", 2, 10, 1, 1)]


def test_activity_and_counter_failures_do_not_break_operations(client, world):
    world.down |= {"activity"}
    assert client.post("/recipes/10/like", headers=auth(2)).status_code == 204
    world.down |= {"recipes"}
    clients.reset()
    assert client.get("/recipes/10/interactions", headers=auth(2)).json()["like_count"] == 1
    assert client.get("/recipes/10/comments").status_code == 200


def test_writes_return_503_when_recipe_service_down_but_reads_work(client, world):
    client.post("/recipes/10/comments", json={"text": "antes"}, headers=auth(2))
    world.down.add("recipes")
    clients.reset()
    r = client.post("/recipes/10/comments", json={"text": "depois"}, headers=auth(2))
    assert r.status_code == 503 and "indisponível" in r.json()["detail"] and r.headers["Retry-After"]
    assert client.post("/recipes/10/like", headers=auth(2)).status_code == 503
    assert client.post("/recipes/10/ratings", json={"score": 5}, headers=auth(2)).status_code == 503
    assert [c["text"] for c in client.get("/recipes/10/comments").json()] == ["antes"]  # nada foi gravado a meio


def test_comment_usernames_degrade_when_users_service_down(client, world):
    client.post("/recipes/10/comments", json={"text": "olá"}, headers=auth(2))
    world.down.add("users")
    clients.reset()
    r = client.get("/recipes/10/comments")
    assert r.status_code == 200 and r.json()[0]["username"] is None


def test_circuit_breaker_stops_hammering_a_dead_service(client, world):
    world.down.add("recipes")
    clients.reset()
    for _ in range(3):
        assert client.post("/recipes/10/like", headers=auth(2)).status_code == 503
    attempts = [c for c in world.calls if "recipes.test" in c[1]]
    assert len(attempts) == 1   # após a 1.ª falha, os restantes pedidos nem tentam a rede


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "service": "interaction"}
