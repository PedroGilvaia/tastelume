from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import LoginIn, RegisterIn, TokenOut, UserPrivate
from ..security import burn_password_check, create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    """Cria uma conta. 409 se o username ou o email já existirem."""
    taken = db.scalar(
        select(User).where(
            or_(func.lower(User.username) == data.username.lower(), User.email == data.email)
        )
    )
    if taken is not None:
        field = "username" if taken.username.lower() == data.username.lower() else "email"
        raise HTTPException(status.HTTP_409_CONFLICT, f"Já existe uma conta com este {field}.")

    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        description="",
        interests=[],
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # corrida entre dois registos simultâneos
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma conta com estes dados.")
    return user


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    """Autentica com username ou email. Mensagem de erro igual para ambos os casos de falha."""
    ident = data.identifier.strip()
    user = db.scalar(
        select(User).where(
            or_(func.lower(User.username) == ident.lower(), User.email == ident.lower())
        )
    )
    if user is None:
        burn_password_check(data.password)
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Credenciais inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, expires_in = create_access_token(user.id, user.username)
    return TokenOut(access_token=token, expires_in=expires_in)
