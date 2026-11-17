"""Chamadas ao Users e Recipe Service (só leitura, para enriquecer respostas e obter seguidores).

- `follower_ids` lança `Unavailable` quando o Users Service não responde: o chamador decide o que fazer.
- Os enriquecimentos (`users_map`, `recipes_map`) são best-effort: falham em silêncio.
- Circuit breaker por serviço: após uma falha não se volta a tentar durante `breaker_cooldown` s.
"""
import logging
import time

import httpx

from .config import settings

logger = logging.getLogger("activity_service.clients")


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
    return {"users": settings.users_service_url, "recipes": settings.recipe_service_url}[service]


def _call(service: str, path: str, **kw) -> httpx.Response:
    base = _base(service)
    if not base or time.monotonic() < _down_until.get(service, 0.0):
        raise Unavailable(service)
    try:
        resp = httpx.request(
            "GET", f"{base}{path}", headers={"X-Internal-Token": settings.internal_token},
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


def follower_ids(user_id: int) -> list[int]:
    resp = _call("users", f"/internal/users/{user_id}/follower-ids")
    if resp.status_code != 200:
        logger.error("Users Service respondeu %s a follower-ids.", resp.status_code)
        raise Unavailable("users")
    return [int(i) for i in resp.json()]


def _many(service: str, path: str, ids: set[int]) -> dict[int, dict]:
    ids = set(ids)
    if not ids:
        return {}
    now = time.monotonic()
    found = {i: v[1] for i in ids if (v := _cache.get((service, i))) and v[0] > now}
    missing = sorted(ids - found.keys())
    # O Users/Recipe Service aceitam no máximo 100 ids por pedido.
    for start in range(0, len(missing), 100):
        chunk = missing[start:start + 100]
        try:
            resp = _call(service, path, params={"ids": ",".join(str(i) for i in chunk)})
            if resp.status_code == 200:
                for item in resp.json():
                    _cache[(service, item["id"])] = (now + _CACHE_TTL, item)
                    found[item["id"]] = item
        except (Unavailable, ValueError, KeyError):
            break
    return found


def users_map(ids: set[int]) -> dict[int, dict]:
    return _many("users", "/internal/users", ids)


def recipes_map(ids: set[int]) -> dict[int, dict]:
    return _many("recipes", "/internal/recipes", ids)
