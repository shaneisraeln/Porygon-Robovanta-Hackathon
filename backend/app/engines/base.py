"""Shared engine recipe.

    gather context  →  reason (local LLM, else grounded heuristic)  →  save  →  return

Every engine calls `run_engine(...)`. The LLM is asked to return JSON matching a
schema; if it's unavailable or returns junk, the engine's heuristic builder
produces the same shape from real data. Output is saved as a versioned artifact
so GET can load instantly and POST regenerates.
"""
from __future__ import annotations

import json
import re
from typing import Callable

from .. import ai, competitors, llm, memory, metrics, research
from ..extract import fmt_money


# ---------------- context assembly ----------------

def company_context(company_id: str, *, web_query: str | None = None, web_k: int = 6) -> dict:
    """A compact, grounded snapshot of the business for any engine."""
    co = memory.get_company(company_id) or {}
    m = ai.derive_metrics(company_id)
    lead = metrics.calc_lead_score(company_id)
    churn = metrics.calc_churn(company_id)
    cac_ltv = metrics.calc_cac_ltv(company_id, m)

    def fact(key: str) -> str:
        for f in memory.list_facts(company_id):
            if f["key"] == key and f["value"]:
                return f["value"]
        return ""

    comp = competitors.comparison(company_id)
    ctx = {
        "company": {"name": co.get("name", ""), "what": co.get("what", ""),
                     "customers": co.get("customers", ""), "stage": co.get("stage", "")},
        "metrics": {
            "revenue": m.get("revenue"), "growth_pct": m.get("growth"), "customers": m.get("customers"),
            "retention_pct": m.get("retention"), "churn_pct": churn.get("churn_rate"),
            "monthly_burn": m.get("monthly_spend"), "runway_months": m.get("runway_months"),
            "lead_score": lead.get("lead_score"), "cac_ltv_ratio": cac_ltv.get("ratio"),
            "health": m.get("health"), "market_position": m.get("market_position"),
        },
        "facts": {
            "pricing": fact("pricing"), "features": fact("features"),
            "business_model": fact("business_model"), "geography": fact("geography"),
            "acquisition_channels": fact("marketing"), "problem": fact("problem"),
            "lead_source_mix": fact("lead_source_mix"),
            "lead_conversion_rate": fact("lead_conversion_rate"),
            "sales_motion": fact("sales_motion"),
            "target_segment": fact("segment"),
        },
        "competitors": [c["name"] for c in comp.get("competitors", [])],
        "where_you_win": comp.get("where_you_win", []),
        "where_youre_exposed": comp.get("where_youre_exposed", []),
        "recent_outcomes": _recent_outcomes(company_id),
    }
    if web_query:
        ctx["web_research"] = research.web_search(web_query, k=web_k)
    return ctx


def _recent_outcomes(company_id: str) -> list[str]:
    from .. import outcomes
    out = []
    for o in outcomes.get_recent_outcomes(company_id, limit=5):
        out.append(f"{o.get('outcome_metric', 'metric')}: {o.get('baseline_value') or '—'} → {o.get('outcome_value') or '?'}")
    return out


def context_text(ctx: dict) -> str:
    """Readable, compact rendering of the context for the LLM prompt."""
    c, m, f = ctx["company"], ctx["metrics"], ctx["facts"]
    lines = [f"Company: {c['name'] or 'Unknown'}",
             f"What they do: {c['what'] or 'unknown'}",
             f"Customers: {c['customers'] or 'unknown'}",
             f"Stage: {c['stage'] or 'unknown'}", "", "Metrics (None = not on file):"]
    for k, v in m.items():
        if v is not None:
            lines.append(f"  - {k}: {v}")
    lines.append("")
    for k, v in f.items():
        if v:
            lines.append(f"{k}: {v}")
    if ctx.get("competitors"):
        lines.append("\nCompetitors: " + ", ".join(ctx["competitors"]))
    if ctx.get("where_you_win"):
        lines.append("Where you win: " + "; ".join(ctx["where_you_win"][:4]))
    if ctx.get("where_youre_exposed"):
        lines.append("Where you're exposed: " + "; ".join(ctx["where_youre_exposed"][:4]))
    if ctx.get("recent_outcomes"):
        lines.append("\nPast campaign outcomes: " + "; ".join(ctx["recent_outcomes"]))
    if ctx.get("web_research"):
        lines.append("\nWeb research results (use only these for external facts):")
        for r in ctx["web_research"]:
            lines.append(f"  - {r['title']} ({r['url']}): {r['snippet'][:160]}")
    return "\n".join(lines)


# ---------------- robust JSON parsing ----------------

def parse_json(text: str | None):
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip().rstrip("`").strip()
    # Grab the outermost object/array.
    for opener, closer in (("{", "}"), ("[", "]")):
        i, j = t.find(opener), t.rfind(closer)
        if i != -1 and j != -1 and j > i:
            try:
                return json.loads(t[i:j + 1])
            except (ValueError, TypeError):
                continue
    try:
        return json.loads(t)
    except (ValueError, TypeError):
        return None


# ---------------- the runner ----------------

def run_engine(
    company_id: str,
    kind: str,
    title: str,
    system_prompt: str,
    ctx: dict,
    heuristic_builder: Callable[[str, dict], dict],
    *,
    max_tokens: int = 1400,
    ctx_text: str | None = None,
) -> dict:
    """Generate an engine result (LLM-first, heuristic fallback) and save it."""
    result = None
    used = "heuristic"
    if llm.active():
        raw = llm.complete(system_prompt, (ctx_text or context_text(ctx)) +
                           "\n\nReturn ONLY valid JSON in the schema described. No prose, no code fences.",
                           max_tokens=max_tokens)
        parsed = parse_json(raw)
        if isinstance(parsed, dict):
            result = parsed
            used = "local-ai"
    if result is None:
        result = heuristic_builder(company_id, ctx)
    result["generated_by"] = used
    saved = memory.save_artifact(company_id, kind, title, result)
    result["version"] = saved["version"]
    return result


def load_or_note(company_id: str, kind: str) -> dict | None:
    art = memory.latest_artifact(company_id, kind)
    if not art:
        return None
    content = art["content"]
    content["version"] = art["version"]
    return content


# Small shared helpers for heuristic builders.
def money(v) -> str:
    return fmt_money(v) if v is not None else "—"
