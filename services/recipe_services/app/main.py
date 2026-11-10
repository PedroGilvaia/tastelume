from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .categories import ensure_categories
from .config import settings
from .database import SessionLocal, get_db
from .routers import internal, recipes


@asynccontextmanager
async def lifespan(_: FastAPI):
    with SessionLocal() as db:
        ensure_categories(db)  # idempotente: só insere categorias em falta
    yield


app = FastAPI(
    title="Tastelume — Recipe Service",
    version="0.1.0",
    description="Receitas, categorias, pesquisa, imagens e visualizações.",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"],
                   expose_headers=["X-Total-Count"])
app.include_router(recipes.router)
app.include_router(internal.router)


@app.get("/health", tags=["health"])
def health(response: Response, db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        response.status_code = 503
        return {"status": "unavailable", "service": "recipe"}
    return {"status": "ok", "service": "recipe"}
