# Guião do vídeo de demonstração (≈ 6 min)

Preparação: `docker compose up --build`, `python scripts/seed.py`, emulador a correr, app aberta no ecrã de entrada. Conta: `ana_cozinha` / `Tastelume123`.

| Min | O quê | Mostrar |
|---|---|---|
| 0:00 | Introdução | Problema, arquitetura (diagrama dos 4 microserviços), stack |
| 0:45 | Registo e login | Criar conta nova; erro com password errada; sessão guardada (fechar e reabrir a app) |
| 1:30 | Feed | Ordenação, categorias, «Para ti», scroll infinito, pull-to-refresh |
| 2:15 | Detalhe | Gostar, avaliar, comentar/editar/apagar, guardar em favoritos, partilhar com `rui_chef` |
| 3:00 | **Criar receita com a câmara** | Fotografar, preencher, publicar; aparece no feed e no perfil |
| 3:45 | Social | Perfil de `marta_veg`, seguir, mensagem; abrir com `rui_chef` as notificações e mensagens |
| 4:30 | Estatísticas | Totais, gráfico diário, top de receitas; alterar o período |
| 5:00 | **Resiliência** | `docker compose stop interaction_service`: a receita abre com aviso; `stop users_service`: o feed continua; `stop activity_service`: nada quebra. Voltar a ligar e «Tentar novamente» |
| 5:45 | Conclusão | Testes (104 + e2e + Flutter), trabalho futuro |
