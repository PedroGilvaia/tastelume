import os


class Settings:
    """Configuração lida das variáveis de ambiente (nunca hardcoded em produção)."""

    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./users_dev.db")
        self.jwt_secret = os.getenv("JWT_SECRET", "dev-only-change-me")
        self.jwt_algorithm = "HS256"
        self.jwt_expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
        self.internal_token = os.getenv("INTERNAL_SERVICE_TOKEN", "dev-internal-token")
        # Vazio = não enviar eventos (útil em testes).
        self.activity_service_url = os.getenv("ACTIVITY_SERVICE_URL", "").rstrip("/")
        self.activity_timeout = float(os.getenv("ACTIVITY_TIMEOUT_SECONDS", "2"))
        self.cors_origins = [
            o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
        ]


settings = Settings()
