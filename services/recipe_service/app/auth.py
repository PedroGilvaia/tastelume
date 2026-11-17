"""Validação local do JWT emitido pelo Users Service (segredo partilhado)."""
import hmac
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthUser:
    id: int
    username: str


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


def _parse(creds: HTTPAuthorizationCredentials | None) -> AuthUser | None:
    if creds is None:
        return None
    try:
        payload = jwt.decode(
            creds.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
        return AuthUser(id=int(payload["sub"]), username=str(payload.get("username", "")))
    except (jwt.PyJWTError, ValueError, KeyError):
        raise _unauthorized("Sessão inválida ou expirada.")


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> AuthUser:
    user = _parse(creds)
    if user is None:
        raise _unauthorized("Autenticação necessária.")
    return user


def get_optional_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> AuthUser | None:
    return _parse(creds)


def require_internal(x_internal_token: str | None = Header(default=None)) -> None:
    if x_internal_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token interno em falta.")
    if not hmac.compare_digest(x_internal_token, settings.internal_token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token interno inválido.")
