from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .routers import events, notifications, stats

app = FastAPI(
    title="Tastelume — Activity Service",
    version="0.1.0",
    description="Eventos, notificações e estatísticas de atividade.",
)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"],
                   allow_headers=["*"], expose_headers=["X-Total-Count", "X-Unread-Count"])
for r in (events.router, notifications.router, stats.router):
    app.include_router(r)


@app.get("/health", tags=["health"])
def health(response: Response, db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        response.status_code = 503
        return {"status": "unavailable", "service": "activity"}
    return {"status": "ok", "service": "activity"}
