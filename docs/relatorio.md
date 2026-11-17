# Tastelume — Relatório

> Rascunho com a estrutura pedida e o conteúdo técnico já preenchido. Completa o que está entre `[…]` e acrescenta capturas de ecrã e os diagramas (`tastelume_diagramas.zip`).

**Unidade curricular:** […] **Aluno:** Pedro Gilvaia […] **Data:** […]

## 1. Introdução
A Tastelume é uma rede social de partilha de receitas culinárias: os utilizadores publicam receitas com fotografia (tirada com a câmara do telemóvel), seguem outros utilizadores, gostam, avaliam e comentam, guardam favoritos, trocam mensagens e acompanham estatísticas da sua atividade.

## 2. Requisitos
**Funcionais:** autenticação; CRUD de receitas com imagem; categorias, pesquisa (texto/ingrediente), ordenação e paginação; feed personalizado por interesses; gostos, avaliações (1–5), comentários; listas de favoritos; partilha de receitas; seguidores; mensagens; notificações; estatísticas.
**Não funcionais:** uso obrigatório da câmara; **degradação graciosa** quando um serviço falha; serviços independentes, cada um com a sua base de dados; execução reprodutível com Docker Compose.

## 3. Arquitetura
Ver `docs/architecture.md` (detalhe por serviço e tabelas de endpoints).

- **Quatro microserviços FastAPI**, cada um com a sua base PostgreSQL: **Users** (8001), **Recipe** (8002), **Interaction** (8003), **Activity** (8004).
- **JWT partilhado:** só o Users Service emite tokens; os restantes validam-nos localmente com o mesmo segredo, pelo que continuam a autenticar pedidos mesmo com o Users Service em baixo.
- **Comunicação entre serviços** por HTTP, com `INTERNAL_SERVICE_TOKEN` em `/internal/*`, timeouts curtos e *cache* de curta duração de nomes de utilizador.
- **Consistência:** os contadores das receitas (gostos, comentários, avaliações, visualizações) são mantidos pelo Interaction Service e enviados ao Recipe Service como **totais absolutos** (`PUT /internal/recipes/{id}/counters`), tornando as atualizações idempotentes; os eventos para o Activity Service são *fire-and-forget*.
- **Resiliência:** 404 (não existe) distingue-se de 503 (não foi possível validar); nunca se grava um dado que dependa de uma validação que não foi feita.

## 4. Aplicação móvel
Flutter com **MVVM + Provider** (`mobile_app/README.md`):
- **Model** — classes imutáveis com `fromJson`;
- **Service** — quatro clientes de API sobre um `ApiClient` comum (JWT, *timeout*, conversão de erros em `ApiException`, mensagens de validação em português);
- **ViewModel** — `ChangeNotifier` por ecrã, com estados independentes por serviço (ex.: o detalhe da receita separa conteúdo, interações, comentários e relacionadas);
- **View** — ecrãs e componentes reutilizáveis.

Pontos técnicos: sessão em `flutter_secure_storage`; *polling* (30 s) do emblema de notificações e (5 s) das mensagens, por o backend não ter tempo real; gostos otimistas com reversão; `image_picker` para câmara/galeria; paginação infinita; deteção de sessão expirada (401) com regresso ao login.

## 5. Testes
Ver `docs/testes.md`: 104 testes de backend, 19 verificações ponta-a-ponta (incluindo desligar serviços) e testes unitários Flutter.

## 6. Limitações e trabalho futuro
Notificações push/WebSocket; HTTPS e gestão de segredos; testes de widgets e de integração no dispositivo; moderação de conteúdos; cache offline na app.

## 7. Conclusão
[…]

## Anexos
Repositório GitHub: https://github.com/PedroGilvaia/tastelume · Vídeo de demonstração: […] (guião em `docs/guiao-demo.md`).
