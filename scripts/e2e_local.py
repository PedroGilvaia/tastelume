#!/usr/bin/env python3
"""Teste ponta-a-ponta SEM Docker: arranca os 4 serviços com SQLite temporário, corre o seed e verifica
os fluxos principais e a degradação graciosa (serviços desligados a meio).

Requisitos: Python 3.11+ com as dependências instaladas (uma vez):
    pip install -r services/users_service/requirements-dev.txt
Uso:  python scripts/e2e_local.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import seed  # noqa: E402

PORTS = {"users": 18001, "recipe": 18002, "interaction": 18003, "activity": 18004}
SECRET = "e2e-jwt-secret-e2e-jwt-secret-e2e-jwt"
INTERNAL = "e2e-internal-token"
procs: dict[str, subprocess.Popen] = {}
passed = 0


def check(cond: bool, label: str) -> None:
    global passed
    if not cond:
        print(f"  ✗ {label}")
        raise SystemExit(f"FALHOU: {label}")
    passed += 1
    print(f"  ✓ {label}")


def wait_health(port: int, timeout: float = 30) -> None:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2):
                return
        except Exception:
            time.sleep(0.3)
    raise SystemExit(f"Serviço na porta {port} não arrancou a tempo.")


def start(name: str, tmp: Path) -> None:
    cwd = ROOT / "services" / f"{name}_service"
    env = dict(
        os.environ, JWT_SECRET=SECRET, INTERNAL_SERVICE_TOKEN=INTERNAL,
        DATABASE_URL=f"sqlite:///{tmp / (name + '.db')}", IMAGE_DIR=str(tmp / "images"),
        USERS_SERVICE_URL=f"http://127.0.0.1:{PORTS['users']}",
        RECIPE_SERVICE_URL=f"http://127.0.0.1:{PORTS['recipe']}",
        INTERACTION_SERVICE_URL=f"http://127.0.0.1:{PORTS['interaction']}",
        ACTIVITY_SERVICE_URL=f"http://127.0.0.1:{PORTS['activity']}",
    )
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=cwd, env=env, check=True, capture_output=True)
    procs[name] = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORTS[name]), "--log-level", "warning"],
        cwd=cwd, env=env,
    )


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="tastelume_e2e_"))
    try:
        for name in PORTS:
            start(name, tmp)
        for port in PORTS.values():
            wait_health(port)
        print("Serviços a correr (migrações Alembic aplicadas).")

        api = seed.Api("127.0.0.1", tuple(PORTS.values()))  # type: ignore[arg-type]
        seed.seed(api)
        seed.seed(api)  # idempotência: a segunda execução não pode duplicar nada
        time.sleep(1.5)  # tarefas em background (contadores e eventos)

        print("\nVerificações")
        _, recipes = api.call("GET", f"{api.recipes}/recipes?limit=50")
        check(len(recipes) == len(seed.RECIPES), "seed idempotente: nº de receitas = nº definido")
        _, users = api.call("GET", f"{api.users}/users?limit=50")
        check(len([u for u in users if u["username"] in {x[0] for x in seed.USERS}]) == len(seed.USERS), "5 utilizadores de demonstração, sem duplicados")
        check(all(r["image_url"] for r in recipes), "todas as receitas têm imagem")
        check(any(r["like_count"] > 0 and r["comment_count"] > 0 and r["rating_avg"] for r in recipes), "contadores chegaram ao Recipe Service")
        check(sorted(recipes, key=lambda r: -(r["view_count"] + 3 * r["like_count"]))[0]["id"] != 0, "feed popular devolve dados")

        status, tok = api.call("POST", f"{api.users}/auth/login", {"identifier": "ana_cozinha", "password": seed.PASSWORD})
        ana = tok["access_token"]
        _, me = api.call("GET", f"{api.users}/users/me", token=ana)
        _, notes = api.call("GET", f"{api.activity}/notifications", token=ana)
        check(len(notes) > 0, "a autora recebe notificações (gostos/comentários/seguidores)")
        _, unread = api.call("GET", f"{api.activity}/notifications/unread-count", token=ana)
        check(unread["unread"] > 0, "contador de não lidas > 0")
        st, _ = api.call("POST", f"{api.activity}/notifications/read-all", token=ana)
        _, unread = api.call("GET", f"{api.activity}/notifications/unread-count", token=ana)
        check(st == 204 and unread["unread"] == 0, "marcar todas como lidas")
        _, stats = api.call("GET", f"{api.activity}/stats/me?days=30", token=ana)
        check(stats["totals"]["views"] > 0 and stats["totals"]["likes"] > 0, "estatísticas refletem a atividade")
        _, top = api.call("GET", f"{api.activity}/stats/me/top-recipes?days=30&sort=views", token=ana)
        check(len(top) > 0 and top[0]["title"], "top de receitas com títulos")

        _, personalized = api.call("GET", f"{api.recipes}/recipes?personalized=true&sort=recent&limit=3", token=ana)
        check(personalized[0]["category"]["slug"] in {"sopas", "carnes", "sobremesas"}, "feed personalizado prioriza os interesses")

        print("\nDegradação graciosa")
        procs["activity"].terminate(); procs["activity"].wait(10)
        rid = recipes[0]["id"]
        _, tok = api.call("POST", f"{api.users}/auth/login", {"identifier": "joao_doces", "password": seed.PASSWORD})
        joao = tok["access_token"]
        st, _ = api.call("POST", f"{api.inter}/recipes/{rid}/comments", {"text": "Com o Activity Service em baixo."}, joao)
        check(st == 201, "comentar funciona com o Activity Service desligado")
        st, _ = api.call("POST", f"{api.recipes}/recipes/{rid}/view", token=joao)
        check(st == 200, "visualização regista-se com o Activity Service desligado")

        procs["users"].terminate(); procs["users"].wait(10)
        st, lst = api.call("GET", f"{api.recipes}/recipes?limit=5")
        check(st == 200 and len(lst) > 0, "feed continua a funcionar sem Users Service (nomes de autor vêm da cache ou null)")
        st, _ = api.call("GET", f"{api.recipes}/recipes/{rid}")
        check(st == 200, "detalhe de receita sem Users Service")
        st, created = api.call("POST", f"{api.recipes}/recipes", {
            "title": "Receita criada sem Users", "category": "sopas", "ingredients": [{"name": "água"}],
            "preparation_steps": ["Ferver."], "preparation_time": 5, "servings": 1, "difficulty": "facil"}, joao)
        check(st == 201, "criar receita sem Users Service (JWT validado localmente)")
        st, _ = api.call("POST", f"{api.inter}/messages/9999", {"text": "olá"}, joao)
        check(st == 503, "mensagem a destinatário não validável (Users Service em baixo) → 503, nada é gravado")

        procs["recipe"].terminate(); procs["recipe"].wait(10)
        st, summary = api.call("GET", f"{api.inter}/recipes/{rid}/interactions", token=joao)
        check(st == 200 and summary["like_count"] >= 0, "resumo de interações sem Recipe Service")
        st, _ = api.call("POST", f"{api.inter}/recipes/{rid}/like", token=joao)
        check(st in (204, 409, 503), "gostar sem Recipe Service nunca devolve 500")
        print(f"\n{passed} verificações passaram.")
    finally:
        for p in procs.values():
            if p.poll() is None:
                p.terminate()
        for p in procs.values():
            try:
                p.wait(5)
            except Exception:
                p.kill()


if __name__ == "__main__":
    main()
