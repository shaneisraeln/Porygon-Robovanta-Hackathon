"""Runtime configuration loaded from environment (12-factor).

Every external service is optional: when its env var is absent the app falls
back to a runnable embedded implementation, so the backend boots with zero
infrastructure while remaining production-ready when the services are wired in.
"""
from __future__ import annotations

import os
from pathlib import Path

# Load a .env file if present (no hard dependency on python-dotenv).
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists():
    for _line in _ENV_PATH.read_text().splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip())

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


class Settings:
    # Storage
    database_url: str | None = os.getenv("DATABASE_URL")
    sqlite_path: str = str(DATA_DIR / "cbo.db")
    neo4j_url: str | None = os.getenv("NEO4J_URL")
    qdrant_url: str | None = os.getenv("QDRANT_URL")
    redis_url: str | None = os.getenv("REDIS_URL")

    # AI
    llm_provider: str = os.getenv("LLM_PROVIDER", "local").lower()
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")

    # Connector default credentials (per-company tokens override these)
    github_token: str | None = os.getenv("GITHUB_TOKEN")
    notion_token: str | None = os.getenv("NOTION_TOKEN")
    slack_token: str | None = os.getenv("SLACK_TOKEN")
    stripe_api_key: str | None = os.getenv("STRIPE_API_KEY")

    cors_origins: list[str] = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()
    ]

    @property
    def llm_active(self) -> bool:
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        if self.llm_provider == "anthropic":
            return bool(self.anthropic_api_key)
        return False


settings = Settings()
