import logging

import httpx

from .config import settings

logger = logging.getLogger("users_service.events")


def emit_event(
    event_type: str,
    actor_id: int,
    recipe_owner_id: int | None = None,
    recipe_id: int | None = None,
    target_user_id: int | None = None,
) -> None:
    """Envia um evento ao Activity Service (best-effort).

    Falhas são apenas registadas: a indisponibilidade do Activity Service nunca
    pode impedir uma operação principal (ex.: seguir um utilizador).
    """
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
                "target_user_id": target_user_id,
            },
            headers={"X-Internal-Token": settings.internal_token},
            timeout=settings.activity_timeout,
        )
    except httpx.HTTPError:
        logger.warning("Activity Service indisponível; evento '%s' não registado.", event_type)
