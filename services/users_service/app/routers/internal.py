"""Endpoints para comunicação entre serviços. Exigem o cabeçalho X-Internal-Token."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_internal
from ..models import Follow, User
from ..schemas import InternalUser

router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[Depends(require_internal)])


@router.get("/users", response_model=list[InternalUser])
def users_by_ids(
    ids: str = Query(description="IDs separados por vírgula (máx. 100)"),
    db: Session = Depends(get_db),
):
    try:
        wanted = {int(i) for i in ids.split(",") if i.strip()}
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Lista de ids inválida.")
    if not wanted or len(wanted) > 100:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Indica entre 1 e 100 ids.")
    return list(db.scalars(select(User).where(User.id.in_(wanted))))


@router.get("/users/by-username/{username}", response_model=InternalUser)
def user_by_username(username: str, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.username) == username.lower()))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilizador não encontrado.")
    return user


@router.get("/users/{user_id}", response_model=InternalUser)
def user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilizador não encontrado.")
    return user


@router.get("/users/{user_id}/follower-ids", response_model=list[int])
def follower_ids(user_id: int, db: Session = Depends(get_db)):
    """Ids de quem segue `user_id` (usado para notificar novas receitas)."""
    return list(db.scalars(select(Follow.follower_id).where(Follow.followed_id == user_id)))
