import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")


class RegisterIn(BaseModel):
    username: str
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("username")
    @classmethod
    def _username(cls, v: str) -> str:
        v = v.strip()
        if not USERNAME_RE.match(v):
            raise ValueError("O username deve ter 3-30 caracteres (letras, números ou _).")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:  # limite do bcrypt
            raise ValueError("A password não pode exceder 72 bytes.")
        return v


class LoginIn(BaseModel):
    identifier: str = Field(min_length=1, description="Username ou email")
    password: str = Field(min_length=1, max_length=200)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=500)
    interests: list[str] | None = Field(default=None, max_length=20)

    @field_validator("interests")
    @classmethod
    def _interests(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        cleaned: list[str] = []
        for item in v:
            item = item.strip()
            if not item or len(item) > 40:
                raise ValueError("Cada interesse deve ter entre 1 e 40 caracteres.")
            if item.lower() not in (c.lower() for c in cleaned):
                cleaned.append(item)
        return cleaned


class UserPrivate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: str
    description: str
    interests: list[str]
    created_at: datetime


class UserPublic(BaseModel):
    id: int
    username: str
    description: str
    interests: list[str]
    created_at: datetime
    followers_count: int
    following_count: int
    is_following: bool | None = None  # None para visitantes


class InternalUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    interests: list[str]
