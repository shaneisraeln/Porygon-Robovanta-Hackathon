"""Growth Agent (v2 core + v3 outcome-aware reasoning).

Generates ranked campaign and sales recommendations strictly from stored
product / customer / competitor / metric facts. Declines to recommend anything
unsupported by data. Each recommendation carries a persistent, deterministic
`recommendation_id` so it can be tracked through the Deliver -> Develop loop
(recommended -> in_progress -> completed -> measured), and generation pulls in
recent `campaign_outcome` facts so new advice explicitly reflects what worked.
"""
from __future__ import annotations

import hashlib
import json

from . import ai, memory, metrics, outcomes

REC_TYPE = "recommendation"


def _rid(company_id: str, slug: str) -> str:
    """Deterministic id — regeneration maps a candidate to its tracked state."""
    h = hashlib.md5(f"{company_id}:{slug}".encode()).hexdigest()[:10]
    return f"rec_{h}"


def _persist(company_id: str, rid: str, rec: dict) -> None:
    """Record the recommendation once so its lifecycle can be tracked by id."""
    for f in memory.list_facts(company_id):
        if f["type"] == REC_TYPE and f["key"] == rid:
            return
    memory.add_fact(
        company_id, REC_TYPE, rid, rec["title"], json.dumps(rec),
        source_ref="Growth Agent", source_kind="conversation",
        evidence=rec.get("rationale", ""), confidence=rec.get("confidence", 0.7) / 100, owner="system",
    )


def _candidates(company_id: str, m: dict, lead: dict) -> list[dict]:
    """Build data-grounded candidates. Empty when there's nothing to stand on."""
    g = memory.latest_num
    facts = memory.list_facts(company_id)

    retention = m.get("retention")
    growth = m.get("growth")
    customers = m.get("customers")
    revenue = m.get("revenue")
    conversion = g(company_id, "lead_conversion_rate")
    source_mix = next((f["value"] for f in facts if f["key"] == "lead_source_mix"), None)
    competitors = next((f["value"] for f in facts if f["key"] == "competitors"), None)

    out: list[dict] = []

    def rec(slug, category, title, detail, rationale, priority, confidence, evidence,
            playbook, impact, effort, timeframe):
        out.append({
            "slug": slug, "category": category, "title": title, "detail": detail,
            "rationale": rationale, "priority": priority, "confidence": confidence,
            "evidence": [e for e in evidence if e], "playbook": playbook,
            "expected_impact": impact, "effort": effort, "timeframe": timeframe,
        })

    # Retention / churn -> win-back or retention play.
    if retention is not None and retention < 90:
        rec("winback", "retention", "Launch a win-back campaign for at-risk accounts",
            "Segment the accounts driving churn and run a targeted win-back offer plus a check-in from the founder.",
            f"Retention is {metrics.clamp(retention)}% — below the 90% durability bar, so revenue is leaking before it compounds.",
            1, 80, [f"Retention {retention}%", f"{customers} customers" if customers is not None else ""],
            ["Pull the list of accounts that churned or went inactive in the last 90 days",
             "Segment by churn reason (price, activation, support)",
             "Draft a tailored win-back offer per segment",
             "Founder sends a personal check-in to the top 10 by value",
             "Track recovered accounts and log the outcome here"],
            f"Recover a share of the ~{metrics.clamp(100 - retention)}% leaking each period", "Medium", "2–4 weeks")

    # Weak lead conversion -> sales enablement play.
    if conversion is not None and conversion < 4:
        rec("conversion", "sales", "Tighten the lead-to-customer conversion path",
            "Instrument the funnel stage where leads stall, add a follow-up sequence, and qualify harder at the top.",
            f"Conversion is {conversion}% — a small lift here compounds across every lead you already generate.",
            2, 74, [f"Conversion {conversion}%"],
            ["Instrument each funnel stage to find where leads drop",
             "Add a 3-touch follow-up sequence for new leads",
             "Add a qualification checklist so reps focus on fit",
             "A/B test the highest-drop step",
             "Measure conversion lift and log the outcome"],
            f"Lifting conversion from {conversion}% toward 5–6% roughly adds customers without more leads",
            "Low", "2–3 weeks")

    # Single-channel dependency -> diversify acquisition.
    if source_mix and metrics._channel_count(source_mix) == 1:
        rec("diversify", "marketing", "Diversify lead acquisition beyond one channel",
            "Test a second acquisition channel (e.g. referral or outbound) before the current one saturates.",
            "All leads currently come from a single channel — that concentration is a growth and risk exposure.",
            2, 70, [f"Source mix: {source_mix}"],
            ["Pick one new channel to test (referral, outbound, or content)",
             "Set a small time-boxed budget and a target CPA",
             "Run a 2-week pilot with a single clear offer",
             "Compare CPA against your current channel",
             "Double down or kill based on the data"],
            "Reduces single-channel risk and opens a second growth lever", "Medium", "3–4 weeks")

    # Strong growth -> scale what works.
    if growth is not None and growth >= 10:
        rec("scale", "marketing", "Scale spend behind the channel that's working",
            "Reallocate budget toward the highest-performing channel and set a CAC guardrail as you scale.",
            f"Growth is compounding at {ai.numfmt(growth)}% MoM — press the advantage while the signal is strong.",
            3, 72, [f"Growth {growth}% MoM"],
            ["Rank channels by CAC and payback period",
             "Set a CAC guardrail you won't exceed",
             "Increase budget on the best channel in 20% steps",
             "Watch for CAC creep as you scale",
             "Log the outcome after one full cycle"],
            f"Compounds the current {ai.numfmt(growth)}% MoM without diluting efficiency", "Medium", "Ongoing")

    # Competitors on file -> positioning campaign.
    if competitors:
        rec("positioning", "marketing", "Run a positioning campaign against named competitors",
            "Build a comparison narrative around your defensible wedge and lead with it in outbound and content.",
            f"Competitors are on file ({competitors[:60]}) — a sharp positioning gap converts better than generic messaging.",
            3, 68, [f"Competitors: {competitors}"],
            ["Pull the Where-You-Win points from Competitor Analysis",
             "Write a one-line wedge that names the gap",
             "Build a comparison page and outbound snippet",
             "Run it in your top channel for 2 weeks",
             "Measure reply/convert lift and log the outcome"],
            "Sharper messaging typically lifts reply and conversion rates", "Low", "2 weeks")

    # Revenue with few customers -> expansion / upsell play.
    if revenue and customers is not None and customers < 50:
        rec("expansion", "sales", "Prioritize expansion revenue from existing accounts",
            "Map upsell/cross-sell paths in your best accounts; expansion is cheaper than net-new at this stage.",
            f"With {ai.numfmt(customers)} customers already paying, expanding them beats chasing volume right now.",
            2, 71, [f"{customers} customers", "Revenue on file"],
            ["Identify your 10 highest-usage accounts",
             "Map an upsell or cross-sell path for each",
             "Offer a scoped upgrade with clear added value",
             "Book expansion conversations with the top 5",
             "Track expansion revenue and log the outcome"],
            "Expansion revenue is cheaper than net-new acquisition", "Low", "3–4 weeks")

    return out


