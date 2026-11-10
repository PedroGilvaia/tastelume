[Uploading architecture.md…]()
# Arquitetura

## Serviços
Cada serviço tem código, contentor e base de dados PostgreSQL próprios. Nenhum serviço acede à BD de outro; a comunicação faz-se por REST.

| Serviço | Responsabilidade | Porta |
|---|---|---|
| users_service | autenticação, perfis, interesses, seguidores | 8001 |
| recipe_service | receitas, categorias, pesquisa, imagens | 8002 |
| interaction_service | comentários, likes, avaliações, favoritos, partilhas, mensagens | 8003 |
| activity_service | eventos, notificações, estatísticas | 8004 |

## Autenticação
- O Users Service emite JWT (HS256) com `sub` = id do utilizador, `username`, `iat` e `exp`.
- Os restantes serviços **validam localmente** a assinatura com o `JWT_SECRET` partilhado (sem chamar o Users Service em cada pedido).
- Compromisso assumido: um utilizador apagado continua com token válido nos outros serviços até expirar. O Users Service verifica sempre a existência do utilizador. (Não há endpoint de apagar conta.)

## Comunicação entre serviços
- Endpoints `/internal/*` exigem o cabeçalho `X-Internal-Token` (segredo partilhado, comparação em tempo constante). Um JWT de utilizador **não** dá acesso.
- Eventos para o Activity Service são **best-effort**: timeout de 2 s, executados em background, falhas só são registadas em log. A indisponibilidade do Activity Service nunca falha a operação principal (testado em `test_follow_succeeds_when_activity_service_is_down`).
- Payload dos eventos para `POST /internal/events`: `{event_type, actor_id, recipe_id?, recipe_owner_id?, target_user_id?}`.
  `target_user_id` é **quem deve ser notificado** (dono da receita em comment/like/rating; destinatário em share/message; utilizador seguido em follow). O Activity Service ignora notificações em que `actor_id == target_user_id`.

## Dados e integridade (Users Service)
- `username` único sem distinguir maiúsculas (índice em `lower(username)`); `email` único e normalizado para minúsculas.
- `follows`: chave primária composta (sem duplicados) + `CHECK (follower_id <> followed_id)`.
- Passwords com bcrypt; limite de 72 bytes validado na API.
- Contagens de seguidores/seguidos calculadas por `COUNT` na altura da consulta (sem contadores desnormalizados que possam divergir).
- `login` devolve a mesma resposta para utilizador inexistente e password errada, e gasta tempo equivalente a uma verificação bcrypt.
- O número de receitas de um perfil pertence ao Recipe Service; a app agrega ambas as respostas.

## API do Users Service
Documentação interativa: `/docs` (OpenAPI).

| Método e caminho | Auth | Respostas |
|---|---|---|
| POST /auth/register | — | 201, 409 (username/email existente), 422 |
| POST /auth/login `{identifier, password}` | — | 200 `{access_token, token_type, expires_in}`, 401 |
| GET /users/me | JWT | 200, 401 |
| PATCH /users/me `{description?, interests?}` | JWT | 200, 401, 422 |
| GET /users?q=&limit=&offset= | opcional | 200 (perfis públicos, sem email) |
| GET /users/{id} | opcional | 200 (`is_following` só com sessão), 404 |
| POST /users/{id}/follow | JWT | 204, 400 (a si próprio), 401, 404, 409 |
| DELETE /users/{id}/follow | JWT | 204, 401, 404 |
| GET /users/{id}/followers · /following | opcional | 200, 404 |
| GET /internal/users?ids= · /internal/users/{id} · /internal/users/by-username/{u} · /internal/users/{id}/follower-ids | X-Internal-Token | 200, 400, 401, 403, 404 |
| GET /health | — | 200 / 503 |


---

# Recipe Service (Fase 2)

## Contagens e estatísticas
Cada receita guarda contadores desnormalizados (`view_count`, `like_count`, `comment_count`, `rating_count`, `rating_avg`) para permitir ordenar e paginar sem consultar outros serviços.

| Contador | Quem o calcula | Como chega ao Recipe Service |
|---|---|---|
| `view_count` | Recipe Service | `POST /recipes/{id}/view` (ver regra abaixo) |
| `like_count`, `comment_count`, `rating_count`, `rating_avg` | Interaction Service (dono dos dados) | `PUT /internal/recipes/{id}/counters` com **totais absolutos** |

