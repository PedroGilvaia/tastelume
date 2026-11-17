#!/usr/bin/env python3
"""Dados de demonstração para o Tastelume.

Só usa a biblioteca padrão do Python e fala com os serviços pela API pública (como a app).
É idempotente: pode ser executado várias vezes sem duplicar utilizadores, receitas ou comentários.

Uso (com o backend a correr):
    python scripts/seed.py
    python scripts/seed.py --host 192.168.1.20      # outro endereço
Todas as contas de demonstração usam a password:  Tastelume123
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import urllib.error
import urllib.request
import uuid
import zlib

PASSWORD = "Tastelume123"

USERS = [
    ("ana_cozinha", "Cozinha tradicional portuguesa, sem pressas.", ["Sopas", "Carnes", "Sobremesas"]),
    ("rui_chef", "Chef amador. Peixe fresco e muito alho.", ["Peixes", "Entradas"]),
    ("marta_veg", "Vegetariana desde 2015. Receitas simples e coloridas.", ["Vegetarianas", "Sopas"]),
    ("joao_doces", "Pastelaria caseira ao fim de semana.", ["Sobremesas", "Pequenos-almoços"]),
    ("sofia_mar", "Do Algarve para a tua mesa.", ["Peixes", "Massas e arroz"]),
]

# autor, título, categoria, descrição, ingredientes [(nome, qtd, unidade)], passos, minutos, doses, dificuldade, etiquetas
RECIPES = [
    ("ana_cozinha", "Caldo verde", "sopas", "A sopa mais portuguesa de todas.",
     [("batata", 500, "g"), ("couve galega", 200, "g"), ("cebola", 1, None), ("chouriço", 100, "g"), ("azeite", 4, "colheres de sopa")],
     ["Coze a batata com a cebola em água e sal.", "Tritura tudo e volta a levar ao lume.",
      "Corta a couve em tiras muito finas e junta à sopa durante 5 minutos.", "Serve com rodelas de chouriço e um fio de azeite."],
     40, 4, "facil", ["tradicional", "inverno"]),
    ("ana_cozinha", "Bacalhau à Brás", "peixes", "Clássico de lojas de petiscos e almoços de domingo.",
     [("bacalhau desfiado", 400, "g"), ("batata palha", 200, "g"), ("ovos", 6, None), ("cebola", 2, None), ("alho", 2, "dentes")],
     ["Refoga a cebola e o alho em azeite.", "Junta o bacalhau e mexe 5 minutos.", "Adiciona os ovos batidos e a batata palha, mexendo até ficar cremoso.", "Serve com salsa e azeitonas."],
     35, 4, "media", ["bacalhau", "clássico"]),
    ("ana_cozinha", "Arroz doce", "sobremesas", "Cremoso, com casca de limão e canela.",
     [("arroz", 200, "g"), ("leite", 1, "l"), ("açúcar", 150, "g"), ("gemas", 4, None), ("casca de limão", 1, None), ("canela", 1, "colher de chá")],
     ["Coze o arroz em água com a casca de limão.", "Junta o leite quente e o açúcar aos poucos.", "Retira do lume e envolve as gemas.", "Serve frio, decorado com canela."],
     60, 6, "media", ["doce", "tradicional"]),
    ("rui_chef", "Sardinhas assadas com salada de pimentos", "peixes", "O verão num prato.",
     [("sardinhas", 12, None), ("sal grosso", 2, "colheres de sopa"), ("pimentos", 3, None), ("azeite", 3, "colheres de sopa"), ("vinagre", 1, "colher de sopa")],
     ["Tempera as sardinhas com sal grosso e deixa repousar.", "Assa os pimentos, descasca e corta em tiras.", "Grelha as sardinhas 3 a 4 minutos de cada lado.", "Serve com a salada temperada com azeite e vinagre."],
     30, 4, "facil", ["verão", "grelhados"]),
    ("rui_chef", "Pastéis de bacalhau", "entradas", "Crocantes por fora, macios por dentro.",
     [("bacalhau cozido", 300, "g"), ("batata", 300, "g"), ("ovos", 2, None), ("salsa", 1, "molho"), ("cebola", 1, None)],
     ["Esmaga a batata e mistura com o bacalhau desfiado.", "Junta a cebola picada, a salsa e os ovos.", "Molda com duas colheres de sopa.", "Frita em óleo quente até dourar."],
     45, 6, "media", ["petisco", "frito"]),
    ("marta_veg", "Sopa de grão com espinafres", "sopas", "Reconfortante e cheia de proteína vegetal.",
     [("grão cozido", 400, "g"), ("espinafres", 200, "g"), ("cebola", 1, None), ("alho", 2, "dentes"), ("cominhos", 1, "colher de chá")],
     ["Refoga a cebola e o alho.", "Junta o grão, os cominhos e água a cobrir.", "Deixa cozer 20 minutos e adiciona os espinafres.", "Tritura parcialmente e serve quente."],
     35, 4, "facil", ["vegan", "proteína"]),
    ("marta_veg", "Salada de quinoa com legumes assados", "vegetarianas", "Colorida e pronta em meia hora.",
     [("quinoa", 200, "g"), ("curgete", 1, None), ("pimento vermelho", 1, None), ("tomate cherry", 150, "g"), ("limão", 1, None)],
     ["Coze a quinoa e deixa arrefecer.", "Assa os legumes a 200 °C durante 20 minutos.", "Mistura tudo e tempera com sumo de limão e azeite."],
     30, 2, "facil", ["vegan", "salada"]),
    ("marta_veg", "Lasanha de legumes", "vegetarianas", "Camadas de curgete, cogumelos e molho de tomate.",
     [("massa de lasanha", 250, "g"), ("curgete", 2, None), ("cogumelos", 250, "g"), ("molho de tomate", 500, "ml"), ("queijo", 150, "g")],
     ["Salteia os legumes.", "Alterna camadas de massa, legumes, molho e queijo.", "Leva ao forno a 180 °C durante 35 minutos."],
     75, 6, "media", ["forno", "vegetariano"]),
    ("joao_doces", "Pão de ló de Ovar", "sobremesas", "Húmido no centro, como manda a tradição.",
     [("ovos", 8, None), ("açúcar", 250, "g"), ("farinha", 120, "g")],
     ["Bate os ovos com o açúcar até triplicar de volume.", "Envolve a farinha peneirada com cuidado.", "Coze a 180 °C durante 20 minutos: o centro deve ficar húmido."],
     40, 8, "dificil", ["bolo", "tradicional"]),
    ("joao_doces", "Panquecas de aveia e banana", "pequenos-almocos", "Sem açúcar adicionado.",
     [("aveia", 100, "g"), ("banana madura", 2, None), ("ovos", 2, None), ("leite", 100, "ml")],
     ["Tritura todos os ingredientes.", "Deixa a massa repousar 5 minutos.", "Coze em frigideira antiaderente, dos dois lados."],
     15, 2, "facil", ["rápido", "saudável"]),
    ("sofia_mar", "Arroz de tamboril", "massas-arroz", "Malandrinho, com coentros frescos.",
     [("arroz carolino", 300, "g"), ("tamboril", 600, "g"), ("tomate", 3, None), ("coentros", 1, "molho"), ("camarão", 200, "g")],
     ["Faz um refogado de cebola, alho e tomate.", "Junta o tamboril e o camarão.", "Adiciona o arroz e água quente (2 partes por 1 de arroz).", "Cozinha 12 minutos e finaliza com coentros."],
     50, 4, "media", ["marisco", "algarve"]),
    ("sofia_mar", "Cataplana de amêijoas", "peixes", "Receita algarvia para partilhar.",
     [("amêijoas", 800, "g"), ("chouriço", 100, "g"), ("pimento", 1, None), ("tomate", 2, None), ("vinho branco", 1, "copo")],
     ["Coloca todos os ingredientes na cataplana.", "Fecha e leva ao lume vivo 10 minutos.", "Serve com pão alentejano."],
     25, 3, "facil", ["algarve", "marisco"]),
    ("sofia_mar", "Sumo de laranja e gengibre", "bebidas", "Um estalo de vitamina C.",
     [("laranjas", 4, None), ("gengibre", 1, "colher de chá"), ("hortelã", 4, "folhas")],
     ["Espreme as laranjas.", "Junta o gengibre ralado e a hortelã.", "Serve com gelo."],
     5, 2, "facil", ["rápido", "bebida"]),
]

COMMENTS = [
    "Fiz hoje e ficou delicioso!", "Obrigado pela receita, a família adorou.",
    "Acrescentei um pouco de piripiri e ficou ainda melhor.", "Quanto tempo posso guardar no frigorífico?",
    "Simples e rápida, vou repetir.", "Fiquei com água na boca só de ler.",
]


class Api:
    def __init__(self, host: str, ports: tuple[int, int, int, int], scheme: str = "http"):
        self.users, self.recipes, self.inter, self.activity = (f"{scheme}://{host}:{p}" for p in ports)

    @staticmethod
    def call(method, url, body=None, token=None, headers=None, raw=None, ok=(200, 201, 204)):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        hdr = {"Accept": "application/json"}
        if body is not None:
            hdr["Content-Type"] = "application/json"
        if token:
            hdr["Authorization"] = f"Bearer {token}"
        hdr.update(headers or {})
        req = urllib.request.Request(url, data=data, method=method, headers=hdr)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                payload = r.read()
                return r.status, (json.loads(payload) if payload else None)
        except urllib.error.HTTPError as e:
            payload = e.read()
            try:
                return e.code, json.loads(payload) if payload else None
            except ValueError:
                return e.code, payload.decode(errors="replace")


def make_png(seed: int, size: int = 480) -> bytes:
    """PNG sem dependências: degradé suave com cores derivadas do `seed`."""
    def channel(k: int) -> int:
        return 90 + (seed * (37 + 23 * k) + 61 * k) % 140

    r0, g0, b0 = channel(0), channel(1), channel(2)
    rows = bytearray()
    for y in range(size):
        rows.append(0)  # filtro "None"
        t = y / (size - 1)
        for x in range(size):
            s = (x / (size - 1) + t) / 2
            rows += bytes((int(r0 + (255 - r0) * s * 0.5), int(g0 + (255 - g0) * s * 0.5), int(b0 + (255 - b0) * s * 0.5)))

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows), 6)) + chunk(b"IEND", b""))


def multipart_png(png: bytes) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"foto.png\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + png + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def ensure_user(api: Api, username: str, description: str, interests: list[str]) -> tuple[int, str]:
    email = f"{username}@tastelume.demo"
    status, tok = api.call("POST", f"{api.users}/auth/login", {"identifier": username, "password": PASSWORD})
    if status == 401:
        status, _ = api.call("POST", f"{api.users}/auth/register", {"username": username, "email": email, "password": PASSWORD})
        if status != 201:
            sys.exit(f"Falha ao registar {username}: {status}")
        status, tok = api.call("POST", f"{api.users}/auth/login", {"identifier": username, "password": PASSWORD})
    if status != 200:
        sys.exit(f"Falha no login de {username}: {status} {tok}")
    token = tok["access_token"]
    status, me = api.call("PATCH", f"{api.users}/users/me", {"description": description, "interests": interests}, token)
    if status != 200:
        sys.exit(f"Falha ao atualizar o perfil de {username}: {status} {me}")
    return me["id"], token


def seed(api: Api) -> None:
    ids: dict[str, int] = {}
    tokens: dict[str, str] = {}
    for username, desc, interests in USERS:
        ids[username], tokens[username] = ensure_user(api, username, desc, interests)
    print(f"Utilizadores: {', '.join(ids)}")

    recipe_ids: list[int] = []
    created = 0
    for n, (author, title, cat, desc, ingredients, steps, minutes, servings, difficulty, tags) in enumerate(RECIPES):
        _, mine = api.call("GET", f"{api.recipes}/users/{ids[author]}/recipes?limit=50")
        existing = next((r for r in (mine or []) if r["title"] == title), None)
        if existing:
            recipe_ids.append(existing["id"])
            continue
        body = {
            "title": title, "description": desc, "category": cat,
            "ingredients": [{"name": i[0], "quantity": i[1], "unit": i[2]} for i in ingredients],
            "preparation_steps": steps, "preparation_time": minutes, "servings": servings,
            "difficulty": difficulty, "tags": tags,
        }
        status, rec = api.call("POST", f"{api.recipes}/recipes", body, tokens[author])
        if status != 201:
            sys.exit(f"Falha ao criar «{title}»: {status} {rec}")
        png, ctype = multipart_png(make_png(n + 1))
        st, _ = api.call("POST", f"{api.recipes}/recipes/{rec['id']}/image", token=tokens[author], raw=png, headers={"Content-Type": ctype})
        if st != 200:
            print(f"  (aviso) imagem de «{title}» não carregada: {st}")
        recipe_ids.append(rec["id"])
        created += 1
    print(f"Receitas: {len(recipe_ids)} ({created} novas)")

    names = list(ids)
    # seguidores (409 = já existe)
    for i, a in enumerate(names):
        for b in (names[(i + 1) % len(names)], names[(i + 2) % len(names)]):
            api.call("POST", f"{api.users}/users/{ids[b]}/follow", token=tokens[a])
    # gostos e avaliações determinísticos
    for n, rid in enumerate(recipe_ids):
        for k, user in enumerate(names):
            if (n + k) % 3 != 0:
                api.call("POST", f"{api.inter}/recipes/{rid}/like", token=tokens[user])  # 409 = já gostou
            if (n * 2 + k) % 4 != 0:
                api.call("POST", f"{api.inter}/recipes/{rid}/ratings", {"score": 3 + (n + k) % 3}, tokens[user])
        _, comments = api.call("GET", f"{api.inter}/recipes/{rid}/comments?limit=1")
        if not comments:
            for k in range(2):
                user = names[(n + k + 1) % len(names)]
                api.call("POST", f"{api.inter}/recipes/{rid}/comments", {"text": COMMENTS[(n + k) % len(COMMENTS)]}, tokens[user])
        for v in range(2 + (n * 3) % 7):  # visitantes anónimos distintos
            api.call("POST", f"{api.recipes}/recipes/{rid}/view", headers={"X-Client-Id": f"seed-{rid}-{v}"})
    print("Seguidores, gostos, avaliações, comentários e visualizações criados.")

    # favoritos, partilhas e mensagens (só se ainda não existirem)
    _, cols = api.call("GET", f"{api.inter}/favorite-collections", token=tokens["marta_veg"])
    if not cols:
        _, col = api.call("POST", f"{api.inter}/favorite-collections", {"name": "Para fazer no fim de semana"}, tokens["marta_veg"])
        for rid in recipe_ids[:3]:
            api.call("POST", f"{api.inter}/favorite-collections/{col['id']}/recipes/{rid}", token=tokens["marta_veg"])
    _, shares = api.call("GET", f"{api.inter}/shares/received", token=tokens["rui_chef"])
    if not shares:
        api.call("POST", f"{api.inter}/recipes/{recipe_ids[0]}/share", {"recipient_username": "rui_chef"}, tokens["ana_cozinha"])
    _, convs = api.call("GET", f"{api.inter}/messages/conversations", token=tokens["ana_cozinha"])
    if not convs:
        api.call("POST", f"{api.inter}/messages/{ids['rui_chef']}", {"text": "Viste a minha receita de caldo verde?"}, tokens["ana_cozinha"])
        api.call("POST", f"{api.inter}/messages/{ids['ana_cozinha']}", {"text": "Vi! Vou experimentar no domingo."}, tokens["rui_chef"])
    print("Favoritos, partilha e mensagens de exemplo criados.")
    print(f"\nPronto. Entra na app com qualquer utilizador, p. ex. «ana_cozinha» / «{PASSWORD}».")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", default="localhost")
    p.add_argument("--ports", default="8001,8002,8003,8004", help="users,recipe,interaction,activity")
    args = p.parse_args()
    ports = tuple(int(x) for x in args.ports.split(","))
    seed(Api(args.host, ports))  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
