from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "PARAKH API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    VERSION: str = "0.1.0"

    # Database
    DATABASE_URL: str = (
        "postgresql+psycopg://parakh:parakh_password@localhost:5432/parakh"
    )

    # Security & JWT
    SECRET_KEY: str = "parakh-super-secret-key-change-in-production-0987654321"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    # Assessment Engine Selection ("mock" or "ml")
    ASSESSMENT_ENGINE: str = "mock"

settings = Settings()
