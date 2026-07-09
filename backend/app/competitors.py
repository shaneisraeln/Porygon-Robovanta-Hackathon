"""Competitor Analysis (v2).

Introduces the `competitor` fact type and a comparison engine that builds a
feature / pricing / positioning gap table and a grounded "Where You Win / Where
You're Exposed" read. Everything is derived from entered facts — when the LLM is
active it composes the win/exposed narrative over the SAME structured data
(never outside knowledge); otherwise a deterministic rule set is used.
"""
from __future__ import annotations

import json
import re

from . import llm, memory, research

COMPETITOR_TYPE = "competitor"

_EXTRACT_SYSTEM = (
    "You are a market analyst. From the provided web search results, extract the real competing "
    "PRODUCTS or companies (never review sites, listicles or aggregators). Return ONLY a JSON array "
    "of objects: [{\"name\": str, \"positioning\": str, \"url\": str}]. Use only names that actually "
    "appear as products in the results. No prose, no code fences."
)

# Signals scanned in competitor positioning/notes — grounded in entered text.
_THEM_STRONGER = re.compile(r"cheaper|lower price|less expensive|faster|bigger|larger|"
                            r"more funding|well[- ]funded|enterprise|incumbent|established|"
                            r"market leader|more features|scale", re.I)
_THEM_WEAKER = re.compile(r"limited|early|niche|lacks|lacking|no [a-z]|slow|expensive|"
                          r"legacy|outdated|manual|clunky|hard to use|poor", re.I)


def add_competitor(company_id: str, name: str, features: str = "", pricing: str = "",
                   positioning: str = "", notes: str = "", url: str = "") -> dict:
    payload = {"name": name, "features": features, "pricing": pricing,
               "positioning": positioning, "notes": notes, "url": url}
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "competitor"
    memory.add_fact(
        company_id, COMPETITOR_TYPE, f"competitor_{slug}", f"Competitor: {name}",
        json.dumps(payload), source_ref="Competitor analysis", source_kind="conversation",
        evidence=positioning or notes, confidence=0.8, owner="founder",
        entity_id=memory.upsert_entity(company_id, "competitor", name, "competes with"),
    )
    return payload


def list_competitors(company_id: str) -> list[dict]:
    out = []
    seen = set()
    for f in memory.list_facts(company_id):  # newest first — keep latest per name
        if f["type"] != COMPETITOR_TYPE:
            continue
        try:
            rec = json.loads(f["value"])
        except (ValueError, TypeError):
            continue
        key = rec.get("name", "").lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(rec)
    return out


def _us(company_id: str) -> dict:
    co = memory.get_company(company_id) or {}
    def latest_text(key: str) -> str:
        for f in memory.list_facts(company_id):
            if f["key"] == key and f["value"]:
                return f["value"]
        return ""
    return {
        "name": co.get("name", "You"),
        "features": latest_text("features"),
        "pricing": latest_text("pricing"),
        "positioning": co.get("what") or latest_text("positioning"),
    }


def _rule_based(us: dict, comps: list[dict]) -> tuple[list[str], list[str]]:
    wins, exposed = [], []
    for c in comps:
        blob = f"{c.get('positioning','')} {c.get('notes','')}"
        for m in set(_THEM_STRONGER.findall(blob)):
            exposed.append(f"{c['name']} is stronger on: {m.lower()}")
        for m in set(_THEM_WEAKER.findall(blob)):
            wins.append(f"vs {c['name']}: they're {m.lower().strip()}")
    if us.get("positioning"):
        wins.append(f"You have a defined wedge: \"{us['positioning'][:80]}\"")
    if not us.get("features"):
        exposed.append("Your own feature set isn't on file — add it to sharpen the comparison.")
    # De-dup while preserving order.
    dd = lambda xs: list(dict.fromkeys(xs))  # noqa: E731
    return dd(wins)[:5], dd(exposed)[:5]


def comparison(company_id: str) -> dict:
    comps = list_competitors(company_id)
    us = _us(company_id)

    if not comps:
        return {"us": us, "competitors": [], "table": [], "where_you_win": [],
                "where_youre_exposed": [], "insufficient": True,
                "note": "No competitors on file yet. Add one to build the comparison."}

    dims = [("features", "Features"), ("pricing", "Pricing"), ("positioning", "Positioning")]
    table = [{
        "dimension": label,
        "us": us.get(key, "") or "—",
        "competitors": [{"name": c["name"], "value": c.get(key, "") or "—"} for c in comps],
    } for key, label in dims]

    wins, exposed = _rule_based(us, comps)

    # Optional LLM narrative over the SAME structured data — grounded, no outside knowledge.
    if llm.active():
        ctx = json.dumps({"us": us, "competitors": comps})
        out = llm.complete(
            "You are CBO's Market analyst. Using ONLY the structured comparison data provided, "
            "list where the company wins and where it is exposed. Do not invent facts about any "
            "company beyond what is given. Return two short bullet lists labeled WIN: and EXPOSED:.",
            ctx,
        )
        if out:
            w, e = _parse_llm(out)
            if w:
                wins = w
            if e:
                exposed = e

    return {"us": us, "competitors": comps, "table": table, "where_you_win": wins,
            "where_youre_exposed": exposed, "insufficient": False, "note": ""}


