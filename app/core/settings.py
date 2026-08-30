from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# General local development settings, including the server-side OpenAI API key.
# Existing process variables always win so deployment configuration remains
# authoritative.
load_dotenv(PROJECT_ROOT / ".env", override=False)

# GitHub App credentials have their own hidden file. Existing process variables
# always win, which keeps deployment configuration authoritative.
load_dotenv(PROJECT_ROOT / ".env.github-app", override=False)


def _as_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_positive_int(value: str | None, *, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/openfde",
    )
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    openai_transcription_model: str = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")
    codex_model: str = os.getenv("CODEX_MODEL", "gpt-5.6-terra")
    codex_reasoning_effort: str = os.getenv("CODEX_REASONING_EFFORT", "medium")
    codex_runner_timeout_seconds: int = _as_positive_int(
        os.getenv("CODEX_RUNNER_TIMEOUT_SECONDS"), default=120
    )
    codex_clone_timeout_seconds: int = _as_positive_int(
        os.getenv("CODEX_CLONE_TIMEOUT_SECONDS"), default=60
    )
    codex_max_repository_bytes: int = _as_positive_int(
        os.getenv("CODEX_MAX_REPOSITORY_BYTES"), default=250_000_000
    )
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    )
    app_base_url: str = os.getenv("APP_BASE_URL", "http://localhost:8001").rstrip("/")
    frontend_base_url: str = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")
    cookie_secure: bool = _as_bool(os.getenv("COOKIE_SECURE"))
    github_app_id: str | None = os.getenv("GITHUB_APP_ID")
    github_app_slug: str | None = os.getenv("GITHUB_APP_SLUG")
    github_client_id: str | None = os.getenv("GITHUB_APP_CLIENT_ID")
    github_client_secret: str | None = os.getenv("GITHUB_APP_CLIENT_SECRET")
    github_private_key: str | None = os.getenv("GITHUB_APP_PRIVATE_KEY")
    github_private_key_path: str | None = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
    github_webhook_secret: str | None = os.getenv("GITHUB_WEBHOOK_SECRET")
    github_state_secret: str | None = os.getenv("GITHUB_STATE_SECRET")

    @property
    def github_oauth_callback_url(self) -> str:
        return f"{self.app_base_url}/v1/integrations/github/oauth/callback"

    def missing_github_settings(self) -> list[str]:
        values = {
            "GITHUB_APP_ID": self.github_app_id,
            "GITHUB_APP_SLUG": self.github_app_slug,
            "GITHUB_APP_CLIENT_ID": self.github_client_id,
            "GITHUB_APP_CLIENT_SECRET": self.github_client_secret,
            "GITHUB_STATE_SECRET": self.github_state_secret,
        }
        missing = [name for name, value in values.items() if not value]
        if not self.github_private_key and not self.github_private_key_path:
            missing.append("GITHUB_APP_PRIVATE_KEY or GITHUB_APP_PRIVATE_KEY_PATH")
        return missing

    def read_github_private_key(self) -> str:
        if self.github_private_key:
            return self.github_private_key.replace("\\n", "\n")
        if self.github_private_key_path:
            path = Path(self.github_private_key_path).expanduser()
            if not path.is_absolute():
                path = PROJECT_ROOT / path
            return path.read_text(encoding="utf-8")
        raise RuntimeError("GitHub App private key is not configured")


def get_settings() -> Settings:
    return settings


settings = Settings()
