from datetime import datetime, timezone

from sqlalchemy import (
    DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Referência lógica ao Users Service (sem FK entre bases de dados).
    author_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    ingredients: Mapped[list] = mapped_column(JSON, nullable=False)
    # Nomes dos ingredientes em minúsculas, apenas para pesquisa.
    ingredients_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    preparation_steps: Mapped[list] = mapped_column(JSON, nullable=False)  # a ordem é a da lista
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    preparation_time: Mapped[int] = mapped_column(Integer, nullable=False)  # minutos
    servings: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False)
    image_path: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # Contadores desnormalizados (ver docs/architecture.md).
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating_avg: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    category: Mapped[Category] = relationship(lazy="joined")

    __table_args__ = (
        Index("ix_recipes_author_id", "author_id"),
        Index("ix_recipes_category_id", "category_id"),
        Index("ix_recipes_created_at", "created_at"),
    )


class ViewLog(Base):
    """Última visualização contada por (receita, visitante) — evita contagens repetidas."""

    __tablename__ = "view_log"

    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True)
    viewer_key: Mapped[str] = mapped_column(String(80), primary_key=True)
    last_counted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
