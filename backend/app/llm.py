"""LLM provider abstraction.

Priority, in order:
  1. A running **local Ollama** model (private — data never leaves the machine).
  2. A configured cloud provider (OpenAI / Anthropic) if a key is set.
  3. The grounded heuristic reasoner in the callers (when `complete()` returns None).

Default `LLM_PROVIDER=local` auto-detects Ollama, so installing Ollama and
pulling a model is enough — no config editing. Either way the Brain, Council and
Engines stay grounded in retrieved Company Memory (no hallucination).
"""
from __future__ import annotations

import time

import httpx

from .config import settings

import re

# Cache Ollama reachability + installed models so we don't ping on every call.
_ollama_cache: dict = {"checked": 0.0, "ok": False, "models": []}
_OLLAMA_TTL = 30.0  # seconds
# Remote endpoints (e.g. a Colab tunnel) are slower to reach than localhost.
_DETECT_TIMEOUT = float(settings.__dict__.get("ollama_detect_timeout", 0)) or 4.0

# Preferred general-purpose instruct models, best first. Code-only models
# (codellama) are used only as a last resort.
_MODEL_PREFS = ["qwen2.5", "qwen3", "qwen", "llama3.1", "llama3", "gpt-oss", "mistral", "gemma", "phi3", "phi"]
_THINK_RE = re.compile(r"<think>.*?</think>", re.S | re.I)


def _ollama_url() -> str:
    return settings.ollama_base_url.rstrip("/")


def _ollama_available() -> bool:
    now = time.time()
    if now - _ollama_cache["checked"] < _OLLAMA_TTL:
        return bool(_ollama_cache["ok"])
    ok, models = False, []
    try:
        r = httpx.get(f"{_ollama_url()}/api/tags", timeout=_DETECT_TIMEOUT)
        if r.status_code == 200:
            ok = True
            models = [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
    except Exception:
        ok = False
    _ollama_cache.update(checked=now, ok=ok, models=models)
    return ok


def _pick_model(fast: bool) -> str:
    """Use the configured model if installed, else the best available one."""
    configured = settings.ollama_fast_model if fast else settings.ollama_model
    models = _ollama_cache.get("models") or []
    if not models:
        return configured
    if configured in models:
        return configured
    for pref in _MODEL_PREFS:
        for m in models:
            if m.startswith(pref) or pref in m:
                return m
    non_code = [m for m in models if "codellama" not in m]
    return (non_code or models)[0]


def provider() -> str:
    """The provider that will actually be used right now."""
    p = settings.llm_provider
    if p in ("openai", "anthropic", "ollama"):
        return p
    # 'local'/'auto': prefer a running local model, else heuristic.
    return "ollama" if _ollama_available() else "local"


def active() -> bool:
    """True when a real model (local or cloud) is available to compose text."""
    p = provider()
    if p == "openai":
        return bool(settings.openai_api_key)
    if p == "anthropic":
        return bool(settings.anthropic_api_key)
    if p == "ollama":
        return _ollama_available()
    return False


def info() -> dict:
    """For the health endpoint / diagnostics."""
    p = provider()
    model = None
    if p == "ollama":
        _ollama_available()  # refresh installed-model cache
        model = _pick_model(fast=False)
    elif p == "openai":
        model = settings.openai_model
    elif p == "anthropic":
        model = settings.anthropic_model
    return {"provider": p, "active": active(), "model": model}


def complete(system: str, prompt: str, max_tokens: int = 600, fast: bool = False) -> str | None:
    """Returns model text, or None when no provider is available.

    `fast=True` uses the smaller/quicker local model (e.g. for chat replies)."""
    p = provider()
    if p == "ollama":
        return _ollama(system, prompt, max_tokens, fast)
    if p == "openai" and settings.openai_api_key:
        return _openai(system, prompt, max_tokens)
    if p == "anthropic" and settings.anthropic_api_key:
        return _anthropic(system, prompt, max_tokens)
    return None


def _ollama(system: str, prompt: str, max_tokens: int, fast: bool) -> str | None:
    if not _ollama_available():
        return None
    model = _pick_model(fast)
    try:
        r = httpx.post(
            f"{_ollama_url()}/api/chat",
            json={
                "model": model,
                "stream": False,
                "think": False,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "options": {"num_predict": max_tokens, "temperature": 0.4},
            },
            timeout=180,
        )
        content = (r.json().get("message") or {}).get("content")
    except Exception:
        return None
    if not content:
        return None
    # Strip any reasoning traces from "thinking" models.
    return _THINK_RE.sub("", content).strip()


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
