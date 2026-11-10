def test_internal_requires_token(client, ana):
    uid = ana[0]["id"]
    assert client.get(f"/internal/users/{uid}").status_code == 401
    assert client.get(f"/internal/users/{uid}", headers={"X-Internal-Token": "errado"}).status_code == 403
    # Um JWT de utilizador não dá acesso a endpoints internos.
    assert client.get(f"/internal/users/{uid}", headers=ana[1]).status_code == 401


def test_internal_lookups(client, ana, rui, internal_headers):
    a, r = ana[0], rui[0]
    assert client.get(f"/internal/users/{a['id']}", headers=internal_headers).json()["username"] == "ana"
    assert client.get("/internal/users/by-username/RUI", headers=internal_headers).json()["id"] == r["id"]
    assert client.get("/internal/users/by-username/nao", headers=internal_headers).status_code == 404
    got = client.get("/internal/users", params={"ids": f"{a['id']},{r['id']},999"}, headers=internal_headers).json()
    assert sorted(u["username"] for u in got) == ["ana", "rui"]
    assert client.get("/internal/users", params={"ids": "x"}, headers=internal_headers).status_code == 400
    assert "email" not in got[0]


def test_internal_follower_ids(client, ana, rui, internal_headers):
    client.post(f"/users/{rui[0]['id']}/follow", headers=ana[1])
    r = client.get(f"/internal/users/{rui[0]['id']}/follower-ids", headers=internal_headers)
    assert r.json() == [ana[0]["id"]]
