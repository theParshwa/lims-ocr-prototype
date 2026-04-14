"""
config.py - Application configuration using pydantic-settings.

All settings are loaded from environment variables or the .env file.
Override via environment variables for deployment flexibility.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Central application configuration."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────
    app_name: str = "LIMS OCR Document Processor"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # ── Server ───────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # ── CORS ─────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── File Storage ─────────────────────────────────────────
    upload_dir: Path = BASE_DIR / "uploads"
    output_dir: Path = BASE_DIR / "outputs"
    max_upload_size_mb: int = 100
    allowed_extensions: list[str] = [".pdf", ".docx", ".doc"]

    # ── Database ─────────────────────────────────────────────
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'lims_ocr.db'}"

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        """Auto-convert Supabase/standard postgres URLs to asyncpg driver format."""
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and "+asyncpg" not in v:
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # ── AI Provider (Azure OpenAI) ──────────────────────────
    azure_openai_endpoint: str = "https://eyq-incubator.asiapac.fabric.ey.com/eyq/as/api"
    azure_openai_api_key: Optional[str] = None
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_deployment: str = "gpt-5.1"           # deployment name in Azure
    azure_openai_embed_deployment: str = "text-embedding-3-small"  # embedding deployment name
    ai_temperature: float = 0.0
    ai_max_tokens: int = 8192

    # ── Extraction ───────────────────────────────────────────
    ocr_enabled: bool = True
    ocr_language: str = "eng"
    chunk_size: int = 12000      # characters per LLM chunk (fits ~5 pages in one call)
    chunk_overlap: int = 200

    # ── Redis / Celery ───────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── Confidence Thresholds ────────────────────────────────
    confidence_low_threshold: float = 0.6    # below → flag for review
    confidence_medium_threshold: float = 0.85

    def ensure_dirs(self) -> None:
        """Create storage directories if they do not exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


# Singleton instance used throughout the application
settings = Settings()
settings.ensure_dirs()
