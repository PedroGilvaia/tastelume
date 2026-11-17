"""Caixa de notificações do utilizador autenticado."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .. import clients
from ..auth import AuthUser, get_current_user
from ..database import get_db
from ..models import Notification, utcnow
from ..schemas import NotificationOut, UnreadCount

router = APIRouter(prefix="/notifications", tags=["notifications"])

_TEXTS = {
    "follow": "{actor} começou a seguir-te.",
    "like": "{actor} gostou da tua receita{recipe}.",
    "comment": "{actor} comentou a tua receita{recipe}.",
    "rating": "{actor} avaliou a tua receita{recipe}.",
    "share": "{actor} partilhou contigo uma receita{recipe}.",
    "message": "{actor} enviou-te uma mensagem.",
    "recipe_created": "{actor} publicou uma nova receita{recipe}.",
}


def _text(kind: str, actor: str | None, recipe: str | None) -> str:
    """Se faltar o nome ou o título (serviço indisponível), usa uma formulação neutra."""
    return _TEXTS[kind].format(actor=actor or "Alguém", recipe=f" «{recipe}»" if recipe else "")


def _unread(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.count()).where(Notification.user_id == user_id, Notification.read_at.is_(None))
    ) or 0


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    response: Response,
    unread_only: bool = False,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """Mais recentes primeiro. `X-Total-Count` = total da lista pedida; `X-Unread-Count` = por ler."""
    base = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        base = base.where(Notification.read_at.is_(None))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = list(db.scalars(base.order_by(Notification.created_at.desc(), Notification.id.desc())
                           .limit(limit).offset(offset)))
    users = clients.users_map({n.actor_id for n in rows if n.actor_id is not None})
    recipes = clients.recipes_map({n.recipe_id for n in rows if n.recipe_id is not None})
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Unread-Count"] = str(_unread(db, user.id))
    out = []
    for n in rows:
        actor = (users.get(n.actor_id) or {}).get("username") if n.actor_id is not None else None
        title = (recipes.get(n.recipe_id) or {}).get("title") if n.recipe_id is not None else None
        out.append(NotificationOut(
            id=n.id, type=n.event_type, actor_id=n.actor_id, actor_username=actor,
            recipe_id=n.recipe_id, recipe_title=title, text=_text(n.event_type, actor, title),
            read=n.read_at is not None, created_at=n.created_at,
        ))
    return out


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    """Leve e sem dependências de outros serviços: serve para o emblema da app (consulta periódica)."""
    return UnreadCount(unread=_unread(db, user.id))


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def read_all(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=utcnow())
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(notification_id: int, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    """Idempotente. Uma notificação de outro utilizador responde 404 (não revela que existe)."""
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notificação não encontrada.")
    if n.read_at is None:
        n.read_at = utcnow()
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
