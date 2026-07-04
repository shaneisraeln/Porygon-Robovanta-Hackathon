"""Web research layer.

Real internet search behind one function. Uses the best provider that's
configured (Tavily / Serper / Brave for quality), and falls back to a keyless
DuckDuckGo HTML scrape so search works with zero configuration. An optional LLM
pass structures/summarizes results over the SAME fetched data — it never invents
sources. Every result carries its real URL for citation.
"""
from __future__ import annotations

import html
import json
import re

import httpx

from .config import settings

_UA = {"User-Agent": "Mozilla/5.0 (compatible; CBO-Research/1.0)"}


def available_provider() -> str:
    p = settings.search_provider
    if p != "auto":
        return p
    if settings.tavily_api_key:
        return "tavily"
    if settings.serper_api_key:
        return "serper"
    if settings.brave_api_key:
        return "brave"
    return "duckduckgo"


def web_search(query: str, k: int = 8) -> list[dict]:
    """Return [{title, url, snippet}] from the active provider. Never raises."""
    provider = available_provider()
    try:
        if provider == "tavily" and settings.tavily_api_key:
            return _tavily(query, k)
        if provider == "serper" and settings.serper_api_key:
            return _serper(query, k)
        if provider == "brave" and settings.brave_api_key:
            return _brave(query, k)
        return _duckduckgo(query, k)
    except Exception:
        # Last-resort fallback if a keyed provider fails at runtime.
        try:
            return _duckduckgo(query, k)
        except Exception:
            return []


def _tavily(query: str, k: int) -> list[dict]:
    r = httpx.post("https://api.tavily.com/search", timeout=20, json={
        "api_key": settings.tavily_api_key, "query": query, "max_results": k})
    data = r.json()
    return [{"title": x.get("title", ""), "url": x.get("url", ""), "snippet": x.get("content", "")}
            for x in data.get("results", [])][:k]


def _serper(query: str, k: int) -> list[dict]:
    r = httpx.post("https://google.serper.dev/search", timeout=20,
                   headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"},
                   json={"q": query, "num": k})
    data = r.json()
    return [{"title": x.get("title", ""), "url": x.get("link", ""), "snippet": x.get("snippet", "")}
            for x in data.get("organic", [])][:k]


def _brave(query: str, k: int) -> list[dict]:
    r = httpx.get("https://api.search.brave.com/res/v1/web/search", timeout=20,
                  headers={"X-Subscription-Token": settings.brave_api_key, "Accept": "application/json"},
                  params={"q": query, "count": k})
    data = r.json()
    return [{"title": x.get("title", ""), "url": x.get("url", ""), "snippet": x.get("description", "")}
            for x in data.get("web", {}).get("results", [])][:k]


_DDG_LINK = re.compile(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_DDG_SNIP = re.compile(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', re.S)
_TAG = re.compile(r"<[^>]+>")


def _clean(s: str) -> str:
    return html.unescape(_TAG.sub("", s)).strip()


def _ddg_real_url(href: str) -> str:
    m = re.search(r"[?&]uddg=([^&]+)", href)
    if m:
        from urllib.parse import unquote
        return unquote(m.group(1))
    return href


def _duckduckgo(query: str, k: int) -> list[dict]:
    r = httpx.post("https://html.duckduckgo.com/html/", timeout=20, headers=_UA, data={"q": query})
    body = r.text
    links = _DDG_LINK.findall(body)
    snips = _DDG_SNIP.findall(body)
    out = []
    for i, (href, title) in enumerate(links[:k]):
        out.append({
            "title": _clean(title),
            "url": _ddg_real_url(href),
            "snippet": _clean(snips[i]) if i < len(snips) else "",
        })
    return out


# Aggregators/listicles that aren't themselves products.
_AGGREGATORS = {"g2.com", "capterra.com", "getapp.com", "trustradius.com", "producthunt.com",
                "reddit.com", "medium.com", "youtube.com", "wikipedia.org", "quora.com",
                "linkedin.com", "twitter.com", "x.com", "facebook.com", "crunchbase.com",
                "softwareadvice.com", "gartner.com", "forbes.com", "techcrunch.com"}


def domain_of(url: str) -> str:
    m = re.search(r"https?://([^/]+)/?", url)
    host = (m.group(1) if m else url).lower().lstrip("www.")
    return host


def is_aggregator(url: str) -> bool:
    host = domain_of(url)
    return any(host == a or host.endswith("." + a) for a in _AGGREGATORS)


def summarize(query: str, results: list[dict], system: str) -> str | None:
    """Optional LLM pass over fetched results. Returns None if no LLM."""
    from . import llm
    if not llm.active() or not results:
        return None
    ctx = json.dumps([{"title": r["title"], "url": r["url"], "snippet": r["snippet"]} for r in results])
    return llm.complete(system, f"Query: {query}\n\nSearch results (use ONLY these):\n{ctx}")
