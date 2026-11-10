from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from .. import clients
from ..auth import require_internal
from ..database import get_db
from ..models import Comment, FavoriteCollectionRecipe, Like, Rating, RecipeShare
from .interactions import counters

router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[Depends(require_internal)])


@router.delete("/recipes/{recipe_id}/data", status_code=status.HTTP_204_NO_CONTENT)
def purge_recipe_data(recipe_id: int, db: Session = Depends(get_db)):
    """Chamado pelo Recipe Service quando uma receita é apagada (idempotente)."""
    for model in (Comment, Like, Rating, FavoriteCollectionRecipe, RecipeShare):
        db.execute(delete(model).where(model.recipe_id == recipe_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/recipes/{recipe_id}/resync-counters", status_code=status.HTTP_204_NO_CONTENT)
def resync_counters(recipe_id: int, db: Session = Depends(get_db)):
    """Reenvia os totais ao Recipe Service (reparação manual se um envio tiver falhado)."""
    clients.push_counters(recipe_id, counters(db, recipe_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