Os totais são absolutos (e não incrementos) para que repetir ou perder um pedido nunca corrompa o valor: o pedido seguinte repõe o valor correto. `rating_count = 0` implica `rating_avg = null` ("não classificada").

## Regra das visualizações
- A app chama `POST /recipes/{id}/view` **uma vez** ao abrir o detalhe; `GET /recipes/{id}` nunca conta.
- Cada visitante conta no máximo **1 vez por receita em cada janela de 30 minutos** (`VIEW_WINDOW_MINUTES`). Utilizador autenticado: chave `u:<id>`; anónimo: cabeçalho `X-Client-Id` ou, na falta dele, o IP.
- O autor não conta as próprias visualizações.
- Só visualizações contadas geram o evento `view` para o Activity Service.

## Popularidade
`popularidade = visualizações + 3·likes + 4·comentários + 2·(nº avaliações × média)` — definida uma única vez (`popularity_expr`) e usada por `sort=popular` (omissão, o que os visitantes veem), pelo desempate das receitas relacionadas e em qualquer ordenação futura.

`sort=rating` coloca as receitas não classificadas no fim.

## Personalização
`GET /recipes?personalized=true` (com sessão): o Recipe Service pede os interesses ao Users Service e coloca primeiro as receitas cujas categorias (slug ou nome, sem acentos nem maiúsculas) coincidem com os interesses; dentro de cada grupo aplica-se a ordenação pedida. Sem sessão, ou com o Users Service em baixo, o parâmetro é ignorado sem erro.

## Resiliência
- `UsersClient`: timeout de 2 s, cache de 60 s e *circuit breaker* (após uma falha não volta a tentar durante 15 s) — um Users Service lento não atrasa o feed.
- Sem o Users Service, as receitas continuam a ser listadas, abertas e **criadas** (o JWT é validado localmente); apenas `author_username` vem a `null`.
- Eventos para o Activity Service são best-effort, em background.

## Imagens
- `POST /recipes/{id}/image` (multipart, só o autor): limite de 5 MB; o formato é determinado pelos **bytes iniciais** (JPEG/PNG/WebP), não pelo `Content-Type` nem pelo nome enviados.
- O ficheiro é guardado com nome gerado pelo servidor (`uuid4().ext`) no volume `recipe_images`; a BD guarda só o nome.
- `GET /images/{nome}` só serve nomes que cumpram `^[a-f0-9]{32}\.(jpg|png|webp)$` (sem *path traversal*), com `nosniff`.
- Ao substituir a imagem ou apagar a receita, o ficheiro antigo é removido.

## API do Recipe Service
| Método e caminho | Auth | Respostas |
|---|---|---|
| GET /categories | — | 200 |
| GET /recipes `?q&ingredient&category&author_id&sort&personalized&limit&offset` | opcional | 200 (+`X-Total-Count`), 422 |
| POST /recipes | JWT | 201, 401, 422 |
| GET /recipes/{id} | — | 200, 404 |
| PATCH /recipes/{id} | JWT (autor) | 200, 401, 403, 404, 422 |
| DELETE /recipes/{id} | JWT (autor) | 204, 401, 403, 404 |
| GET /recipes/{id}/related | — | 200, 404 |
| POST /recipes/{id}/view | opcional | 200 `{counted, view_count}`, 404 |
| POST /recipes/{id}/image | JWT (autor) | 200, 401, 403, 404, 413, 415 |
| GET /images/{nome} | — | 200, 404 |
| GET /users/{id}/recipes | — | 200 (+`X-Total-Count`) |
| GET /internal/recipes?ids= · /internal/recipes/{id} | X-Internal-Token | 200, 400, 401, 403, 404 |
| PUT /internal/recipes/{id}/counters | X-Internal-Token | 204, 401, 403, 404, 422 |

Modelo de receita: `ingredients` = lista de `{name, quantity?, unit?}`; `preparation_steps` = lista ordenada (a API devolve `{order, text}`); `difficulty` ∈ `facil|media|dificil`; `preparation_time` em minutos.


---

# Interaction Service (Fase 3)

