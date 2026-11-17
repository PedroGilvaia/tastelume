import os


class Settings:
    """Configuração lida das variáveis de ambiente."""

    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./activity_dev.db")
        self.jwt_secret = os.getenv("JWT_SECRET", "dev-only-change-me-dev-only-change-me")
        self.jwt_algorithm = "HS256"
        self.internal_token = os.getenv("INTERNAL_SERVICE_TOKEN", "dev-internal-token")
        self.users_service_url = os.getenv("USERS_SERVICE_URL", "").rstrip("/")
        self.recipe_service_url = os.getenv("RECIPE_SERVICE_URL", "").rstrip("/")
        self.http_timeout = float(os.getenv("HTTP_TIMEOUT_SECONDS", "2"))
        self.breaker_cooldown = float(os.getenv("BREAKER_COOLDOWN_SECONDS", "15"))
        # Máximo de seguidores notificados por receita publicada (evita rajadas enormes).
        self.max_fanout = int(os.getenv("MAX_FANOUT", "5000"))
        self.cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]


settings = Settings()
