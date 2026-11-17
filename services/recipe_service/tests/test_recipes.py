from conftest import PNG, auth, create, recipe_body


def test_categories_public_and_ordered(client):
    r = client.get("/categories")
    assert r.status_code == 200
    slugs = [c["slug"] for c in r.json()]
    assert slugs[0] == "entradas" and "sobremesas" in slugs and len(slugs) == 9


def test_create_requires_auth(client):
    assert client.post("/recipes", json=recipe_body()).status_code == 401
    assert client.post("/recipes", json=recipe_body(), headers={"Authorization": "Bearer x"}).status_code == 401


def test_create_and_read_detail_as_visitor(client):
    created = create(client)
    assert created["author_id"] == 1 and created["author_username"] == "ana"
    assert created["tags"] == ["chocolate", "forno"]
    assert [s["order"] for s in created["preparation_steps"]] == [1, 2, 3]
    assert created["rating_avg"] is None and created["rating_count"] == 0  # não classificada
    assert created["image_url"] is None

    r = client.get(f"/recipes/{created['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["ingredients"][0] == {"name": "Farinha", "quantity": 200.0, "unit": "g"}
    assert body["category"] == {"slug": "sobremesas", "name": "Sobremesas"}


def test_create_validation(client):
    bad = [
        recipe_body(title="ab"),
        recipe_body(category="inexistente"),
        recipe_body(ingredients=[]),
        recipe_body(ingredients=[{"name": "  "}]),
        recipe_body(preparation_steps=[]),
        recipe_body(preparation_steps=["  "]),
        recipe_body(difficulty="impossivel"),
        recipe_body(preparation_time=0),
        recipe_body(servings=0),
        recipe_body(tags=["x"] * 11),
    ]
    for body in bad:
        r = client.post("/recipes", json=body, headers=auth(1))
        assert r.status_code == 422, body


def test_read_404(client):
    assert client.get("/recipes/999").status_code == 404


def test_only_author_can_edit_and_delete(client):
    rid = create(client, 1)["id"]
    assert client.patch(f"/recipes/{rid}", json={"title": "Roubado"}, headers=auth(2)).status_code == 403
    assert client.delete(f"/recipes/{rid}", headers=auth(2)).status_code == 403
    assert client.patch(f"/recipes/{rid}", json={"title": "Roubado"}).status_code == 401
    assert client.get(f"/recipes/{rid}").json()["title"] == "Bolo de chocolate"

    r = client.patch(
        f"/recipes/{rid}",
        json={"title": "Bolo de laranja", "category": "pequenos-almocos",
              "ingredients": [{"name": "Laranja", "quantity": 2}]},
        headers=auth(1),
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Bolo de laranja"
    assert r.json()["category"]["slug"] == "pequenos-almocos"
    assert [i["name"] for i in r.json()["ingredients"]] == ["Laranja"]
    # a pesquisa por ingredientes acompanha a edição
    assert [x["id"] for x in client.get("/recipes", params={"ingredient": "laranja"}).json()] == [rid]
    assert client.get("/recipes", params={"ingredient": "farinha"}).json() == []

    assert client.patch(f"/recipes/{rid}", json={"title": None}, headers=auth(1)).status_code == 422
    assert client.patch(f"/recipes/{rid}", json={"category": "nao"}, headers=auth(1)).status_code == 422

    assert client.delete(f"/recipes/{rid}", headers=auth(1)).status_code == 204
    assert client.get(f"/recipes/{rid}").status_code == 404
    assert client.patch("/recipes/999", json={"title": "xxx"}, headers=auth(1)).status_code == 404


def test_search_filters_and_pagination(client):
    create(client, 1, title="Bolo de chocolate")
    create(client, 2, title="Sopa de legumes", category="sopas",
           ingredients=[{"name": "Cenoura"}, {"name": "Batata"}], description="Reconfortante")
    create(client, 2, title="Bife com ovo", category="carnes", ingredients=[{"name": "Bife"}, {"name": "Ovos"}])

    titles = lambda **p: sorted(x["title"] for x in client.get("/recipes", params=p).json())
    assert titles(q="CHOCOLATE") == ["Bolo de chocolate"]           # título (sem distinguir maiúsculas)
    assert titles(q="reconfortante") == ["Sopa de legumes"]         # descrição
    assert titles(q="cenoura") == ["Sopa de legumes"]               # ingrediente via q
    assert titles(ingredient="ovo") == ["Bife com ovo", "Bolo de chocolate"]
    assert titles(category="sopas") == ["Sopa de legumes"]
    assert titles(category="sopas", q="bolo") == []
    assert titles(author_id=2) == ["Bife com ovo", "Sopa de legumes"]
    assert titles(q="%") == []                                      # wildcard escapado
    assert titles(q="zzz") == []

    r = client.get("/recipes", params={"limit": 2, "offset": 0})
    assert len(r.json()) == 2 and r.headers["X-Total-Count"] == "3"
    assert len(client.get("/recipes", params={"limit": 2, "offset": 2}).json()) == 1
    assert client.get("/recipes", params={"limit": 0}).status_code == 422
    assert client.get("/recipes", params={"sort": "aleatorio"}).status_code == 422


def test_sorting(client, internal):
    a = create(client, 1, title="Receita A")["id"]
    b = create(client, 1, title="Receita B")["id"]
    c = create(client, 1, title="Receita C")["id"]
    put = lambda rid, body: client.put(f"/internal/recipes/{rid}/counters", json=body, headers=internal)
    assert put(a, {"rating_count": 2, "rating_avg": 4.0, "like_count": 0}).status_code == 204
    assert put(b, {"rating_count": 5, "rating_avg": 4.8, "like_count": 1}).status_code == 204
    # C não tem avaliações

    ids = lambda sort: [x["id"] for x in client.get("/recipes", params={"sort": sort}).json()]
    assert ids("recent") == [c, b, a]
    assert ids("rating") == [b, a, c]  # não classificadas no fim

    from app.database import SessionLocal
    from app.models import Recipe
    with SessionLocal() as db:
        db.get(Recipe, c).view_count = 100
        db.commit()
    assert ids("views")[0] == c
    # popularidade: C = 100; B = 0 + 3 + 0 + 2*5*4.8 = 51; A = 2*2*4 = 16
    assert ids("popular") == [c, b, a]
    assert ids("popular") == [x["id"] for x in client.get("/recipes").json()]  # omissão = popular


def test_user_recipes_public(client):
    create(client, 1, title="Bolo de chocolate")
    create(client, 2, title="Sopa de legumes", category="sopas")
    r = client.get("/users/2/recipes")
    assert [x["title"] for x in r.json()] == ["Sopa de legumes"]
    assert r.headers["X-Total-Count"] == "1"
    assert client.get("/users/99/recipes").json() == []


def test_related_same_category_excluding_self(client):
    a = create(client, 1, title="Bolo A")["id"]
    b = create(client, 1, title="Bolo B")["id"]
    create(client, 1, title="Sopa", category="sopas")
    assert [x["id"] for x in client.get(f"/recipes/{a}/related").json()] == [b]
    assert client.get("/recipes/999/related").status_code == 404


def test_personalization_prioritizes_interest_categories(client):
    create(client, 2, title="Sopa de legumes", category="sopas")
    create(client, 2, title="Bife", category="carnes")
    create(client, 2, title="Pudim", category="sobremesas")  # interesse da ana ("Sobremesas")
    # sem personalização: apenas a ordenação pedida (mais recentes primeiro)
    assert [x["title"] for x in client.get("/recipes", params={"sort": "recent"}).json()] == ["Pudim", "Bife", "Sopa de legumes"]

    # 'Salada' é a mais recente; só a personalização pode pôr 'Pudim' (interesse da ana) à frente
    create(client, 2, title="Salada", category="vegetarianas")
    r = client.get("/recipes", params={"sort": "recent", "personalized": True}, headers=auth(1))
    assert r.json()[0]["title"] == "Pudim"
    # visitante com personalized=true: ignora silenciosamente
    r = client.get("/recipes", params={"sort": "recent", "personalized": True})
    assert r.json()[0]["title"] == "Salada"


def test_works_when_users_service_is_down(client, monkeypatch):
    import httpx
    from app.clients import users_client

    def boom(ids):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(users_client, "_fetch", boom)
    users_client.reset()
    create(client, 1)
    r = client.get("/recipes")
    assert r.status_code == 200 and r.json()[0]["author_username"] is None
    assert client.get("/recipes/1").status_code == 200
    # com personalização também não falha
    assert client.get("/recipes", params={"personalized": True}, headers=auth(1)).status_code == 200
