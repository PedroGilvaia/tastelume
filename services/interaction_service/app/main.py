from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .clients import Unavailable
from .config import settings
from .database import get_db
from .routers import favorites, interactions, internal, social

app = FastAPI(
    title="Tastelume — Interaction Service",
    version="0.1.0",
    description="Comentários, likes, avaliações, favoritos, partilhas e mensagens.",
)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"],
                   allow_headers=["*"], expose_headers=["X-Total-Count"])
for r in (interactions.router, favorites.router, social.router, internal.router):
    app.include_router(r)


@app.exception_handler(Unavailable)
async def _unavailable(_: Request, exc: Unavailable):
    return JSONResponse(
        status_code=503,
        content={"detail": "Serviço temporariamente indisponível. Tenta novamente dentro de instantes."},
        headers={"Retry-After": "15"},
    )


@app.get("/health", tags=["health"])
def health(response: Response, db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        response.status_code = 503
        return {"status": "unavailable", "service": "interaction"}
    return {"status": "ok", "service": "interaction"}