## Regras de integridade
| Regra | Garantia |
|---|---|
| 1 like por utilizador e receita | `UNIQUE(recipe_id, user_id)`; duplicado → 409 (também sob pedidos simultâneos) |
| 1 avaliação por utilizador e receita, atualizável | `UNIQUE(recipe_id, user_id)` + `CHECK(score BETWEEN 1 AND 5)`; POST cria (201) ou atualiza (200) |
| Comentários só editáveis/apagáveis pelo autor | verificação no backend → 403 |
| Listas de favoritos só do dono | verificação no backend → 403; nome único por utilizador (sem distinguir maiúsculas) |
| Mensagens privadas | todas as queries filtram pelo utilizador do token; não há forma de pedir a conversa de terceiros |
| Sem auto-mensagem / auto-partilha | `CHECK(sender_id <> recipient_id)` e 400 |
| Ids de receita/utilizador válidos | validados no Recipe/Users Service antes de gravar |

## Validação entre serviços: 404 vs 503
Ao gravar (comentar, gostar, avaliar, favoritar, partilhar, enviar mensagem), o serviço valida o id no serviço dono. Se o id não existir → **404**. Se o serviço dono não responder → **503** com `Retry-After`, e **nada é gravado**: nunca se aceita um id só porque não foi possível validá-lo. As leituras (comentários, resumo de interações, favoritos, mensagens) não dependem dos outros serviços; apenas perdem enriquecimentos (`username`, `recipe_title` → `null`).

Cada serviço remoto tem um *circuit breaker* (15 s): após uma falha, os pedidos seguintes falham de imediato em vez de esperar pelo timeout.

## Contadores para o Recipe Service
Depois de cada like/unlike, comentário/remoção ou avaliação, o Interaction Service recalcula os **totais absolutos** a partir da sua BD e envia-os por `PUT /internal/recipes/{id}/counters` (em background). Se o envio falhar, o valor certo é reposto pela interação seguinte nessa receita ou por `POST /internal/recipes/{id}/resync-counters`. O resumo `GET /recipes/{id}/interactions` lê sempre da BD local, por isso o detalhe nunca mostra valores desatualizados.

## Receitas apagadas
O Recipe Service chama `DELETE /internal/recipes/{id}/data` (best-effort, idempotente) para apagar comentários, likes, avaliações, entradas em favoritos e partilhas dessa receita. Se falhar, ficam dados órfãos inofensivos: a app só mostra receitas que o Recipe Service ainda devolve (`GET /recipes?ids=`).

## Mensagens
Sem tempo real: a app consulta `GET /messages/{id}?after_id=<último>` periodicamente. Ler a conversa marca como lidas as mensagens recebidas (`read_at`), visível ao remetente.

## API do Interaction Service
| Método e caminho | Auth | Respostas |
|---|---|---|
| GET /recipes/{id}/interactions | opcional | 200 (likes, comentários, avaliações, `my_like`, `my_score`) |
| GET /recipes/{id}/comments `?limit&offset` | — | 200 (+`X-Total-Count`) |
| POST /recipes/{id}/comments | JWT | 201, 401, 404, 422, 503 |
| PATCH · DELETE /comments/{id} | JWT (autor) | 200/204, 401, 403, 404, 422 |
| POST · DELETE /recipes/{id}/like | JWT | 204, 401, 404, 409 (só POST), 503 |
| POST /recipes/{id}/ratings `{score}` | JWT | 201 (nova), 200 (atualizada), 401, 404, 422, 503 |
| GET /recipes/{id}/ratings | opcional | 200 (média, total, distribuição 1–5) |
| GET · POST /favorite-collections | JWT | 200/201, 401, 409, 422 |
| GET · DELETE /favorite-collections/{id} | JWT (dono) | 200/204, 403, 404 |
| POST · DELETE /favorite-collections/{id}/recipes/{rid} | JWT (dono) | 201/204, 403, 404, 409, 503 |
| POST /recipes/{id}/share `{recipient_username}` | JWT | 201, 400, 404, 503 |
| GET /shares/received | JWT | 200 |
| GET /messages/conversations | JWT | 200 (último texto + não lidas) |
| GET /messages/{user_id} `?after_id&limit` | JWT | 200 |
| POST /messages/{user_id} | JWT | 201, 400, 404, 422, 503 |
| DELETE /internal/recipes/{id}/data · POST /internal/recipes/{id}/resync-counters | X-Internal-Token | 204, 401, 403 |
