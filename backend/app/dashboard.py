"""Business Intelligence Dashboard v2 — the "Dominate" surface.

Assembles the nine PS-04 KPI tiles as a pure aggregator over Company Memory.
No new computation lives here that isn't grounded in stored facts: scores come
from `metrics` and `ai.derive_metrics`, recommendations from the Growth Agent,
and risk/summary from the same reasoning used elsewhere. Tiles that lack data
return `status: "insufficient"` rather than a fabricated number.
"""
from __future__ import annotations

from . import ai, growth, memory, metrics
from .extract import fmt_money


def _score_status(score: float | None, warn_below: float = 55) -> str:
    if score is None:
        return "insufficient"
    return "warn" if score < warn_below else "ok"


def _risk_alerts(company_id: str, m: dict) -> list[dict]:
    alerts: list[dict] = []

    def add(title: str, detail: str, severity: str):
        alerts.append({"title": title, "detail": detail, "severity": severity})

    if m.get("monthly_spend") and not m.get("revenue"):
        add("Burn without revenue", f"Spending {fmt_money(m['monthly_spend'])}/mo with no revenue on file.", "high")
    if m.get("runway_months") is not None and m["runway_months"] <= 6:
        add("Short runway", f"About {m['runway_months']} months of runway remaining.", "high")

    churn = metrics.calc_churn(company_id)["churn_rate"]
    if churn is not None and churn >= 10:
        add("Elevated churn", f"Churn is {churn}% — retention is leaking revenue.", "medium")

    ratio = metrics.calc_cac_ltv(company_id, m)["ratio"]
    if ratio is not None and ratio < 1:
        add("Unsustainable unit economics", f"CAC:LTV is {ratio}:1 — you lose money per customer.", "high")

    lead = metrics.calc_lead_score(company_id)
    if lead["detail"].get("single_channel_risk"):
        add("Single-channel lead dependency", "All leads come from one channel — concentration risk.", "medium")

    for inv in memory.list_investors(company_id):
        if inv["state"] == "cooling":
            add(f"{inv['firm']} is cooling", "An investor relationship is losing momentum.", "medium")
            break

    if not alerts:
        add("No critical flags", "Nothing urgent surfaced from memory — keep instrumenting.", "low")
    return alerts


def _executive_summary(company_id: str, m: dict) -> str:
    bits = [ai.summarize_metrics(m)]
    ratio = metrics.calc_cac_ltv(company_id, m)["ratio"]
    if ratio is not None:
        bits.append(f"CAC:LTV {ratio}:1")
    posture = "raise-ready" if m["fundraising_readiness"] >= 75 else "still building the raise story"
    bits.append(f"Fundraising: {posture} ({m['fundraising_readiness']}%)")
    # v3 feedback loop made visible on the dashboard.
    learnings = ai.outcome_learnings(company_id, limit=1)
    if learnings:
        bits.append(f"Last measured outcome: {learnings[0]}")
    return " · ".join(bits) + "."


def build_dashboard(company_id: str) -> dict:
    m = ai.derive_metrics(company_id)

    lead = metrics.calc_lead_score(company_id)
    customer = metrics.calc_customer_health(company_id, m)
    growth_s = metrics.calc_growth_score(company_id, m)
    rev_opp = metrics.calc_revenue_opportunity(company_id, m)
    cac_ltv = metrics.calc_cac_ltv(company_id, m)

    recs = growth.generate_recommendations(company_id)["recommendations"]
    rec_tiles = [{
        "recommendation_id": r["recommendation_id"], "title": r["title"],
        "status": r["status"], "confidence": r["confidence"],
        "outcome_badge": "outcome logged" if r["outcome"] else "outcome pending",
    } for r in recs[:4]]

    alerts = _risk_alerts(company_id, m)

    tiles = [
        {"key": "business_health", "label": "Business Health", "kind": "score",
         "value": m["health"], "status": _score_status(m["health"]),
         "detail": "Composite of execution, readiness, retention and market."},

        {"key": "growth_score", "label": "Growth Score", "kind": "score",
         "value": growth_s["score"], "status": _score_status(growth_s["score"]),
         "detail": f"Inputs: {', '.join(growth_s['inputs_used']) or 'none'}."},

        {"key": "revenue_opportunity", "label": "Revenue Opportunity", "kind": "money",
         "value": rev_opp["amount"], "display": fmt_money(rev_opp["amount"]) if rev_opp["amount"] is not None else "—",
         "status": "ok" if rev_opp["amount"] is not None else "insufficient",
         "detail": rev_opp["detail"].get("basis", "Add revenue and churn to compute.")},

        {"key": "lead_score", "label": "Lead Score", "kind": "score",
         "value": lead["lead_score"], "status": _score_status(lead["lead_score"]),
         "detail": f"Inputs: {', '.join(lead['inputs_used']) or 'none'}."},

        {"key": "customer_health", "label": "Customer Health", "kind": "score",
         "value": customer["score"], "status": _score_status(customer["score"]),
         "detail": f"Churn {customer['detail'].get('churn_rate')}% · retention {customer['detail'].get('retention')}%"
                   if customer["score"] is not None else "Add retention or churn to compute."},

        {"key": "market_readiness", "label": "Market Readiness", "kind": "score",
         "value": m["market_position"], "status": _score_status(m["market_position"]),
         "detail": "Positioning strength from TAM and competitive signal."},

        {"key": "cac_ltv", "label": "CAC : LTV", "kind": "ratio",
         "value": cac_ltv["ratio"], "display": f"{cac_ltv['ratio']}:1" if cac_ltv["ratio"] is not None else "—",
         "status": ("ok" if cac_ltv["verdict"] == "healthy" else "warn") if cac_ltv["ratio"] is not None else "insufficient",
         "detail": (f"LTV {fmt_money(cac_ltv['ltv'])} vs CAC {fmt_money(cac_ltv['cac'])} — {cac_ltv['verdict']}."
                    if cac_ltv["ratio"] is not None else "Add CAC, revenue and churn to compute.")},

        {"key": "ai_recommendations", "label": "AI Recommendations", "kind": "list",
         "value": len(rec_tiles), "items": rec_tiles, "status": "ok" if rec_tiles else "insufficient",
         "detail": "Growth Agent plays, each tracked to an outcome." if rec_tiles else "No grounded plays yet."},

        {"key": "risk_alerts", "label": "Risk Alerts", "kind": "list",
         "value": len([a for a in alerts if a["severity"] != "low"]), "items": alerts,
         "status": "warn" if any(a["severity"] == "high" for a in alerts) else "ok",
         "detail": "Surfaced from memory and unit economics."},
    ]

    return {
        "tiles": tiles,
        "executive_summary": _executive_summary(company_id, m),
        "metrics": m,
        "generated_at": memory.now(),
    }