def _parse_llm(text: str) -> tuple[list[str], list[str]]:
    wins, exposed, bucket = [], [], None
    for line in text.splitlines():
        s = line.strip(" -•\t")
        if not s:
            continue
        low = s.lower()
        if low.startswith("win"):
            bucket = wins
            s = s.split(":", 1)[-1].strip()
            if not s:
                continue
        elif low.startswith("exposed"):
            bucket = exposed
            s = s.split(":", 1)[-1].strip()
            if not s:
                continue
        if bucket is not None and s:
            bucket.append(s)
    return wins[:5], exposed[:5]


def _name_from_domain(url: str) -> str:
    host = research.domain_of(url)
    label = host.split(".")[0]
    if label in ("www", "app", "get", "try", "go"):
        parts = host.split(".")
        label = parts[1] if len(parts) > 1 else label
    return label.replace("-", " ").title()


def _looks_like_us(name: str, us: dict) -> bool:
    return name.lower().strip() == (us.get("name", "").lower().strip())


def _parse_competitors_json(text: str) -> list[dict]:
    if not text:
        return []
    t = text.strip().strip("`")
    t = re.sub(r"^json", "", t).strip()
    m = re.search(r"\[.*\]", t, re.S)
    if m:
        t = m.group(0)
    try:
        data = json.loads(t)
    except (ValueError, TypeError):
        return []
    out = []
    for x in data if isinstance(data, list) else []:
        if isinstance(x, dict) and x.get("name"):
            out.append({"name": str(x["name"])[:60], "positioning": str(x.get("positioning", ""))[:160],
                        "url": str(x.get("url", ""))})
    return out


def discover_competitors(company_id: str, limit: int = 6) -> dict:
    """Find similar products on the web and add them as cited competitor facts."""
    us = _us(company_id)
    seed = us.get("positioning") or us.get("features")
    if not seed:
        return {**comparison(company_id), "discovered": 0,
                "note": "Add a one-line product description in onboarding first — I search the web from that."}

    query = f"best alternatives to and competitors of {seed}"
    results = research.web_search(query, k=10)
    if not results:
        return {**comparison(company_id), "discovered": 0,
                "note": "Web search returned nothing (network or provider issue). Try again, or add competitors manually."}

    existing = {c["name"].lower() for c in list_competitors(company_id)}
    added: list[str] = []

    # Primary path: LLM extracts real products from the fetched results.
    if llm.active():
        parsed = _parse_competitors_json(research.summarize(query, results, _EXTRACT_SYSTEM) or "")
        for p in parsed:
            if len(added) >= limit:
                break
            name = p["name"].strip()
            if not name or name.lower() in existing or _looks_like_us(name, us):
                continue
            add_competitor(company_id, name, positioning=p["positioning"], url=p["url"],
                           notes=f"Discovered via web research. Source: {p['url'] or 'search'} — review before relying on it.")
            added.append(name)
            existing.add(name.lower())

    # Keyless fallback: derive product names from non-aggregator result domains.
    if not added:
        for r in results:
            if len(added) >= limit:
                break
            if research.is_aggregator(r["url"]):
                continue
            name = _name_from_domain(r["url"])
            if not name or name.lower() in existing or _looks_like_us(name, us):
                continue
            add_competitor(company_id, name, positioning=(r.get("snippet") or "")[:160], url=r["url"],
                           notes=f"Discovered via web: {r['url']} — unverified, review before relying on it.")
            added.append(name)
            existing.add(name.lower())

    comp = comparison(company_id)
    comp["discovered"] = len(added)
    comp["added"] = added
    comp["provider"] = research.available_provider()
    comp["note"] = (f"Found {len(added)} candidate(s) via web research — verify each before trusting it."
                    if added else "No new competitors extracted. Add one manually, or set an LLM key for sharper extraction.")
    return comp


def market_signal(company_id: str) -> dict:
    """Compact signal for the Market Agent: competitor count + top exposure."""
    comp = comparison(company_id)
    if comp["insufficient"]:
        return {"count": 0, "top_exposure": None, "top_win": None}
    return {
        "count": len(comp["competitors"]),
        "top_exposure": comp["where_youre_exposed"][0] if comp["where_youre_exposed"] else None,
        "top_win": comp["where_you_win"][0] if comp["where_you_win"] else None,
    }
