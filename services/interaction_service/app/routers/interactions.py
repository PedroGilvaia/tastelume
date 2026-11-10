"""Comentários, likes e avaliações."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import clients
from ..auth import AuthUser, get_current_user, get_optional_user
from ..database import get_db
from ..models import Comment, Like, Rating, utcnow
from ..schemas import CommentIn, CommentOut, InteractionSummary, RatingIn, RatingSummary

router = APIRouter(tags=["interactions"])


# ---------- helpers ----------
def ensure_recipe(recipe_id: int) -> dict:
    """404 se a receita não existe; 503 (via Unavailable) se não for possível validar."""
    recipe = clients.recipe_by_id(recipe_id)
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada.")
    return recipe


def rating_summary(db: Session, recipe_id: int, user_id: int | None = None) -> RatingSummary:
    rows = db.execute(
        select(Rating.score, func.count()).where(Rating.recipe_id == recipe_id).group_by(Rating.score)
    ).all()
    dist = {str(n): 0 for n in range(1, 6)}
    for score, n in rows:
        dist[str(score)] = n
    count = sum(dist.values())
    average = round(sum(int(k) * v for k, v in dist.items()) / count, 2) if count else None
    my = None
    if user_id is not None:
        my = db.scalar(select(Rating.score).where(Rating.recipe_id == recipe_id, Rating.user_id == user_id))
    return RatingSummary(average=average, count=count, distribution=dist, my_score=my)


def counters(db: Session, recipe_id: int) -> dict:
    """Totais absolutos para o Recipe Service (ver docs/architecture.md)."""
    rating = rating_summary(db, recipe_id)
    return {
        "like_count": db.scalar(select(func.count()).where(Like.recipe_id == recipe_id)) or 0,
        "comment_count": db.scalar(select(func.count()).where(Comment.recipe_id == recipe_id)) or 0,
        "rating_count": rating.count,
        "rating_avg": rating.average,
    }


def _sync(background: BackgroundTasks, db: Session, recipe_id: int) -> None:
    background.add_task(clients.push_counters, recipe_id, counters(db, recipe_id))


def _comment_out(c: Comment, names: dict[int, dict]) -> CommentOut:
    return CommentOut(
        id=c.id, recipe_id=c.recipe_id, user_id=c.user_id,
        username=(names.get(c.user_id) or {}).get("username"),
        text=c.text, created_at=c.created_at, updated_at=c.updated_at,
    )


# ---------- resumo ----------
@router.get("/recipes/{recipe_id}/interactions", response_model=InteractionSummary)
def interactions_summary(
    recipe_id: int, db: Session = Depends(get_db), viewer: AuthUser | None = Depends(get_optional_user)
):
    """Tudo o que o ecrã de detalhe precisa numa só chamada (não depende de outros serviços)."""
    c = counters(db, recipe_id)
    my_like = None
    if viewer is not None:
        my_like = db.scalar(select(Like.id).where(Like.recipe_id == recipe_id, Like.user_id == viewer.id)) is not None
    return InteractionSummary(
        like_count=c["like_count"], comment_count=c["comment_count"],
        rating=rating_summary(db, recipe_id, viewer.id if viewer else None), my_like=my_like,
    )


# ---------- comentários ----------
@router.get("/recipes/{recipe_id}/comments", response_model=list[CommentOut])
def list_comments(
    recipe_id: int,
    response: Response,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    base = select(Comment).where(Comment.recipe_id == recipe_id)
    response.headers["X-Total-Count"] = str(db.scalar(select(func.count()).select_from(base.subquery())) or 0)
    comments = list(db.scalars(base.order_by(Comment.created_at.desc(), Comment.id.desc()).limit(limit).offset(offset)))
    names = clients.users_map({c.user_id for c in comments})
    return [_comment_out(c, names) for c in comments]


@router.post("/recipes/{recipe_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    recipe_id: int, data: CommentIn, background: BackgroundTasks,
    user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db),
):
    recipe = ensure_recipe(recipe_id)
    comment = Comment(recipe_id=recipe_id, user_id=user.id, text=data.text)
    db.add(comment)
    db.commit()
    _sync(background, db, recipe_id)
    background.add_task(clients.emit_event, "comment", user.id, recipe_id, recipe["author_id"], recipe["author_id"])
    return _comment_out(comment, {user.id: {"username": user.username}})


def _own_comment(db: Session, comment_id: int, user: AuthUser) -> Comment:
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comentário não encontrado.")
    if comment.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Só o autor pode alterar este comentário.")
    return comment


@router.patch("/comments/{comment_id}", response_model=CommentOut)
def edit_comment(
    comment_id: int, data: CommentIn, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    comment = _own_comment(db, comment_id, user)
    comment.text = data.text
    comment.updated_at = utcnow()
    db.commit()
    return _comment_out(comment, {user.id: {"username": user.username}})


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: int, background: BackgroundTasks,
    user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db),
):
    comment = _own_comment(db, comment_id, user)
    recipe_id = comment.recipe_id
    db.delete(comment)
    db.commit()
    _sync(background, db, recipe_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- likes ----------
@router.post("/recipes/{recipe_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def like(
    recipe_id: int, background: BackgroundTasks,
    user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db),
):
    recipe = ensure_recipe(recipe_id)
    db.add(Like(recipe_id=recipe_id, user_id=user.id))
    try:
        db.commit()
    except IntegrityError:  # unique(recipe_id, user_id): também protege pedidos simultâneos
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já gostaste desta receita.")
    _sync(background, db, recipe_id)
    background.add_task(clients.emit_event, "like", user.id, recipe_id, recipe["author_id"], recipe["author_id"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/recipes/{recipe_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def unlike(
    recipe_id: int, background: BackgroundTasks,
    user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db),
):
    row = db.scalar(select(Like).where(Like.recipe_id == recipe_id, Like.user_id == user.id))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ainda não gostaste desta receita.")
    db.delete(row)
    db.commit()
    _sync(background, db, recipe_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- avaliações ----------
@router.post("/recipes/{recipe_id}/ratings", response_model=RatingSummary)
def rate(
    recipe_id: int, data: RatingIn, response: Response, background: BackgroundTasks,
    user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db),
):
    """Uma avaliação por utilizador e receita: 201 ao criar, 200 ao atualizar a existente."""
    recipe = ensure_recipe(recipe_id)

    def existing():
        return db.scalar(select(Rating).where(Rating.recipe_id == recipe_id, Rating.user_id == user.id))

    row = existing()
    created = row is None
    if created:
        db.add(Rating(recipe_id=recipe_id, user_id=user.id, score=data.score))
        try:
            db.commit()
        except IntegrityError:  # corrida: outra avaliação do mesmo utilizador entrou entretanto
            db.rollback()
            created, row = False, existing()
    if not created:
        row.score = data.score
        row.updated_at = utcnow()
        db.commit()
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    _sync(background, db, recipe_id)
    background.add_task(clients.emit_event, "rating", user.id, recipe_id, recipe["author_id"], recipe["author_id"])
    return rating_summary(db, recipe_id, user.id)


@router.get("/recipes/{recipe_id}/ratings", response_model=RatingSummary)
def read_ratings(
    recipe_id: int, db: Session = Depends(get_db), viewer: AuthUser | None = Depends(get_optional_user)
):
    return rating_summary(db, recipe_id, viewer.id if viewer else None)
