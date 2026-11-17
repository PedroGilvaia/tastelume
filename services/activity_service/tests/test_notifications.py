from conftest import auth


def test_notifications_require_auth(client):
    for method, path in (("get", "/notifications"), ("get", "/notifications/unread-count"),
                         ("post", "/notifications/read-all"), ("post", "/notifications/1/read")):
        assert getattr(client, method)(path).status_code == 401, path


def test_list_is_enriched_newest_first_and_paginated(send, client):
    send("like", 2, 10, 1, 1)
    send("comment", 3, 11, 1, 1)
    send("follow", 2, None, 1, 1)
    r = client.get("/notifications", headers=auth(1))
    assert r.status_code == 200
    assert r.headers["X-Total-Count"] == "3" and r.headers["X-Unread-Count"] == "3"
    body = r.json()
    assert [n["type"] for n in body] == ["follow", "comment", "like"]
    assert body[0]["text"] == "rui começou a seguir-te."
    assert body[1]["text"] == "eva comentou a tua receita «Sopa de legumes»."
    assert body[2]["recipe_title"] == "Bolo de chocolate" and body[2]["read"] is False

    page = client.get("/notifications", params={"limit": 1, "offset": 1}, headers=auth(1)).json()
    assert [n["type"] for n in page] == ["comment"]
    assert client.get("/notifications", params={"limit": 0}, headers=auth(1)).status_code == 422
    assert client.get("/notifications", params={"limit": 101}, headers=auth(1)).status_code == 422


def test_read_flow_and_unread_filter(send, client):
    send("like", 2, 10, 1, 1)
    send("comment", 3, 10, 1, 1)
    first = client.get("/notifications", headers=auth(1)).json()[1]["id"]
    assert client.post(f"/notifications/{first}/read", headers=auth(1)).status_code == 204
    assert client.post(f"/notifications/{first}/read", headers=auth(1)).status_code == 204  # idempotente
    assert client.get("/notifications/unread-count", headers=auth(1)).json() == {"unread": 1}

    unread = client.get("/notifications", params={"unread_only": True}, headers=auth(1))
    assert unread.headers["X-Total-Count"] == "1" and [n["type"] for n in unread.json()] == ["comment"]
    everything = client.get("/notifications", headers=auth(1))
    assert everything.headers["X-Total-Count"] == "2" and everything.headers["X-Unread-Count"] == "1"

    assert client.post("/notifications/read-all", headers=auth(1)).status_code == 204
    assert client.get("/notifications/unread-count", headers=auth(1)).json() == {"unread": 0}


def test_users_cannot_touch_each_others_notifications(send, client):
    send("like", 2, 10, 1, 1)
    nid = client.get("/notifications", headers=auth(1)).json()[0]["id"]
    assert client.post(f"/notifications/{nid}/read", headers=auth(3)).status_code == 404
    assert client.post("/notifications/9999/read", headers=auth(1)).status_code == 404
    assert client.post("/notifications/read-all", headers=auth(3)).status_code == 204
    assert client.get("/notifications/unread-count", headers=auth(1)).json() == {"unread": 1}  # intacta
    assert client.get("/notifications", headers=auth(3)).json() == []


def test_list_degrades_gracefully_without_other_services(send, client, world):
    send("like", 2, 10, 1, 1)
    send("follow", 3, None, None, 1)
    world.down.update({"users", "recipes"})
    r = client.get("/notifications", headers=auth(1))
    assert r.status_code == 200
    by_type = {n["type"]: n for n in r.json()}
    assert by_type["like"]["text"] == "Alguém gostou da tua receita."
    assert by_type["like"]["actor_username"] is None and by_type["like"]["recipe_title"] is None
    assert by_type["follow"]["text"] == "Alguém começou a seguir-te."
    assert client.get("/notifications/unread-count", headers=auth(1)).json() == {"unread": 2}


def test_invalid_token_is_rejected(client):
    r = client.get("/notifications", headers={"Authorization": "Bearer lixo"})
    assert r.status_code == 401
