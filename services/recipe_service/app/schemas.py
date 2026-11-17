from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Difficulty = Literal["facil", "media", "dificil"]


class IngredientIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    quantity: float | None = Field(default=None, ge=0, le=100000)
    unit: str | None = Field(default=None, max_length=20)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("O nome do ingrediente não pode estar vazio.")
        return v

    @field_validator("unit")
    @classmethod
    def _unit(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v else None


def _clean_steps(v: list[str]) -> list[str]:
    cleaned = [s.strip() for s in v]
    if any(not s or len(s) > 1000 for s in cleaned):
        raise ValueError("Cada passo deve ter entre 1 e 1000 caracteres.")
    return cleaned


def _clean_tags(v: list[str]) -> list[str]:
    out: list[str] = []
    for tag in v:
        tag = tag.strip().lower()
        if not tag or len(tag) > 30:
            raise ValueError("Cada etiqueta deve ter entre 1 e 30 caracteres.")
        if tag not in out:
            out.append(tag)
    return out


class RecipeIn(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    category: str = Field(description="slug da categoria (ver GET /categories)")
    ingredients: list[IngredientIn] = Field(min_length=1, max_length=60)
    preparation_steps: list[str] = Field(min_length=1, max_length=60)
    preparation_time: int = Field(ge=1, le=1440, description="minutos")
    servings: int = Field(ge=1, le=100)
    difficulty: Difficulty
    tags: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("preparation_steps")
    @classmethod
    def _steps(cls, v: list[str]) -> list[str]:
        return _clean_steps(v)

    @field_validator("tags")
    @classmethod
    def _tags(cls, v: list[str]) -> list[str]:
        return _clean_tags(v)

    @field_validator("title", "description")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class RecipeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = None
    ingredients: list[IngredientIn] | None = Field(default=None, min_length=1, max_length=60)
    preparation_steps: list[str] | None = Field(default=None, min_length=1, max_length=60)
    preparation_time: int | None = Field(default=None, ge=1, le=1440)
    servings: int | None = Field(default=None, ge=1, le=100)
    difficulty: Difficulty | None = None
    tags: list[str] | None = Field(default=None, max_length=10)

    @field_validator("preparation_steps")
    @classmethod
    def _steps(cls, v):
        return None if v is None else _clean_steps(v)

    @field_validator("tags")
    @classmethod
    def _tags(cls, v):
        return None if v is None else _clean_tags(v)

    @field_validator("title", "description")
    @classmethod
    def _strip(cls, v):
        return None if v is None else v.strip()


class CategoryOut(BaseModel):
    slug: str
    name: str


class IngredientOut(BaseModel):
    name: str
    quantity: float | None = None
    unit: str | None = None


class StepOut(BaseModel):
    order: int
    text: str


class RecipeSummary(BaseModel):
    id: int
    title: str
    author_id: int
    author_username: str | None  # None se o Users Service estiver indisponível
    category: CategoryOut
    difficulty: str
    preparation_time: int
    image_url: str | None
    rating_avg: float | None  # None = não classificada
    rating_count: int
    view_count: int
    like_count: int
    comment_count: int
    created_at: datetime


class RecipeDetail(RecipeSummary):
    description: str
    ingredients: list[IngredientOut]
    preparation_steps: list[StepOut]
    tags: list[str]
    servings: int
    updated_at: datetime


class ViewResult(BaseModel):
    counted: bool
    view_count: int


class CountersIn(BaseModel):
    """Totais absolutos (idempotentes) calculados pelo Interaction Service."""

    like_count: int | None = Field(default=None, ge=0)
    comment_count: int | None = Field(default=None, ge=0)
    rating_count: int | None = Field(default=None, ge=0)
    rating_avg: float | None = Field(default=None, ge=1, le=5)


class InternalRecipe(BaseModel):
    id: int
    author_id: int
    title: str
