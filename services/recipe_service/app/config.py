import os


class Settings:
    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./recipe_dev.db")
        self.jwt_secret = os.getenv("JWT_SECRET", "dev-only-change-me-dev-only-change-me")
        self.jwt_algorithm = "HS256"
        self.internal_token = os.getenv("INTERNAL_SERVICE_TOKEN", "dev-internal-token")
        self.users_service_url = os.getenv("USERS_SERVICE_URL", "").rstrip("/")
        self.interaction_service_url = os.getenv("INTERACTION_SERVICE_URL", "").rstrip("/")
        self.activity_service_url = os.getenv("ACTIVITY_SERVICE_URL", "").rstrip("/")
        self.http_timeout = float(os.getenv("HTTP_TIMEOUT_SECONDS", "2"))
        self.image_dir = os.getenv("IMAGE_DIR", "./data/images")
        self.max_image_bytes = int(os.getenv("MAX_IMAGE_BYTES", str(5 * 1024 * 1024)))
        # Janela em que várias aberturas do mesmo detalhe contam como uma só visualização.
        self.view_window_minutes = int(os.getenv("VIEW_WINDOW_MINUTES", "30"))
        self.cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]


settings = Settings()
