# Testes

## Backend (pytest, SQLite em memória) — 104 testes

```powershell
cd services\users_service        # idem recipe_service, interaction_service, activity_service
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -q
```

| Serviço | Testes |
|---|---|
| Users | 23 |
| Recipe | 30 |
| Interaction | 27 |
| Activity | 24 |

## Ponta-a-ponta sem Docker — 19 verificações

`scripts/e2e_local.py` arranca os 4 serviços reais (uvicorn + migrações Alembic em SQLite temporário), corre `scripts/seed.py` **duas vezes** (idempotência) e verifica:

- dados semeados (13 receitas com imagem, 5 utilizadores, sem duplicados) e contadores propagados entre serviços;
- notificações, contador de não lidas, marcar como lidas, estatísticas e top de receitas;
- feed personalizado;
- **degradação graciosa**, desligando serviços a meio: sem Activity Service (comentar e ver receitas continuam), sem Users Service (feed, detalhe e criar receita continuam; enviar mensagem devolve 503 e não grava nada) e sem Recipe Service (resumo de interações e gostos nunca devolvem 500).

```powershell
pip install -r services\users_service\requirements-dev.txt
pip install -r services\recipe_service\requirements.txt
python scripts\e2e_local.py
```

## Flutter

`mobile_app/test/` — formatação e datas (UTC), modelos JSON, `ApiClient` (token, 401, 422 traduzido, 503/rede) e `AuthViewModel` (sessão recuperada, offline, token expirado, login). Executar: `flutter test`.

## O que ainda tem de ser validado por ti (não foi possível no ambiente de desenvolvimento)

- `docker compose up --build` (Docker e PostgreSQL reais): as migrações foram validadas em SQLite.
- Compilação e execução da app Flutter num emulador/telemóvel (`flutter analyze`, `flutter run`), incluindo a câmara.
