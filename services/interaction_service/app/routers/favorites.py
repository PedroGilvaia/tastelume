from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import AuthUser, get_current_user
from ..database import get_db
from ..models import FavoriteCollection, FavoriteCollectionRecipe
from ..schemas import CollectionIn, CollectionOut
from .interactions import ensure_recipe

router = APIRouter(prefix="/favorite-collections", tags=["favorites"])


def _out(db: Session, col: FavoriteCollection) -> CollectionOut:
    ids = list(db.scalars(
        select(FavoriteCollectionRecipe.recipe_id)
        .where(FavoriteCollectionRecipe.collection_id == col.id)
        .order_by(FavoriteCollectionRecipe.added_at.desc(), FavoriteCollectionRecipe.recipe_id.desc())
    ))
    return CollectionOut(id=col.id, name=col.name, created_at=col.created_at, recipe_count=len(ids), recipe_ids=ids)


def _own(db: Session, collection_id: int, user: AuthUser) -> FavoriteCollection:
    col = db.get(FavoriteCollection, collection_id)
    if col is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lista não encontrada.")
    if col.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Esta lista pertence a outro utilizador.")
    return col


@router.get("", response_model=list[CollectionOut])
def list_collections(user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    cols = db.scalars(
        select(FavoriteCollection).where(FavoriteCollection.user_id == user.id).order_by(FavoriteCollection.id)
    )
    return [_out(db, c) for c in cols]


@router.post("", response_model=CollectionOut, status_code=status.HTTP_201_CREATED)
def create_collection(data: CollectionIn, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    taken = db.scalar(select(FavoriteCollection.id).where(
        FavoriteCollection.user_id == user.id, func.lower(FavoriteCollection.name) == data.name.lower()))
    if taken:
        raise HTTPException(status.HTTP_409_CONFLICT, "Já tens uma lista com este nome.")
    col = FavoriteCollection(user_id=user.id, name=data.name)
    db.add(col)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já tens uma lista com este nome.")
    return _out(db, col)


@router.get("/{collection_id}", response_model=CollectionOut)
def read_collection(collection_id: int, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return _out(db, _own(db, collection_id, user))


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(collection_id: int, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    col = _own(db, collection_id, user)
    db.execute(delete(FavoriteCollectionRecipe).where(FavoriteCollectionRecipe.collection_id == col.id))
    db.delete(col)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{collection_id}/recipes/{recipe_id}", response_model=CollectionOut, status_code=status.HTTP_201_CREATED)
def add_recipe(collection_id: int, recipe_id: int, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    col = _own(db, collection_id, user)
    ensure_recipe(recipe_id)
    db.add(FavoriteCollectionRecipe(collection_id=col.id, recipe_id=recipe_id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A receita já está nesta lista.")
    return _out(db, col)


@router.delete("/{collection_id}/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_recipe(collection_id: int, recipe_id: int, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    col = _own(db, collection_id, user)
    row = db.get(FavoriteCollectionRecipe, (col.id, recipe_id))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "A receita não está nesta lista.")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
