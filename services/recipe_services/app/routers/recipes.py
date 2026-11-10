import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, Query, Request, Response,
    UploadFile, status,
)
from fastapi.responses import FileResponse
from sqlalchemy import case, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import AuthUser, get_current_user, get_optional_user
from ..clients import emit_event, purge_interactions, users_client
from ..config import settings
from ..database import get_db
from ..images import MEDIA_TYPES, delete_image, detect_extension, resolve_image, save_image
from ..models import Category, Recipe, ViewLog, utcnow
from ..schemas import (
    CategoryOut, IngredientOut, RecipeDetail, RecipeIn, RecipeSummary, RecipeUpdate, StepOut,
    ViewResult,
)

router = APIRouter(tags=["recipes"])

SortKey = Literal["recent", "rating", "views", "popular"]


# ---------- helpers ----------
def _norm(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn"
    ).strip()


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def popularity_expr():
    """Popularidade = visualizações + 3·likes + 4·comentários + 2·(nº avaliações × média).

    Definição única, usada por `sort=popular`, pelo feed de visitantes e pelas receitas relacionadas.
    """
    return (
        Recipe.view_count
        + 3 * Recipe.like_count
        + 4 * Recipe.comment_count
        + 2 * Recipe.rating_count * func.coalesce(Recipe.rating_avg, 0)
    )


def _order_by(sort: SortKey) -> list:
    if sort == "recent":
        return [Recipe.created_at.desc(), Recipe.id.desc()]
    if sort == "rating":
        return [
            case((Recipe.rating_avg.is_(None), 1), else_=0),  # não classificadas no fim
            Recipe.rating_avg.desc(),
            Recipe.rating_count.desc(),
            Recipe.id.desc(),
        ]
    if sort == "views":
        return [Recipe.view_count.desc(), Recipe.id.desc()]
    return [popularity_expr().desc(), Recipe.created_at.desc(), Recipe.id.desc()]


def _like_pattern(text: str) -> str:
    escaped = text.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _summary_fields(r: Recipe, authors: dict[int, dict]) -> dict:
    return dict(
        id=r.id,
        title=r.title,
        author_id=r.author_id,
        author_username=(authors.get(r.author_id) or {}).get("username"),
        category=CategoryOut(slug=r.category.slug, name=r.category.name),
        difficulty=r.difficulty,
        preparation_time=r.preparation_time,
        image_url=f"/images/{r.image_path}" if r.image_path else None,
        rating_avg=round(r.rating_avg, 2) if r.rating_avg is not None and r.rating_count else None,
        rating_count=r.rating_count,
        view_count=r.view_count,
        like_count=r.like_count,
        comment_count=r.comment_count,
        created_at=r.created_at,
    )


def to_summaries(recipes: list[Recipe]) -> list[RecipeSummary]:
    authors = users_client.get_users({r.author_id for r in recipes})
    return [RecipeSummary(**_summary_fields(r, authors)) for r in recipes]


def to_detail(r: Recipe) -> RecipeDetail:
    authors = users_client.get_users({r.author_id})
    return RecipeDetail(
        **_summary_fields(r, authors),
        description=r.description,
        ingredients=[IngredientOut(**i) for i in r.ingredients],
        preparation_steps=[StepOut(order=n, text=t) for n, t in enumerate(r.preparation_steps, 1)],
        tags=r.tags,
        servings=r.servings,
        updated_at=r.updated_at,
    )


def _get_recipe_or_404(db: Session, recipe_id: int) -> Recipe:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada.")
    return recipe


def _get_own_recipe(db: Session, recipe_id: int, user: AuthUser) -> Recipe:
    recipe = _get_recipe_or_404(db, recipe_id)
    if recipe.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Só o autor pode alterar esta receita.")
    return recipe


def _category_or_422(db: Session, slug: str) -> Category:
    category = db.scalar(select(Category).where(Category.slug == slug))
    if category is None:
        raise HTTPException(422, "Categoria inexistente.")
    return category


def _ingredients_text(ingredients: list[dict]) -> str:
    return "\n".join(i["name"].lower() for i in ingredients)


# ---------- categorias ----------
@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return list(db.scalars(select(Category).order_by(Category.sort_order, Category.id)))


