from pathlib import Path
from typing import List, Union
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    app_name: str = "QA Intelligence Hub API"
    app_version: str = "0.1.0"
    environment: str = "development"
    jwt_secret: str = ""
    api_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./qa_intelligence.db"

    cors_origins: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    ai_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    qa_domain: str = "airline"

    @model_validator(mode="after")
    def normalize_settings(self) -> "Settings":
        # 1. Normalize database URL for PostgreSQL psycopg3 driver compatibility
        url = self.database_url
        if url.startswith("postgres://"):
            self.database_url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+psycopg://"):
            self.database_url = url.replace("postgresql://", "postgresql+psycopg://", 1)

        # 2. Normalize CORS origins if provided as comma-separated string
        if isinstance(self.cors_origins, str):
            self.cors_origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]

        # 3. Normalize QA domain
        if self.qa_domain:
            self.qa_domain = self.qa_domain.strip().lower()

        return self

    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()