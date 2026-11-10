from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .routers import auth, internal, users

app = FastAPI(
    title="Tastelume — Users Service",
    version="0.1.0",
    description="Autenticação, perfis, interesses e seguidores.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(internal.router)


@app.get("/health", tags=["health"])
def health(response: Response, db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        response.status_code = 503
        return {"status": "unavailable", "service": "users"}
    return {"status": "ok", "service": "users"}
