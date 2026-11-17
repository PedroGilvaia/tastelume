# Tastelume

Rede social de receitas culinárias — trabalho académico de desenvolvimento de aplicações móveis.
Flutter (MVVM + Provider) + 4 microserviços FastAPI, cada um com a sua base de dados PostgreSQL, orquestrados com Docker Compose.

## Estado

| Componente | Estado |
|---|---|
| **Users Service** (registo, login JWT, perfis, interesses, seguidores) | ✅ 23 testes |
| **Recipe Service** (CRUD, categorias, pesquisa, imagens, visualizações, personalização) | ✅ 30 testes |
| **Interaction Service** (comentários, gostos, avaliações, favoritos, partilhas, mensagens) | ✅ 27 testes |
| **Activity Service** (eventos, notificações, estatísticas) | ✅ 24 testes |
| **App Flutter** (`mobile_app/`) | ✅ Escrita; testes unitários incluídos — compilar e executar com `flutter analyze` / `flutter run` |
| **Seed de dados** (`scripts/seed.py`) | ✅ Idempotente, só biblioteca padrão do Python |
| **Teste ponta-a-ponta** (`scripts/e2e_local.py`) | ✅ 19 verificações, incluindo desligar serviços |
| **Docker Compose** | ⚠️ Escrito e validado em YAML; **ainda por executar** com Docker/PostgreSQL reais |
| Relatório e guião do vídeo | 📝 Rascunhos em `docs/` |

## Arrancar tudo (Windows PowerShell)

```powershell
# 1) Backend
copy .env.example .env
docker compose up --build

# 2) Dados de demonstração (noutro terminal, na raiz do projeto)
python scripts\seed.py            # contas: ana_cozinha, rui_chef, ... / password Tastelume123

# 3) App
cd mobile_app
.\setup_platforms.ps1             # só da primeira vez
flutter run
```

| Serviço | Porta | Swagger |
|---|---|---|
| Users | 8001 | http://localhost:8001/docs |
| Recipe | 8002 | http://localhost:8002/docs |
| Interaction | 8003 | http://localhost:8003/docs |
| Activity | 8004 | http://localhost:8004/docs |

Cada serviço aplica as suas migrações (`alembic upgrade head`) ao arrancar.

## Testes

Ver [docs/testes.md](docs/testes.md). Resumo: `python -m pytest -q` em cada pasta de `services/`; `python scripts\e2e_local.py` (sem Docker); `flutter test` em `mobile_app/`.

## Endereço do backend na app

Emulador Android `10.0.2.2` · Simulador iOS `localhost` · Telemóvel físico: IP do PC na rede local. Configurável na app (ícone de servidor no login) ou com `--dart-define=API_HOST=...`.

## Estrutura

```
tastelume/
├── mobile_app/                 # Flutter (MVVM + Provider)
├── services/
│   ├── users_service/
│   ├── recipe_service/
│   ├── interaction_service/
│   └── activity_service/
├── scripts/
│   ├── seed.py                 # dados de demonstração
│   └── e2e_local.py            # teste ponta-a-ponta sem Docker
├── docs/
│   ├── architecture.md
│   ├── testes.md
│   ├── guiao-demo.md
│   └── relatorio.md
├── tastelume_diagramas.zip
├── docker-compose.yml
└── .env.example
```
