import hmac

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User
from .security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"}
    )


def _user_from_credentials(creds: HTTPAuthorizationCredentials | None, db: Session) -> User | None:
    if creds is None:
        return None
    try:
        payload = decode_access_token(creds.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise _unauthorized("Sessão inválida ou expirada.")
    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized("Sessão inválida ou expirada.")
    return user


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    user = _user_from_credentials(creds, db)
    if user is None:
        raise _unauthorized("Autenticação necessária.")
    return user


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    return _user_from_credentials(creds, db)


def require_internal(x_internal_token: str | None = Header(default=None)) -> None:
    """Protege endpoints /internal/*: apenas outros serviços com o token partilhado."""
    if x_internal_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token interno em falta.")
    if not hmac.compare_digest(x_internal_token, settings.internal_token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token interno inválido.")
