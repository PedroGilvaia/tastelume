from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_optional_user
from ..events import emit_event
from ..models import Follow, User
from ..schemas import UserPrivate, UserPublic, UserUpdate

router = APIRouter(tags=["users"])


def _counts(db: Session, user_id: int) -> tuple[int, int]:
    followers = db.scalar(select(func.count()).where(Follow.followed_id == user_id)) or 0
    following = db.scalar(select(func.count()).where(Follow.follower_id == user_id)) or 0
    return followers, following


def to_public(db: Session, user: User, viewer: User | None) -> UserPublic:
    followers, following = _counts(db, user.id)
    is_following = None
    if viewer is not None:
        is_following = (
            db.get(Follow, (viewer.id, user.id)) is not None if viewer.id != user.id else False
        )
    return UserPublic(
        id=user.id,
        username=user.username,
        description=user.description,
        interests=user.interests,
        created_at=user.created_at,
        followers_count=followers,
        following_count=following,
        is_following=is_following,
    )


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilizador não encontrado.")
    return user


@router.get("/users/me", response_model=UserPrivate)
def read_me(me: User = Depends(get_current_user)):
    return me


@router.patch("/users/me", response_model=UserPrivate)
def update_me(data: UserUpdate, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.description is not None:
        me.description = data.description.strip()
    if data.interests is not None:
        me.interests = data.interests
    db.add(me)
    db.commit()
    return me


@router.get("/users", response_model=list[UserPublic])
def search_users(
    q: str = Query(default="", max_length=30, description="Parte do username"),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    stmt = select(User).order_by(User.username).limit(limit).offset(offset)
    q = q.strip()
    if q:
        escaped = q.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(func.lower(User.username).like(f"%{escaped}%", escape="\\"))
    return [to_public(db, u, viewer) for u in db.scalars(stmt)]


@router.get("/users/{user_id}", response_model=UserPublic)
def read_user(
    user_id: int, db: Session = Depends(get_db), viewer: User | None = Depends(get_optional_user)
):
    return to_public(db, _get_user_or_404(db, user_id), viewer)


@router.post("/users/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
def follow(
    user_id: int,
    background: BackgroundTasks,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user_id == me.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Não podes seguir-te a ti próprio.")
    target = _get_user_or_404(db, user_id)
    if db.get(Follow, (me.id, target.id)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Já segues este utilizador.")
    db.add(Follow(follower_id=me.id, followed_id=target.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já segues este utilizador.")
    # Para eventos "follow", recipe_owner_id identifica o utilizador seguido.
    background.add_task(emit_event, "follow", me.id, target.id, None, target.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/users/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
def unfollow(user_id: int, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_user_or_404(db, user_id)
    rel = db.get(Follow, (me.id, user_id))
    if rel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Não segues este utilizador.")
    db.delete(rel)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users/{user_id}/followers", response_model=list[UserPublic])
def followers(
    user_id: int,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    _get_user_or_404(db, user_id)
    stmt = (
        select(User)
        .join(Follow, Follow.follower_id == User.id)
        .where(Follow.followed_id == user_id)
        .order_by(Follow.created_at.desc(), User.id)
        .limit(limit)
        .offset(offset)
    )
    return [to_public(db, u, viewer) for u in db.scalars(stmt)]


@router.get("/users/{user_id}/following", response_model=list[UserPublic])
def following(
    user_id: int,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    _get_user_or_404(db, user_id)
    stmt = (
        select(User)
        .join(Follow, Follow.followed_id == User.id)
        .where(Follow.follower_id == user_id)
        .order_by(Follow.created_at.desc(), User.id)
        .limit(limit)
        .offset(offset)
    )
    return [to_public(db, u, viewer) for u in db.scalars(stmt)]
