"""Chamadas ao Users, Recipe e Activity Service.

- Validações (existe a receita/utilizador?) distinguem "não existe" (None → 404) de
  "serviço indisponível" (Unavailable → 503): nunca se aceita um id por não se conseguir validar.
- Enriquecimentos e eventos são best-effort: falham em silêncio.
- Circuit breaker por serviço: após uma falha não se volta a tentar durante `breaker_cooldown` s.
"""
import logging
import time

import httpx

from .config import settings

logger = logging.getLogger("interaction_service.clients")


class Unavailable(Exception):
    def __init__(self, service: str) -> None:
        super().__init__(service)
        self.service = service


_down_until: dict[str, float] = {}
_cache: dict[tuple[str, int], tuple[float, dict]] = {}
_CACHE_TTL = 60.0


def reset() -> None:
    _down_until.clear()
    _cache.clear()


def _base(service: str) -> str:
    return {"users": settings.users_service_url, "recipes": settings.recipe_service_url,
            "activity": settings.activity_service_url}[service]


def _call(service: str, method: str, path: str, **kw) -> httpx.Response:
    base = _base(service)
    if not base or time.monotonic() < _down_until.get(service, 0.0):
        raise Unavailable(service)
    try:
        resp = httpx.request(
            method, f"{base}{path}", headers={"X-Internal-Token": settings.internal_token},
            timeout=settings.http_timeout, **kw,
        )
    except httpx.HTTPError:
        logger.warning("%s service indisponível.", service)
        _down_until[service] = time.monotonic() + settings.breaker_cooldown
        raise Unavailable(service)
    if resp.status_code >= 500:
        _down_until[service] = time.monotonic() + settings.breaker_cooldown
        raise Unavailable(service)
    return resp


def _one(service: str, path: str) -> dict | None:
    resp = _call(service, "GET", path)
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:  # p. ex. token interno mal configurado: tratar como indisponível
        logger.error("%s service respondeu %s a %s", service, resp.status_code, path)
        raise Unavailable(service)
    return resp.json()


# ---- validações (lançam Unavailable) ----
def recipe_by_id(recipe_id: int) -> dict | None:
    return _one("recipes", f"/internal/recipes/{recipe_id}")


def user_by_id(user_id: int) -> dict | None:
    return _one("users", f"/internal/users/{user_id}")


def user_by_username(username: str) -> dict | None:
    return _one("users", f"/internal/users/by-username/{username}")


# ---- enriquecimentos (best-effort) ----
def _many(service: str, path: str, ids: set[int]) -> dict[int, dict]:
    if not ids:
        return {}
    now = time.monotonic()
    found = {i: v[1] for i in ids if (v := _cache.get((service, i))) and v[0] > now}
    missing = ids - found.keys()
    if missing:
        try:
            resp = _call(service, "GET", path, params={"ids": ",".join(str(i) for i in sorted(missing))})
            if resp.status_code == 200:
                for item in resp.json():
                    _cache[(service, item["id"])] = (now + _CACHE_TTL, item)
                    found[item["id"]] = item
        except (Unavailable, ValueError, KeyError):
            pass
    return found


def users_map(ids: set[int]) -> dict[int, dict]:
    return _many("users", "/internal/users", ids)


def recipes_map(ids: set[int]) -> dict[int, dict]:
    return _many("recipes", "/internal/recipes", ids)


# ---- efeitos laterais (best-effort) ----
def push_counters(recipe_id: int, totals: dict) -> None:
    """Totais absolutos: se falhar, o pedido seguinte (ou /resync-counters) repõe o valor certo."""
    try:
        _call("recipes", "PUT", f"/internal/recipes/{recipe_id}/counters", json=totals)
    except Unavailable:
        logger.warning("Contadores da receita %s não sincronizados.", recipe_id)


def emit_event(
    event_type: str,
    actor_id: int,
    recipe_id: int | None = None,
    recipe_owner_id: int | None = None,
    target_user_id: int | None = None,
) -> None:
    try:
        _call(
            "activity", "POST", "/internal/events",
            json={"event_type": event_type, "actor_id": actor_id, "recipe_id": recipe_id,
                  "recipe_owner_id": recipe_owner_id, "target_user_id": target_user_id},
        )
    except Unavailable:
        logger.warning("Evento '%s' não registado.", event_type)