# ---------- listagem / pesquisa ----------
@router.get("/recipes", response_model=list[RecipeSummary])
def list_recipes(
    response: Response,
    q: str = Query(default="", max_length=100, description="Texto: título, descrição ou ingredientes"),
    ingredient: str = Query(default="", max_length=80),
    category: str | None = Query(default=None, max_length=40, description="slug"),
    author_id: int | None = None,
    ids: str | None = Query(default=None, max_length=400, description="ids separados por vírgula (máx. 50)"),
    sort: SortKey = "popular",
    personalized: bool = Query(default=False, description="Prioriza as categorias de interesse (requer sessão)"),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    viewer: AuthUser | None = Depends(get_optional_user),
):
    stmt = select(Recipe)
    if q.strip():
        pat = _like_pattern(q.strip())
        stmt = stmt.where(
            or_(
                func.lower(Recipe.title).like(pat, escape="\\"),
                func.lower(Recipe.description).like(pat, escape="\\"),
                Recipe.ingredients_text.like(pat, escape="\\"),
            )
        )
    if ingredient.strip():
        stmt = stmt.where(Recipe.ingredients_text.like(_like_pattern(ingredient.strip()), escape="\\"))
    if category:
        stmt = stmt.join(Category, Recipe.category_id == Category.id).where(Category.slug == category)
    if author_id is not None:
        stmt = stmt.where(Recipe.author_id == author_id)
    if ids is not None:
        try:
            wanted = {int(i) for i in ids.split(",") if i.strip()}
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Lista de ids inválida.")
        if not wanted or len(wanted) > 50:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Indica entre 1 e 50 ids.")
        stmt = stmt.where(Recipe.id.in_(wanted))

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    response.headers["X-Total-Count"] = str(total)

    order = _order_by(sort)
    if personalized and viewer is not None:
        interests = users_client.get_users({viewer.id}).get(viewer.id, {}).get("interests", [])
        wanted = {_norm(i) for i in interests}
        if wanted:
            favored = [c.id for c in db.scalars(select(Category)) if {_norm(c.slug), _norm(c.name)} & wanted]
            if favored:
                order = [case((Recipe.category_id.in_(favored), 0), else_=1), *order]

    recipes = list(db.scalars(stmt.order_by(*order).limit(limit).offset(offset)).unique())
    return to_summaries(recipes)


@router.get("/users/{user_id}/recipes", response_model=list[RecipeSummary])
def user_recipes(
    user_id: int,
    response: Response,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Recipe).where(Recipe.author_id == user_id)
    response.headers["X-Total-Count"] = str(
        db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    )
    recipes = list(db.scalars(stmt.order_by(*_order_by("recent")).limit(limit).offset(offset)).unique())
    return to_summaries(recipes)


