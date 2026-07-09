"""Strategy Engine — market research, positioning, pricing, GTM sequence."""
from __future__ import annotations

from .. import memory
from . import base

KIND = "engine_strategy"

_SYSTEM = (
    "You are a senior startup strategist who has advised 100+ early-stage founders — think YC partner "
    "meets brand consultant. You do market research, brand positioning, pricing strategy, and high-level "
    "GTM design.\n"
    "Rules you must follow:\n"
    "- Ground every recommendation in the facts provided. Never invent market size numbers, competitor "
    "details, or pricing benchmarks that aren't in the input.\n"
    "- If a section lacks enough data to be confident, say so explicitly rather than filling the gap with "
    "generic advice.\n"
    "- Be specific and opinionated, not vague. 'Improve your brand' is not an output. 'Reposition around "
    "live instruction since your only tracked competitors sell recorded content' is an output.\n"
    "- Write like a sharp advisor talking to a founder — punchy, direct, no buzzwords like 'synergy' or "
    "'leverage'.\n"
    "Return valid JSON only, matching this schema:\n"
    '{"positioning": {"statement": str, "grounded_in": [str], "confidence": "high|medium|low"},'
    ' "pricing": {"recommendation": str, "rationale": str, "confidence": "high|medium|low"},'
    ' "gtm_sequence": [{"step": str, "why_this_first": str}],'
    ' "insufficient_data_flags": [str]}'
)


def _query(ctx: dict) -> str:
    c = ctx["company"]
    return f"{c['what'] or c['name']} market size trends competitors pricing"


def _heuristic(company_id: str, ctx: dict) -> dict:
    c, m, f = ctx["company"], ctx["metrics"], ctx["facts"]
    cust = c["customers"] or "your target customers"
    edge = ctx["where_you_win"][0] if ctx["where_you_win"] else None
    grounded, flags = [], []

    if c["what"]:
        grounded.append(f"product: {c['what']}")
    if ctx["competitors"]:
        grounded.append(f"competitors: {', '.join(ctx['competitors'][:3])}")
    else:
        flags.append("No competitors on file — add some to sharpen positioning.")
    if not f["geography"]:
        flags.append("No target geography/market on file.")

    statement = f"For {cust}, {c['name'] or 'we'} is the solution for {(c['what'] or 'this need').lower()}" + (f" — {edge}." if edge else ".")
    pos_conf = "high" if (c["what"] and ctx["competitors"]) else "medium" if c["what"] else "low"

    if f["pricing"]:
        pricing = {"recommendation": f"Keep anchoring on {f['pricing']}; test a higher tier for power users.",
                   "rationale": "You already have a price point on file; expand up-market before discounting.",
                   "confidence": "medium"}
    else:
        pricing = {"recommendation": "Introduce simple value-based tiers (Starter / Growth / Business).",
                   "rationale": "No pricing on file; tiering captures different willingness-to-pay.",
                   "confidence": "low"}
        flags.append("No pricing on file.")

    gtm = [{"step": "Put the positioning statement on the homepage and in outreach", "why_this_first": "Clarity converts before anything else."},
           {"step": "Win one beachhead segment before expanding", "why_this_first": "Focus compounds at your stage."}]
    if edge:
        gtm.append({"step": f"Lead with your edge: {edge}", "why_this_first": "It's your clearest differentiator on file."})

    return {"positioning": {"statement": statement, "grounded_in": grounded, "confidence": pos_conf},
            "pricing": pricing, "gtm_sequence": gtm, "insufficient_data_flags": flags}


def generate(company_id: str) -> dict:
    base_ctx = base.company_context(company_id)
    ctx = base.company_context(company_id, web_query=_query(base_ctx))
    result = base.run_engine(company_id, KIND, "Strategy brief", _SYSTEM, ctx, _heuristic)
    pos = (result.get("positioning") or {}).get("statement")
    if pos:
        memory.add_fact(company_id, "strategy", "positioning", "Positioning statement", pos[:300],
                        source_ref="Strategy Engine", source_kind="conversation",
                        evidence=pos[:200], confidence=0.7, owner="system")
    return result


def latest(company_id: str) -> dict | None:
    return base.load_or_note(company_id, KIND)
