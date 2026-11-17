"""Receção de eventos dos outros serviços (X-Internal-Token)."""
import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import clients
from ..auth import require_internal
from ..config import settings
from ..database import get_db
from ..models import Event, Notification
from ..schemas import EventAck, EventIn

logger = logging.getLogger("activity_service.events")
router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[Depends(require_internal)])

# Tipos que geram notificação direta para `target_user_id`.
DIRECT_TYPES = {"follow", "like", "comment", "rating", "share", "message"}
# Tipos em que o evento é "sobre o dono da receita" mesmo que o remetente não envie `target_user_id`.
OWNER_TYPES = {"like", "comment", "rating"}
# Repetir estas ações não deve encher a caixa de notificações: enquanto houver uma por ler
# do mesmo autor (e receita), não se cria outra.
DEDUP_TYPES = {"follow", "like", "rating", "message"}
# O Users Service envia `recipe_owner_id` = utilizador seguido nos follows e o Interaction Service
# não tem receita nas mensagens: nestes tipos o campo não descreve uma receita.
NO_RECIPE_TYPES = {"follow", "message"}


def _target(ev: EventIn) -> int | None:
    if ev.target_user_id is not None:
        return ev.target_user_id
    if ev.event_type in OWNER_TYPES:
        return ev.recipe_owner_id
    return None


def _already_pending(db: Session, user_id: int, ev: EventIn) -> bool:
    q = select(Notification.id).where(
        Notification.user_id == user_id,
        Notification.event_type == ev.event_type,
        Notification.read_at.is_(None),
        Notification.actor_id == ev.actor_id,
    )
    q = q.where(Notification.recipe_id == ev.recipe_id) if ev.recipe_id is not None \
        else q.where(Notification.recipe_id.is_(None))
    return db.scalar(q.limit(1)) is not None


@router.post("/events", response_model=EventAck, status_code=status.HTTP_201_CREATED)
def receive_event(ev: EventIn, db: Session = Depends(get_db)):
    """Guarda o evento e cria as notificações que dele derivam.

    - like/comment/rating/share/follow/message → notifica `target_user_id` (nunca o próprio autor da ação);
    - recipe_created → notifica os seguidores do autor (se o Users Service não responder, o evento
      fica registado e ninguém é notificado: falha silenciosa, sem erro para quem o enviou);
    - view → só estatísticas.
    """
    recipe_id = None if ev.event_type in NO_RECIPE_TYPES else ev.recipe_id
    owner_id = None if ev.event_type in NO_RECIPE_TYPES else ev.recipe_owner_id
    ev = ev.model_copy(update={"recipe_id": recipe_id, "recipe_owner_id": owner_id})

    event = Event(
        event_type=ev.event_type, actor_id=ev.actor_id, recipe_id=ev.recipe_id,
        recipe_owner_id=ev.recipe_owner_id, target_user_id=ev.target_user_id,
    )
    db.add(event)
    db.flush()

    recipients: list[int] = []
    if ev.event_type in DIRECT_TYPES:
        target = _target(ev)
        if target is not None and target != ev.actor_id:
            if not (ev.event_type in DEDUP_TYPES and _already_pending(db, target, ev)):
                recipients = [target]
    elif ev.event_type == "recipe_created" and ev.actor_id is not None:
        try:
            followers = clients.follower_ids(ev.actor_id)
        except clients.Unavailable:
            logger.warning("Seguidores de %s indisponíveis; sem notificações para a receita %s.",
                           ev.actor_id, ev.recipe_id)
            followers = []
        recipients = [f for f in dict.fromkeys(followers) if f != ev.actor_id][: settings.max_fanout]

    db.add_all(
        Notification(
            user_id=uid, event_id=event.id, event_type=ev.event_type,
            actor_id=ev.actor_id, recipe_id=ev.recipe_id,
        )
        for uid in recipients
    )
    db.commit()
    return EventAck(event_id=event.id, notifications_created=len(recipients))
