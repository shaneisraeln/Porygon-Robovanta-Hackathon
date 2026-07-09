"""Analytics Engine — measured facts, labeled forecasts, competitive insight."""
from __future__ import annotations

from .. import ai, competitors, dashboard
from ..extract import fmt_money
from . import base

KIND = "engine_analytics"

_SYSTEM = (
    "You are a business analytics interpreter. You don't just display numbers — you explain what they mean, "
    "forecast trends, and surface competitive insight. You never present a forecast as a guaranteed fact.\n"
    "Rules:\n"
    "- Every forecast must be labeled as a projection based on a trend, with the method named briefly "
    "(e.g. 'based on 3-month linear trend').\n"
    "- Distinguish MEASURED facts (things that happened) from PROJECTED figures — never blur them.\n"
    "- Competitive insight must cite the specific competitor fact being compared against.\n"
    "- If a metric has fewer than 2-3 data points, mark it status 'insufficient_data' instead of projecting.\n"
    "- Tone: clear, calm, boardroom-ready — a CEO reads it in 30 seconds and knows what to do.\n"
    "Return valid JSON only, matching this schema:\n"
    '{"measured_summary": [{"metric": str, "value": str, "trend": str}],'
    ' "forecasts": [{"metric": str, "projected_value": str, "method": str, "confidence": "high|medium|low"} | {"metric": str, "status": "insufficient_data"}],'
    ' "competitive_insight": [{"insight": str, "grounded_in": str}],'
    ' "executive_summary": str}'
)


def _forecast(company_id: str) -> dict:
    m = ai.derive_metrics(company_id)
    monthly_rev = (m["revenue"] / 12) if m["revenue"] else 0.0
    growth = (m["growth"] or 0) / 100.0
    burn = m["monthly_spend"] or 0.0
    cash = m["cash"]
    months, rev, bank = [], monthly_rev, cash
    for i in range(1, 7):
        rev = rev * (1 + growth)
        net = rev - burn
        if bank is not None:
            bank += net
        months.append({"month": i, "revenue": round(rev), "net": round(net),
                        "cash": round(bank) if bank is not None else None})
    return {"projection": months, "runway_months": m.get("runway_months"), "grounded": bool(m["revenue"] or burn)}


def _heuristic(company_id: str, ctx: dict) -> dict:
    m = ctx["metrics"]
    measured, forecasts, comp_insight = [], [], []

    if m.get("revenue") is not None:
        measured.append({"metric": "Revenue", "value": fmt_money(m["revenue"]),
                         "trend": f"{m['growth_pct']}% MoM" if m.get("growth_pct") is not None else "trend unknown"})
    if m.get("customers") is not None:
        measured.append({"metric": "Customers", "value": str(m["customers"]), "trend": "—"})
    if m.get("churn_pct") is not None:
        measured.append({"metric": "Churn", "value": f"{m['churn_pct']}%", "trend": "—"})

    # Forecast revenue only if we have growth (a trend); else insufficient_data.
    if m.get("revenue") and m.get("growth_pct") is not None:
        proj = round(m["revenue"] / 12 * ((1 + m["growth_pct"] / 100) ** 6))
        forecasts.append({"metric": "Monthly revenue (in 6 months)", "projected_value": fmt_money(proj),
                          "method": "current MoM growth extrapolated 6 months", "confidence": "low"})
    else:
        forecasts.append({"metric": "Revenue", "status": "insufficient_data"})

    for w in ctx.get("where_you_win", [])[:2]:
        comp_insight.append({"insight": f"You win here: {w}", "grounded_in": "competitor comparison on file"})
    for e in ctx.get("where_youre_exposed", [])[:1]:
        comp_insight.append({"insight": f"Exposure: {e}", "grounded_in": "competitor comparison on file"})

    summary = ai.summarize_metrics(ai.derive_metrics(company_id))
    return {"measured_summary": measured, "forecasts": forecasts,
            "competitive_insight": comp_insight, "executive_summary": summary + "."}


def generate(company_id: str) -> dict:
    ctx = base.company_context(company_id)
    ai_part = base.run_engine(company_id, KIND, "Analytics summary", _SYSTEM, ctx, _heuristic)
    return live(company_id, _ai=ai_part)


def live(company_id: str, _ai: dict | None = None) -> dict:
    dash = dashboard.build_dashboard(company_id)
    comp = competitors.comparison(company_id)
    ai_part = _ai or base.load_or_note(company_id, KIND) or {}
    return {
        "kpis": dash["tiles"],
        "numeric_forecast": _forecast(company_id),
        "competitive": {
            "competitors": comp.get("competitors", []),
            "where_you_win": comp.get("where_you_win", []),
            "where_youre_exposed": comp.get("where_youre_exposed", []),
        },
        "measured_summary": ai_part.get("measured_summary"),
        "forecasts": ai_part.get("forecasts"),
        "competitive_insight": ai_part.get("competitive_insight"),
        "executive_summary_ai": ai_part.get("executive_summary"),
        "executive_summary": dash["executive_summary"],
        "generated_by": ai_part.get("generated_by"),
    }
