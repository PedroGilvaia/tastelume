from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

EventType = Literal["follow", "like", "comment", "rating", "share", "message", "view", "recipe_created"]


class EventIn(BaseModel):
    """Payload de POST /internal/events (ver docs/architecture.md)."""

    event_type: EventType
    actor_id: int | None = Field(default=None, ge=1)
    recipe_id: int | None = Field(default=None, ge=1)
    recipe_owner_id: int | None = Field(default=None, ge=1)
    target_user_id: int | None = Field(default=None, ge=1)


class EventAck(BaseModel):
    event_id: int
    notifications_created: int


class NotificationOut(BaseModel):
    id: int
    type: EventType
    actor_id: int | None
    actor_username: str | None
    recipe_id: int | None
    recipe_title: str | None
    text: str  # frase pronta a mostrar (pt-PT), com alternativa se faltarem nomes
    read: bool
    created_at: datetime


class UnreadCount(BaseModel):
    unread: int


class StatsTotals(BaseModel):
    views: int
    likes: int
    comments: int
    ratings: int
    shares: int
    new_followers: int
    recipes_published: int


class StatsOut(BaseModel):
    period_days: int
    totals: StatsTotals


class DayPoint(BaseModel):
    date: date
    views: int
    likes: int
    comments: int
    ratings: int
    shares: int


class TopRecipe(BaseModel):
    recipe_id: int
    title: str | None
    views: int
    likes: int
    comments: int
    ratings: int
    shares: int