# ---------- CRUD ----------
@router.post("/recipes", response_model=RecipeDetail, status_code=status.HTTP_201_CREATED)
def create_recipe(
    data: RecipeIn,
    background: BackgroundTasks,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = _category_or_422(db, data.category)
    ingredients = [i.model_dump() for i in data.ingredients]
    recipe = Recipe(
        author_id=user.id,
        title=data.title,
        description=data.description,
        ingredients=ingredients,
        ingredients_text=_ingredients_text(ingredients),
        preparation_steps=data.preparation_steps,
        category_id=category.id,
        tags=data.tags,
        preparation_time=data.preparation_time,
        servings=data.servings,
        difficulty=data.difficulty,
    )
    db.add(recipe)
    db.commit()
    background.add_task(emit_event, "recipe_created", user.id, recipe.id, user.id)
    return to_detail(recipe)


@router.get("/recipes/{recipe_id}", response_model=RecipeDetail)
def read_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Não conta visualizações: a app chama POST /recipes/{id}/view uma vez ao abrir o detalhe."""
    return to_detail(_get_recipe_or_404(db, recipe_id))


@router.patch("/recipes/{recipe_id}", response_model=RecipeDetail)
def update_recipe(
    recipe_id: int,
    data: RecipeUpdate,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = _get_own_recipe(db, recipe_id, user)
    changes = data.model_dump(exclude_unset=True)
    if "category" in changes:
        if changes["category"] is None:
            raise HTTPException(422, "Categoria inválida.")
        recipe.category = _category_or_422(db, changes.pop("category"))
    if "ingredients" in changes:
        changes.pop("ingredients")
        if data.ingredients is None:
            raise HTTPException(422, "Ingredientes inválidos.")
        ingredients = [i.model_dump() for i in data.ingredients]  # dump completo (inclui unit=None)
        recipe.ingredients = ingredients
        recipe.ingredients_text = _ingredients_text(ingredients)
    for field, value in changes.items():
        if value is None:
            raise HTTPException(422, f"Valor inválido para '{field}'.")
        setattr(recipe, field, value)
    recipe.updated_at = utcnow()
    db.commit()
    return to_detail(recipe)


@router.delete("/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(
    recipe_id: int,
    background: BackgroundTasks,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = _get_own_recipe(db, recipe_id, user)
    image = recipe.image_path
    db.execute(delete(ViewLog).where(ViewLog.recipe_id == recipe.id))
    db.delete(recipe)
    db.commit()
    delete_image(image)
    background.add_task(purge_interactions, recipe_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/recipes/{recipe_id}/related", response_model=list[RecipeSummary])
def related_recipes(recipe_id: int, db: Session = Depends(get_db)):
    recipe = _get_recipe_or_404(db, recipe_id)
    stmt = (
        select(Recipe)
        .where(Recipe.category_id == recipe.category_id, Recipe.id != recipe.id)
        .order_by(*_order_by("popular"))
        .limit(6)
    )
    return to_summaries(list(db.scalars(stmt).unique()))


# ---------- visualizações ----------
@router.post("/recipes/{recipe_id}/view", response_model=ViewResult)
def register_view(
    recipe_id: int,
    request: Request,
    background: BackgroundTasks,
    viewer: AuthUser | None = Depends(get_optional_user),
    x_client_id: str | None = Header(default=None, max_length=64),
    db: Session = Depends(get_db),
):
    """Regra: cada visitante (utilizador, ou X-Client-Id/IP se anónimo) conta no máximo 1 vez por
    receita em cada janela de VIEW_WINDOW_MINUTES (30 por omissão). O autor não conta as próprias."""
    recipe = _get_recipe_or_404(db, recipe_id)
    if viewer is not None and viewer.id == recipe.author_id:
        return ViewResult(counted=False, view_count=recipe.view_count)

    if viewer is not None:
        key = f"u:{viewer.id}"
    else:
        key = f"a:{(x_client_id or (request.client.host if request.client else 'unknown'))[:64]}"

    now = utcnow()
    window = timedelta(minutes=settings.view_window_minutes)
    log = db.get(ViewLog, (recipe.id, key))
    if log is not None and now - _as_utc(log.last_counted_at) < window:
        return ViewResult(counted=False, view_count=recipe.view_count)

    if log is None:
        db.add(ViewLog(recipe_id=recipe.id, viewer_key=key, last_counted_at=now))
    else:
        log.last_counted_at = now
    try:
        db.execute(update(Recipe).where(Recipe.id == recipe.id).values(view_count=Recipe.view_count + 1))
        db.commit()
    except IntegrityError:  # pedido simultâneo do mesmo visitante: já foi contado
        db.rollback()
        return ViewResult(counted=False, view_count=db.get(Recipe, recipe_id).view_count)

    background.add_task(emit_event, "view", viewer.id if viewer else None, recipe.id, recipe.author_id)
    db.refresh(recipe)
    return ViewResult(counted=True, view_count=recipe.view_count)


# ---------- imagens ----------
@router.post("/recipes/{recipe_id}/image", response_model=RecipeDetail)
def upload_image(
    recipe_id: int,
    file: UploadFile = File(...),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = _get_own_recipe(db, recipe_id, user)
    data = file.file.read(settings.max_image_bytes + 1)
    if len(data) > settings.max_image_bytes:
        raise HTTPException(
            413,
            f"A imagem excede o limite de {settings.max_image_bytes // (1024 * 1024)} MB.",
        )
    ext = detect_extension(data)
    if ext is None:
        raise HTTPException(415, "Formato inválido. Usa JPEG, PNG ou WebP.")
    old = recipe.image_path
    recipe.image_path = save_image(data, ext)
    recipe.updated_at = utcnow()
    db.commit()
    delete_image(old)
    return to_detail(recipe)


@router.get("/images/{filename}", include_in_schema=True)
def get_image(filename: str):
    path = resolve_image(filename)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Imagem não encontrada.")
    return FileResponse(
        path,
        media_type=MEDIA_TYPES[path.suffix.lstrip(".")],
        headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"},
    )
