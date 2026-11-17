"""Endpoints para outros serviços (X-Internal-Token)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_internal
from ..database import get_db
from ..models import Recipe
from ..schemas import CountersIn, InternalRecipe

router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[Depends(require_internal)])


@router.get("/recipes", response_model=list[InternalRecipe])
def recipes_by_ids(ids: str = Query(description="ids separados por vírgula (máx. 100)"), db: Session = Depends(get_db)):
    try:
        wanted = {int(i) for i in ids.split(",") if i.strip()}
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Lista de ids inválida.")
    if not wanted or len(wanted) > 100:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Indica entre 1 e 100 ids.")
    return list(db.scalars(select(Recipe).where(Recipe.id.in_(wanted))).unique())


@router.get("/recipes/{recipe_id}", response_model=InternalRecipe)
def recipe_by_id(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada.")
    return recipe


@router.put("/recipes/{recipe_id}/counters", status_code=status.HTTP_204_NO_CONTENT)
def set_counters(recipe_id: int, data: CountersIn, db: Session = Depends(get_db)):
    """O Interaction Service envia totais absolutos (idempotente: repetir não corrompe contagens)."""
    recipe = db.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada.")
    changes = data.model_dump(exclude_unset=True)
    for field in ("like_count", "comment_count", "rating_count"):
        if changes.get(field) is not None:
            setattr(recipe, field, changes[field])
    if "rating_avg" in changes:
        recipe.rating_avg = changes["rating_avg"]
    if recipe.rating_count == 0:
        recipe.rating_avg = None
    db.commit()
