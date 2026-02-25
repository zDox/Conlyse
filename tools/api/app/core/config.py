from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "replays"
    POSTGRES_USER: str = "converter"
    POSTGRES_PASSWORD: str = "changeme"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        """Synchronous URL used by Alembic."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # S3 / MinIO
    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_REPLAYS: str = "replays"
    MINIO_BUCKET_BINARIES: str = "binaries"
    MINIO_BUCKET_MAPS: str = "maps"
    MINIO_PRESIGN_EXPIRY: int = 3600  # seconds

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Device / session limits
    MAX_DEVICES_PER_USER: int = 2

    # SMTP (email 2FA)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@conlyse.com"
    SMTP_TLS: bool = True

    # 2FA email code TTL in seconds
    EMAIL_2FA_CODE_EXPIRE_SECONDS: int = 300

    # Email verification on registration (toggleable)
    EMAIL_VERIFICATION_ENABLED: bool = False
    EMAIL_VERIFICATION_CODE_EXPIRE_SECONDS: int = 3600

    # CORS
    # Comma-separated list of allowed origins, e.g. "https://app.conlyse.com,http://localhost:3000"
    CORS_ALLOW_ORIGINS: str = ""

    # Rate limiting (slowapi / limits syntax, e.g. "10/minute")
    RATE_LIMIT_ANONYMOUS: str = "10/minute"
    RATE_LIMIT_AUTHENTICATED: str = "60/minute"

    # General
    PROJECT_NAME: str = "Conlyse API"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False


settings = Settings()
