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
    instagram_token: str | None = os.getenv("INSTAGRAM_TOKEN")
    facebook_token: str | None = os.getenv("FACEBOOK_TOKEN")

    # Web research / search providers (all optional; keyless DuckDuckGo fallback).
    search_provider: str = os.getenv("SEARCH_PROVIDER", "auto").lower()  # auto | tavily | serper | brave | duckduckgo
    tavily_api_key: str | None = os.getenv("TAVILY_API_KEY")
    serper_api_key: str | None = os.getenv("SERPER_API_KEY")
    brave_api_key: str | None = os.getenv("BRAVE_API_KEY")

    # OAuth apps for one-click "Connect" (per provider client id/secret + redirect).
    # When absent, connectors fall back to token paste. Register apps in each
    # provider's developer console to enable sign-in.
    oauth_redirect_base: str = os.getenv("OAUTH_REDIRECT_BASE", "http://127.0.0.1:8000")
    frontend_base: str = os.getenv("FRONTEND_BASE", "http://localhost:3000")

    cors_origins: list[str] = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()
    ]

    def oauth_client(self, provider: str) -> dict | None:
        """Return {client_id, client_secret} for a provider if configured."""
        cid = os.getenv(f"{provider.upper()}_CLIENT_ID")
        secret = os.getenv(f"{provider.upper()}_CLIENT_SECRET")
        if cid and secret:
            return {"client_id": cid, "client_secret": secret}
        return None

    @property
    def search_active(self) -> bool:
        return True  # always available via keyless DuckDuckGo fallback

    @property
    def llm_active(self) -> bool:
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        if self.llm_provider == "anthropic":
            return bool(self.anthropic_api_key)
        return False


settings = Settings()
