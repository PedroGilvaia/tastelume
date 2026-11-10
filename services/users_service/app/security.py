from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], password_hash.encode("ascii"))
    except ValueError:
        return False


# Hash "falso" para igualar o tempo de resposta quando o utilizador não existe.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def burn_password_check(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


def create_access_token(user_id: int, username: str) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    expires = timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + expires,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(expires.total_seconds())


def decode_access_token(token: str) -> dict:
    """Levanta jwt.PyJWTError se o token for inválido ou tiver expirado."""
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub"]},
    )
