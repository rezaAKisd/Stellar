"""Application configuration using Pydantic Settings"""
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    APP_NAME: str = "Stellar Instagram Downloader API"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production-please-use-a-strong-random-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Directories
    DATA_DIR: Path = Path("./data")
    SESSION_DIR: Path = Path("./.stellar/session")

    # Redis (optional - for task tracking)
    REDIS_URL: str = "redis://localhost:6379"
    USE_REDIS: bool = False  # Set to True when Redis is available

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True  # Auto-reload in development

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.SESSION_DIR.mkdir(parents=True, exist_ok=True)


# Create global settings instance
settings = Settings()
