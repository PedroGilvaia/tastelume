from conftest import auth, backdate


def _populate(send):
    send("recipe_created", 1, 10, 1)
    send("recipe_created", 1, 11, 1)
    for viewer in (None, None, 2, 3):
        send("view", viewer, 10, 1)
    send("view", None, 11, 1)
    send("view", 1, 10, 1)            # o autor a ver a própria receita (não conta)
    send("like", 2, 10, 1, 1)
    send("like", 1, 10, 1, 1)         # auto-gosto (não conta)
    send("comment", 3, 11, 1, 1)
    send("rating", 2, 10, 1, 1)
    send("share", 2, 10, 1, 3)
    send("follow", 2, None, 1, 1)
    send("view", None, 12, 2)         # receita de outra pessoa


def test_stats_require_auth(client):
    for path in ("/stats/me", "/stats/me/timeline", "/stats/me/top-recipes"):
        assert client.get(path).status_code == 401, path


def test_totals_only_count_other_peoples_activity_on_my_recipes(send, client):
    _populate(send)
    body = client.get("/stats/me", headers=auth(1)).json()
    assert body["period_days"] == 30
    assert body["totals"] == {"views": 5, "likes": 1, "comments": 1, "ratings": 1, "shares": 1,
                              "new_followers": 1, "recipes_published": 2}
    other = client.get("/stats/me", headers=auth(2)).json()["totals"]
    assert other["views"] == 1 and other["likes"] == 0 and other["recipes_published"] == 0


def test_period_filter(send, client):
    _populate(send)
    backdate(10)
    assert client.get("/stats/me", params={"days": 7}, headers=auth(1)).json()["totals"]["views"] == 0
    assert client.get("/stats/me", params={"days": 30}, headers=auth(1)).json()["totals"]["views"] == 5
    for bad in (0, 366):
        assert client.get("/stats/me", params={"days": bad}, headers=auth(1)).status_code == 422


def test_timeline_fills_empty_days(send, client):
    send("view", None, 10, 1)
    send("like", 2, 10, 1, 1)
    send("view", None, 10, 1)
    backdate(2, "view")  # as duas visualizações passam a há 2 dias
    pts = client.get("/stats/me/timeline", params={"days": 4}, headers=auth(1)).json()
    assert len(pts) == 4
    assert [p["date"] for p in pts] == sorted(p["date"] for p in pts)
    assert [(p["views"], p["likes"]) for p in pts] == [(0, 0), (2, 0), (0, 0), (0, 1)]
    assert client.get("/stats/me/timeline", headers=auth(1)).json().__len__() == 7
    assert client.get("/stats/me/timeline", params={"days": 91}, headers=auth(1)).status_code == 422


def test_top_recipes_sorting_and_titles(send, client):
    _populate(send)
    top = client.get("/stats/me/top-recipes", headers=auth(1)).json()
    assert [(t["recipe_id"], t["title"], t["views"]) for t in top] == [
        (10, "Bolo de chocolate", 4), (11, "Sopa de legumes", 1)]
    assert top[0]["likes"] == 1 and top[0]["shares"] == 1 and top[1]["comments"] == 1

    by_comments = client.get("/stats/me/top-recipes", params={"sort": "comments"}, headers=auth(1)).json()
    assert by_comments[0]["recipe_id"] == 11
    assert len(client.get("/stats/me/top-recipes", params={"limit": 1}, headers=auth(1)).json()) == 1
    assert client.get("/stats/me/top-recipes", params={"sort": "x"}, headers=auth(1)).status_code == 422
    assert client.get("/stats/me/top-recipes", headers=auth(3)).json() == []


def test_top_recipes_without_recipe_service(send, client, world):
    _populate(send)
    world.down.add("recipes")
    top = client.get("/stats/me/top-recipes", headers=auth(1))
    assert top.status_code == 200
    assert [(t["recipe_id"], t["title"]) for t in top.json()] == [(10, None), (11, None)]