def _decorate(company_id: str, cand: dict) -> dict:
    rid = _rid(company_id, cand["slug"])
    rec = {
        "recommendation_id": rid,
        "category": cand["category"],
        "title": cand["title"],
        "detail": cand["detail"],
        "rationale": cand["rationale"],
        "priority": cand["priority"],
        "confidence": cand["confidence"],
        "evidence": cand["evidence"],
        "playbook": cand.get("playbook", []),
        "expected_impact": cand.get("expected_impact", ""),
        "effort": cand.get("effort", ""),
        "timeframe": cand.get("timeframe", ""),
    }
    _persist(company_id, rid, rec)

    rec["status"] = outcomes.get_status(company_id, rid)
    logged = outcomes.get_outcomes_for_recommendation(company_id, rid)
    rec["outcome"] = logged[0] if logged else None

    # Feedback loop: surface the last measured result for this recommendation.
    if rec["outcome"]:
        o = rec["outcome"]
        rec["learning"] = f"Last measured: {o['outcome_metric']} moved {o['baseline_value'] or '—'} → {o['outcome_value']}."
    else:
        rec["learning"] = None
    return rec


def generate_recommendations(company_id: str) -> dict:
    """Ranked, data-grounded recommendations with lifecycle + outcome state."""
    m = ai.derive_metrics(company_id)
    lead = metrics.calc_lead_score(company_id)
    recent = outcomes.get_recent_outcomes(company_id, limit=10)

    cands = _candidates(company_id, m, lead)
    if not cands:
        return {
            "recommendations": [],
            "lead_score": lead,
            "recent_outcomes": recent,
            "note": "Insufficient data to recommend a campaign or sales play yet. Add retention, lead, growth or competitor facts and I'll generate grounded recommendations.",
        }

    recs = [_decorate(company_id, c) for c in cands]
    recs.sort(key=lambda r: (r["priority"], -r["confidence"]))
    return {
        "recommendations": recs,
        "lead_score": lead,
        "recent_outcomes": recent,
        "note": "",
    }
