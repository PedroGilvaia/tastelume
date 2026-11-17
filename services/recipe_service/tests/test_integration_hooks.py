from app.config import settings
from conftest import auth, create


def test_filter_by_ids(client):
    a, b, c = (create(client, 1, title=f"Receita {n}")["id"] for n in "ABC")
    got = client.get("/recipes", params={"ids": f"{a},{c},999"}).json()
    assert sorted(x["id"] for x in got) == sorted([a, c])
    assert client.get("/recipes", params={"ids": "x"}).status_code == 400
    assert client.get("/recipes", params={"ids": ""}).status_code == 400
    assert client.get("/recipes", params={"ids": ",".join(map(str, range(51)))}).status_code == 400


def test_delete_notifies_interaction_service(client, monkeypatch):
    sent = []
    monkeypatch.setattr("app.clients.httpx.delete", lambda url, **kw: sent.append((url, kw["headers"])))
    monkeypatch.setattr(settings, "interaction_service_url", "http://interaction.test")
    rid = create(client, 1)["id"]
    assert client.delete(f"/recipes/{rid}", headers=auth(1)).status_code == 204
    assert sent == [(f"http://interaction.test/internal/recipes/{rid}/data",
                     {"X-Internal-Token": settings.internal_token})]


def test_delete_succeeds_when_interaction_service_is_down(client, monkeypatch):
    monkeypatch.setattr(settings, "interaction_service_url", "http://127.0.0.1:9")
    monkeypatch.setattr(settings, "http_timeout", 0.5)
    rid = create(client, 1)["id"]
    assert client.delete(f"/recipes/{rid}", headers=auth(1)).status_code == 204
    assert client.get(f"/recipes/{rid}").status_code == 404
