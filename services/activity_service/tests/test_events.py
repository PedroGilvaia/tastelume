from conftest import auth


def test_events_require_internal_token(client):
    body = {"event_type": "like", "actor_id": 2, "recipe_id": 10, "recipe_owner_id": 1, "target_user_id": 1}
    assert client.post("/internal/events", json=body).status_code == 401
    assert client.post("/internal/events", json=body, headers={"X-Internal-Token": "errado"}).status_code == 403
    # Um JWT de utilizador não dá acesso a endpoints internos.
    assert client.post("/internal/events", json=body, headers=auth(2)).status_code == 401


def test_event_validation(client, internal):
    bad = [
        {"event_type": "desconhecido", "actor_id": 1},
        {"event_type": "like", "actor_id": 0},
        {"event_type": "like", "actor_id": "x"},
        {"actor_id": 1},
    ]
    for body in bad:
        assert client.post("/internal/events", json=body, headers=internal).status_code == 422, body


def test_like_notifies_recipe_owner_but_not_self(send, client):
    assert send("like", 2, 10, 1, 1)["notifications_created"] == 1
    assert send("like", 1, 10, 1, 1)["notifications_created"] == 0  # gostar da própria receita
    assert client.get("/notifications/unread-count", headers=auth(1)).json() == {"unread": 1}
    assert client.get("/notifications/unread-count", headers=auth(2)).json() == {"unread": 0}


def test_owner_is_used_when_target_is_missing(send, client):
    """Recipe Service não envia target_user_id: nos tipos sobre receitas usa-se o dono."""
    assert send("comment", 2, 10, 1)["notifications_created"] == 1
    assert client.get("/notifications", headers=auth(1)).json()[0]["type"] == "comment"


def test_view_only_counts_for_stats(send, client):
    assert send("view", None, 10, 1)["notifications_created"] == 0  # visitante anónimo
    assert send("view", 2, 10, 1)["notifications_created"] == 0
    assert client.get("/notifications", headers=auth(1)).json() == []
    assert client.get("/stats/me", headers=auth(1)).json()["totals"]["views"] == 2


def test_follow_and_message_ignore_recipe_owner(send, client):
    """O Users Service envia recipe_owner_id = utilizador seguido; não pode contar como receita."""
    send("follow", 2, None, 1, 1)
    send("message", 3, None, None, 1)
    kinds = sorted(n["type"] for n in client.get("/notifications", headers=auth(1)).json())
    assert kinds == ["follow", "message"]
    stats = client.get("/stats/me", headers=auth(1)).json()["totals"]
    assert stats["new_followers"] == 1 and stats["views"] == 0
    assert client.get("/stats/me/top-recipes", headers=auth(1)).json() == []


def test_unread_duplicates_are_collapsed(send, client):
    send("like", 2, 10, 1, 1)
    assert send("like", 2, 10, 1, 1)["notifications_created"] == 0       # gostar, retirar e gostar outra vez
    assert send("like", 2, 11, 1, 1)["notifications_created"] == 1       # outra receita
    assert send("like", 3, 10, 1, 1)["notifications_created"] == 1       # outra pessoa
    send("message", 2, None, None, 1)
    assert send("message", 2, None, None, 1)["notifications_created"] == 0
    # Comentários e partilhas são sempre distintos.
    assert send("comment", 2, 10, 1, 1)["notifications_created"] == 1
    assert send("comment", 2, 10, 1, 1)["notifications_created"] == 1
    # Depois de lida, volta a notificar.
    assert client.post("/notifications/read-all", headers=auth(1)).status_code == 204
    assert send("like", 2, 10, 1, 1)["notifications_created"] == 1


def test_recipe_created_notifies_followers(send, client):
    ack = send("recipe_created", 1, 10, 1)
    assert ack["notifications_created"] == 2  # rui e eva seguem a ana
    for uid in (2, 3):
        n = client.get("/notifications", headers=auth(uid)).json()
        assert [(x["type"], x["recipe_id"], x["actor_username"]) for x in n] == [("recipe_created", 10, "ana")]
    assert client.get("/notifications", headers=auth(1)).json() == []  # o autor não se notifica


def test_recipe_created_survives_users_service_down(send, client, world):
    world.down.add("users")
    ack = send("recipe_created", 1, 10, 1)
    assert ack["notifications_created"] == 0 and ack["event_id"] >= 1   # evento guardado, sem erro
    assert client.get("/stats/me", headers=auth(1)).json()["totals"]["recipes_published"] == 1


def test_fanout_is_capped(send, world, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "max_fanout", 1)
    assert send("recipe_created", 1, 10, 1)["notifications_created"] == 1


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "service": "activity"}
