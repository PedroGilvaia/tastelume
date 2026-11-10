from app.config import settings


def test_follow_unfollow_flow_and_counts(client, ana, rui):
    (a, ha), (r, hr) = ana, rui
    assert client.post(f"/users/{r['id']}/follow", headers=ha).status_code == 204

    profile = client.get(f"/users/{r['id']}", headers=ha).json()
    assert profile["followers_count"] == 1 and profile["is_following"] is True
    assert client.get(f"/users/{a['id']}", headers=ha).json()["following_count"] == 1
    assert client.get(f"/users/{r['id']}", headers=hr).json()["is_following"] is False

    assert [u["username"] for u in client.get(f"/users/{r['id']}/followers").json()] == ["ana"]
    assert [u["username"] for u in client.get(f"/users/{a['id']}/following").json()] == ["rui"]

    assert client.delete(f"/users/{r['id']}/follow", headers=ha).status_code == 204
    assert client.get(f"/users/{r['id']}").json()["followers_count"] == 0


def test_follow_rules(client, ana, rui):
    (a, ha), (r, _) = ana, rui
    assert client.post(f"/users/{a['id']}/follow", headers=ha).status_code == 400  # a si próprio
    assert client.post("/users/999/follow", headers=ha).status_code == 404
    assert client.post(f"/users/{r['id']}/follow").status_code == 401  # visitante
    assert client.post(f"/users/{r['id']}/follow", headers=ha).status_code == 204
    assert client.post(f"/users/{r['id']}/follow", headers=ha).status_code == 409  # duplicado
    assert client.delete(f"/users/{a['id']}/follow", headers=ha).status_code == 404  # não segue


def test_follow_succeeds_when_activity_service_is_down(client, ana, rui, monkeypatch):
    # Porta fechada: simula Activity Service indisponível.
    monkeypatch.setattr(settings, "activity_service_url", "http://127.0.0.1:9")
    monkeypatch.setattr(settings, "activity_timeout", 0.5)
    assert client.post(f"/users/{rui[0]['id']}/follow", headers=ana[1]).status_code == 204
    assert client.get(f"/users/{rui[0]['id']}").json()["followers_count"] == 1


def test_follow_emits_event(client, ana, rui, monkeypatch):
    sent = []
    monkeypatch.setattr("app.events.httpx.post", lambda url, **kw: sent.append((url, kw)))
    monkeypatch.setattr(settings, "activity_service_url", "http://activity")
    client.post(f"/users/{rui[0]['id']}/follow", headers=ana[1])
    assert len(sent) == 1
    url, kw = sent[0]
    assert url == "http://activity/internal/events"
    assert kw["json"]["event_type"] == "follow"
    assert kw["json"]["actor_id"] == ana[0]["id"]
    assert kw["json"]["recipe_owner_id"] == rui[0]["id"]
    assert kw["json"]["target_user_id"] == rui[0]["id"]
    assert kw["headers"]["X-Internal-Token"] == settings.internal_token
