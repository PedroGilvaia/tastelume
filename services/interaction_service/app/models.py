from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ts(**kw):
    return mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, **kw)


# recipe_id e user_id são referências lógicas a outros serviços (sem FK entre bases de dados).
class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (Index("ix_comments_recipe_created", "recipe_id", "created_at"),)


class Rating(Base):
    __tablename__ = "ratings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (
        UniqueConstraint("recipe_id", "user_id", name="uq_rating_recipe_user"),
        CheckConstraint("score BETWEEN 1 AND 5", name="ck_rating_score"),
    )


class Like(Base):
    __tablename__ = "likes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = _ts()
    __table_args__ = (UniqueConstraint("recipe_id", "user_id", name="uq_like_recipe_user"),)


class FavoriteCollection(Base):
    __tablename__ = "favorite_collections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = _ts()
    __table_args__ = (
        Index("uq_collection_user_name", "user_id", func.lower(name), unique=True),
    )


class FavoriteCollectionRecipe(Base):
    __tablename__ = "favorite_collection_recipes"
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("favorite_collections.id", ondelete="CASCADE"), primary_key=True
    )
    recipe_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    added_at: Mapped[datetime] = _ts()
    __table_args__ = (Index("ix_fcr_recipe_id", "recipe_id"),)


class RecipeShare(Base):
    __tablename__ = "recipe_shares"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sender_id: Mapped[int] = mapped_column(Integer, nullable=False)
    recipient_id: Mapped[int] = mapped_column(Integer, nullable=False)
    recipe_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = _ts()
    __table_args__ = (
        Index("ix_shares_recipient", "recipient_id", "created_at"),
        Index("ix_shares_recipe", "recipe_id"),
    )


class DirectMessage(Base):
    __tablename__ = "direct_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sender_id: Mapped[int] = mapped_column(Integer, nullable=False)
    recipient_id: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _ts()
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("sender_id <> recipient_id", name="ck_message_not_self"),
        Index("ix_messages_pair", "sender_id", "recipient_id"),
        Index("ix_messages_recipient_read", "recipient_id", "read_at"),
    )
