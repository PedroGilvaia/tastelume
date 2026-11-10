"""Esqueleto da Fase 1: health check e ligação à base de dados. Endpoints de negócio: fases seguintes."""
import os

from fastapi import FastAPI, Response
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

app = FastAPI(title="Tastelume — Activity Service", version="0.0.1")


@app.get("/health", tags=["health"])
def health(response: Response):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        response.status_code = 503
        return {"status": "unavailable", "service": "activity"}
    return {"status": "ok", "service": "activity"}
