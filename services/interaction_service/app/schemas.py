from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _text(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("O texto não pode estar vazio.")
    return v


class CommentIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)

    @field_validator("text")
    @classmethod
    def _clean(cls, v: str) -> str:
        return _text(v)


class CommentOut(BaseModel):
    id: int
    recipe_id: int
    user_id: int
    username: str | None
    text: str
    created_at: datetime
    updated_at: datetime | None


class RatingIn(BaseModel):
    score: int = Field(ge=1, le=5)


class RatingSummary(BaseModel):
    average: float | None  # None = não classificada
    count: int
    distribution: dict[str, int]  # "1".."5"
    my_score: int | None = None


class InteractionSummary(BaseModel):
    like_count: int
    comment_count: int
    rating: RatingSummary
    my_like: bool | None = None  # None para visitantes


class CollectionIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)

    @field_validator("name")
    @classmethod
    def _clean(cls, v: str) -> str:
        return _text(v)


class CollectionOut(BaseModel):
    id: int
    name: str
    created_at: datetime
    recipe_count: int
    recipe_ids: list[int]  # mais recentes primeiro


class ShareIn(BaseModel):
    recipient_username: str = Field(min_length=1, max_length=30)


class ShareOut(BaseModel):
    id: int
    sender_id: int
    sender_username: str | None
    recipient_id: int
    recipe_id: int
    recipe_title: str | None
    created_at: datetime


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)

    @field_validator("text")
    @classmethod
    def _clean(cls, v: str) -> str:
        return _text(v)


class MessageOut(BaseModel):
    id: int
    sender_id: int
    recipient_id: int
    text: str
    created_at: datetime
    read_at: datetime | None


class ConversationOut(BaseModel):
    user_id: int
    username: str | None
    last_message: MessageOut
    unread_count: int
