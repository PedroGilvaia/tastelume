"""Chamadas a outros serviços, sempre com timeout e degradação graciosa."""
import logging
import time

import httpx

from .config import settings

logger = logging.getLogger("recipe_service.clients")


class UsersClient:
    """Obtém username/interesses ao Users Service.

    - cache em memória (TTL) para evitar pedidos repetidos;
    - circuit breaker simples: após uma falha, não volta a tentar durante `cooldown` segundos,
      para que um Users Service lento não atrase todos os pedidos (falha em cascata).
    """

    def __init__(self, ttl: float = 60.0, cooldown: float = 15.0) -> None:
        self.ttl = ttl
        self.cooldown = cooldown
        self.reset()

    def reset(self) -> None:
        self._cache: dict[int, tuple[float, dict]] = {}
        self._down_until = 0.0

    def _fetch(self, ids: set[int]) -> dict[int, dict]:
        resp = httpx.get(
            f"{settings.users_service_url}/internal/users",
            params={"ids": ",".join(str(i) for i in sorted(ids))},
            headers={"X-Internal-Token": settings.internal_token},
            timeout=settings.http_timeout,
        )
        resp.raise_for_status()
        return {u["id"]: u for u in resp.json()}

    def get_users(self, ids: set[int]) -> dict[int, dict]:
        if not ids or not settings.users_service_url:
            return {}
        now = time.monotonic()
        found = {i: v[1] for i in ids if (v := self._cache.get(i)) and v[0] > now}
        missing = ids - found.keys()
        if missing and now >= self._down_until:
            try:
                fetched = self._fetch(missing)
            except (httpx.HTTPError, ValueError, KeyError):
                logger.warning("Users Service indisponível; a continuar sem dados de autor.")
                self._down_until = now + self.cooldown
            else:
                for uid, data in fetched.items():
                    self._cache[uid] = (now + self.ttl, data)
                found.update(fetched)
        return found


users_client = UsersClient()


def emit_event(
    event_type: str, actor_id: int | None, recipe_id: int | None, recipe_owner_id: int | None
) -> None:
    """Evento para o Activity Service (best-effort: nunca propaga falhas)."""
    if not settings.activity_service_url:
        return
    try:
        httpx.post(
            f"{settings.activity_service_url}/internal/events",
            json={
                "event_type": event_type,
                "actor_id": actor_id,
                "recipe_id": recipe_id,
                "recipe_owner_id": recipe_owner_id,
            },
            headers={"X-Internal-Token": settings.internal_token},
            timeout=settings.http_timeout,
        )
    except httpx.HTTPError:
        logger.warning("Activity Service indisponível; evento '%s' não registado.", event_type)


def purge_interactions(recipe_id: int) -> None:
    """Pede ao Interaction Service que apague comentários, likes, etc. de uma receita apagada (best-effort)."""
    if not settings.interaction_service_url:
        return
    try:
        httpx.delete(
            f"{settings.interaction_service_url}/internal/recipes/{recipe_id}/data",
            headers={"X-Internal-Token": settings.internal_token},
            timeout=settings.http_timeout,
        )
    except httpx.HTTPError:
        logger.warning("Interaction Service indisponível; dados da receita %s ficam órfãos.", recipe_id)
