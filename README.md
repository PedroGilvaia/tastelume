# Tastelume

Rede social de receitas culinárias — trabalho académico de desenvolvimento de aplicações móveis.
Flutter (MVVM + Provider) + 4 microserviços FastAPI, cada um com a sua base de dados PostgreSQL, orquestrados com Docker Compose.

## Estado atual (Fases 1–3 do backend concluídas; Activity Service e Flutter por fazer)

| Componente | Estado |
|---|---|
| **Users Service** (registo, login JWT, perfis, interesses, seguidores, endpoints internos) | ✅ Implementado, 23 testes automatizados a passar |
| **Recipe Service** (CRUD, categorias, pesquisa/ordenação/paginação, imagens, visualizações, personalização, endpoints internos) | ✅ Implementado, 30 testes automatizados a passar; validado com Users Service real via HTTP |
| **Interaction Service** (comentários, likes, avaliações, favoritos, partilhas, mensagens, contadores, limpeza) | ✅ Implementado, 27 testes automatizados a passar; validado com Users + Recipe reais via HTTP |
| Activity Service | ⏳ Esqueleto. Eventos, notificações, estatísticas: Fase 4 |
| Docker Compose (4 serviços + 4 BDs, volumes, health checks) | ✅ Escrito e YAML validado — **ainda não executado** (sem Docker no ambiente de desenvolvimento) |
| Aplicação Flutter (`mobile_app/`) | ❌ Por começar |
| Seed de dados, relatório, guião de demonstração | ❌ Fases 2–6 |

## Arrancar o backend

```bash
cp .env.example .env        # ajusta os segredos se quiseres
docker compose up --build
```

| Serviço | Porta | Swagger |
|---|---|---|
| Users | 8001 | http://localhost:8001/docs |
| Recipe | 8002 | http://localhost:8002/docs |
| Interaction | 8003 | http://localhost:8003/docs |
| Activity | 8004 | http://localhost:8004/docs |

O Users Service aplica as migrações (`alembic upgrade head`) ao arrancar.

## Testes

```bash
cd services/users_service        # ou recipe_service, interaction_service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
```

## Endereço do backend na app Flutter (quando existir)

- Emulador Android: `http://10.0.2.2:8001` (o `localhost` do emulador é o próprio emulador).
- Simulador iOS: `http://localhost:8001`.
- Telemóvel físico: IP do computador na rede local, p. ex. `http://192.168.1.20:8001`.

## Estrutura

```
tastelume/
├── mobile_app/                 # Flutter (por criar)
├── services/
│   ├── users_service/          # completo
│   ├── recipe_service/         # completo
│   ├── interaction_service/    # completo
│   └── activity_service/       # esqueleto
├── docs/architecture.md
├── docker-compose.yml
└── .env.example
```
