"""Partilha de receitas e mensagens diretas."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.orm import Session

from .. import clients
from ..auth import AuthUser, get_current_user
from ..database import get_db
from ..models import DirectMessage, RecipeShare, utcnow
from ..schemas import ConversationOut, MessageIn, MessageOut, ShareIn, ShareOut
from .interactions import ensure_recipe

router = APIRouter(tags=["social"])


# ---------- partilhas ----------
@router.post("/recipes/{recipe_id}/share", response_model=ShareOut, status_code=status.HTTP_201_CREATED)
def share_recipe(
    recipe_id: int, data: ShareIn, background: BackgroundTasks,
    user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db),
):
    recipe = ensure_recipe(recipe_id)
    recipient = clients.user_by_username(data.recipient_username.strip())
    if recipient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilizador não encontrado.")
    if recipient["id"] == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Não podes partilhar contigo próprio.")
    share = RecipeShare(sender_id=user.id, recipient_id=recipient["id"], recipe_id=recipe_id)
    db.add(share)
    db.commit()
    background.add_task(clients.emit_event, "share", user.id, recipe_id, recipe["author_id"], recipient["id"])
    return ShareOut(
        id=share.id, sender_id=user.id, sender_username=user.username, recipient_id=recipient["id"],
        recipe_id=recipe_id, recipe_title=recipe["title"], created_at=share.created_at,
    )


@router.get("/shares/received", response_model=list[ShareOut])
def received_shares(
    limit: int = Query(default=20, ge=1, le=50), offset: int = Query(default=0, ge=0),
    user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db),
):
    shares = list(db.scalars(
        select(RecipeShare).where(RecipeShare.recipient_id == user.id)
        .order_by(RecipeShare.created_at.desc(), RecipeShare.id.desc()).limit(limit).offset(offset)
    ))
    names = clients.users_map({s.sender_id for s in shares})
    recipes = clients.recipes_map({s.recipe_id for s in shares})
    return [
        ShareOut(
            id=s.id, sender_id=s.sender_id, sender_username=(names.get(s.sender_id) or {}).get("username"),
            recipient_id=s.recipient_id, recipe_id=s.recipe_id,
            recipe_title=(recipes.get(s.recipe_id) or {}).get("title"), created_at=s.created_at,
        )
        for s in shares
    ]


# ---------- mensagens ----------
@router.get("/messages/conversations", response_model=list[ConversationOut])
def conversations(user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    other = case((DirectMessage.sender_id == user.id, DirectMessage.recipient_id), else_=DirectMessage.sender_id)
    mine = or_(DirectMessage.sender_id == user.id, DirectMessage.recipient_id == user.id)
    unread = func.sum(case((and_(DirectMessage.recipient_id == user.id, DirectMessage.read_at.is_(None)), 1), else_=0))
    rows = db.execute(
        select(other.label("other"), func.max(DirectMessage.id).label("last_id"), unread.label("unread"))
        .where(mine).group_by(other).order_by(func.max(DirectMessage.id).desc())
    ).all()
    last = {m.id: m for m in db.scalars(select(DirectMessage).where(DirectMessage.id.in_([r.last_id for r in rows])))}
    names = clients.users_map({r.other for r in rows})
    return [
        ConversationOut(
            user_id=r.other, username=(names.get(r.other) or {}).get("username"),
            last_message=MessageOut.model_validate(last[r.last_id], from_attributes=True),
            unread_count=int(r.unread or 0),
        )
        for r in rows
    ]


@router.get("/messages/{user_id}", response_model=list[MessageOut])
def read_conversation(
    user_id: int,
    after_id: int = Query(default=0, ge=0, description="Só mensagens com id maior (útil para atualização periódica)"),
    limit: int = Query(default=100, ge=1, le=200),
    user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db),
):
    """Só devolve a conversa entre o utilizador autenticado e `user_id`; ao lê-la marca como lidas as recebidas."""
    pair = or_(
        and_(DirectMessage.sender_id == user.id, DirectMessage.recipient_id == user_id),
        and_(DirectMessage.sender_id == user_id, DirectMessage.recipient_id == user.id),
    )
    db.execute(
        update(DirectMessage)
        .where(DirectMessage.sender_id == user_id, DirectMessage.recipient_id == user.id, DirectMessage.read_at.is_(None))
        .values(read_at=utcnow())
    )
    db.commit()
    msgs = db.scalars(select(DirectMessage).where(pair, DirectMessage.id > after_id).order_by(DirectMessage.id).limit(limit))
    return [MessageOut.model_validate(m, from_attributes=True) for m in msgs]


@router.post("/messages/{user_id}", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(
    user_id: int, data: MessageIn, background: BackgroundTasks,
    user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db),
):
    if user_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Não podes enviar mensagens a ti próprio.")
    if clients.user_by_id(user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilizador não encontrado.")
    msg = DirectMessage(sender_id=user.id, recipient_id=user_id, text=data.text)
    db.add(msg)
    db.commit()
    background.add_task(clients.emit_event, "message", user.id, None, None, user_id)
    return MessageOut.model_validate(msg, from_attributes=True)
