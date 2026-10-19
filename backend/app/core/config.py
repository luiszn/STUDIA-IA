"""Application configuration.

All runtime configuration is environment driven (12-factor). Nothing secret is
hardcoded; `.env.example` documents every variable.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Runtime settings loaded from the environment / `.env` file."""

    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), str(BACKEND_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ----------------------------- General --------------------------------
    app_name: str = "STUDIA AI"
    app_env: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ----------------------------- Security -------------------------------
    secret_key: str = "insecure-development-key-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # ----------------------------- Database -------------------------------
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'studia.sqlite3').as_posix()}"
    db_echo: bool = False

    # ------------------------------ AI ------------------------------------
    ai_provider: Literal["ollama", "openai", "local"] = "local"
    ai_timeout_seconds: int = 120
    ai_temperature: float = 0.3
    ai_max_tokens: int = 2048

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2:3b"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_keep_alive: str = "10m"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # ------------------------------ RAG -----------------------------------
    embedding_dimensions: int = 768
    chunk_size: int = 1200
    chunk_overlap: int = 180
    rag_top_k: int = 5
    rag_min_score: float = 0.15

    # ---------------------------- Uploads ---------------------------------
    upload_dir: str = "./storage/uploads"
    max_upload_mb: int = 20
    allowed_extensions: str = ".pdf,.docx,.txt"

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, value: str) -> str:
        return value.upper()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_extension_list(self) -> list[str]:
        return [
            ext.strip().lower() if ext.strip().startswith(".") else f".{ext.strip().lower()}"
            for ext in self.allowed_extensions.split(",")
            if ext.strip()
        ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def resolved_upload_dir(self) -> Path:
        path = Path(self.upload_dir)
        if not path.is_absolute():
            path = BACKEND_DIR / path
        return path.resolve()

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (import-safe, cheap)."""
    return Settings()


settings = get_settings()