from conftest import make_user


def test_update_me_description_and_interests(client, ana):
    r = client.patch(
        "/users/me",
        headers=ana[1],
        json={"description": "  Adoro cozinhar  ", "interests": ["Sobremesas", "sobremesas", "Sopas"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["description"] == "Adoro cozinhar"
    assert body["interests"] == ["Sobremesas", "Sopas"]
    assert client.get("/users/me", headers=ana[1]).json()["interests"] == ["Sobremesas", "Sopas"]


def test_update_me_validation_and_auth(client, ana):
    assert client.patch("/users/me", json={"description": "x"}).status_code == 401
    assert client.patch("/users/me", headers=ana[1], json={"description": "x" * 501}).status_code == 422
    assert client.patch("/users/me", headers=ana[1], json={"interests": [""]}).status_code == 422
    assert client.patch("/users/me", headers=ana[1], json={"interests": ["a"] * 21}).status_code == 422


def test_visitor_can_read_public_profile_without_email(client, ana):
    r = client.get(f"/users/{ana[0]['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "ana" and "email" not in body
    assert body["is_following"] is None
    assert body["followers_count"] == 0 and body["following_count"] == 0


def test_profile_404(client):
    assert client.get("/users/12345").status_code == 404


def test_search_users_public(client):
    for name in ("ana", "anabela", "rui"):
        make_user(client, name)
    names = [u["username"] for u in client.get("/users", params={"q": "ANA"}).json()]
    assert names == ["ana", "anabela"]
    assert len(client.get("/users").json()) == 3
    assert client.get("/users", params={"q": "%"}).json() == []  # wildcard escapado
    assert client.get("/users", params={"limit": 0}).status_code == 422
