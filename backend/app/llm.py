"""LLM provider abstraction.

Default provider is `local`: a grounded, deterministic reasoner that NEVER
invents facts — it only composes from retrieved Company Memory. When
OPENAI_API_KEY / ANTHROPIC_API_KEY is configured, `complete()` calls the real
model with the same retrieved context. Either way, the Brain and Council are
grounded in evidence, satisfying the "no hallucination" rule.
"""
from __future__ import annotations

import httpx

from .config import settings


def active() -> bool:
    return settings.llm_active


def complete(system: str, prompt: str, max_tokens: int = 600) -> str | None:
    """Returns model text, or None when no provider is configured."""
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return _openai(system, prompt, max_tokens)
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        return _anthropic(system, prompt, max_tokens)
    return None


def _openai(system: str, prompt: str, max_tokens: int) -> str | None:
    try:
        r = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"model": settings.openai_model, "max_tokens": max_tokens,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]},
            timeout=40,
        )
        return r.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def _anthropic(system: str, prompt: str, max_tokens: int) -> str | None:
    try:
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01"},
            json={"model": settings.anthropic_model, "max_tokens": max_tokens, "system": system,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=40,
        )
        return r.json()["content"][0]["text"]
    except Exception:
        return None
