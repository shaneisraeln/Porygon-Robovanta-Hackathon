"""Consolidated executive report → WhatsApp (via Twilio).

Pulls grounded facts from all five engine areas (Strategy, Marketing, Lead Gen,
Sales, Analytics), writes a plain-text WhatsApp-safe brief with the local LLM
(grounded, no invention), and sends it via Twilio. A heuristic builder produces
the same structure when no LLM is available.
"""
from __future__ import annotations

import re

import httpx

from . import ai, competitors, llm, memory, metrics
from .config import settings
from .engines import base
from .extract import fmt_money

REPORT_SYSTEM = (
    "You are a business reporting assistant preparing a single consolidated executive report for a "
    "founder/CEO, drawing on five areas of analysis: Strategy, Marketing, Lead Generation, Sales, and "
    "Analytics. The report will be delivered via WhatsApp.\n"
    "Rules:\n"
    "- Tone must be professional and neutral, like a business consultant's brief note. No exclamation "
    "marks, no casual language.\n"
    "- Do not use emojis under any circumstances.\n"
    "- Do not use markdown formatting (no asterisks, no '#' headers, no bullet symbols like '-' or '*'). "
    "WhatsApp does not render markdown reliably. Use plain sentences, capitalized section labels, and line "
    "breaks only.\n"
    "- Structure the report in this exact order, using these exact section labels followed by a colon, "
    "each on its own line before its content:\n"
    "  STRATEGY\n  MARKETING\n  LEAD GENERATION\n  SALES\n  ANALYTICS\n"
    "  For each section: 1-3 sentences maximum. State the key finding, then the recommended action. Skip a "
    "section's detail (write only 'No significant update.') if the input facts provide nothing meaningful "
    "for that area.\n"
    "- End with one final line labeled OVERALL PRIORITY: naming the single most important thing the founder "
    "should act on today, across all five areas.\n"
    "- Ground every statement strictly in the facts provided below. Never invent figures, competitor names, "
    "or outcomes not present in the input. If a section lacks enough data to say anything meaningful, state "
    "that plainly rather than guessing.\n"
    "- Do not include a preamble, sign-off, or any text outside the structured report itself."
)


def _facts_text(company_id: str) -> str:
    ctx = base.company_context(company_id)
    c, m, f = ctx["company"], ctx["metrics"], ctx["facts"]
    dm = memory.deal_metrics(company_id)
    lines = [f"COMPANY: {c['name']} — {c['what'] or 'unknown'} (stage: {c['stage'] or 'unknown'})",
             f"Customers served: {c['customers'] or 'unknown'}", ""]

    lines.append("METRICS:")
    for label, key in [("Revenue", "revenue"), ("Growth %/mo", "growth_pct"), ("Customers", "customers"),
                       ("Retention %", "retention_pct"), ("Churn %", "churn_pct"), ("Monthly burn", "monthly_burn"),
                       ("Runway months", "runway_months"), ("Lead score", "lead_score"),
                       ("CAC:LTV", "cac_ltv_ratio"), ("Business health", "health")]:
        v = m.get(key)
        if v is not None:
            lines.append(f"  {label}: {v}")

    lines.append("")
    lines.append("STRATEGY DATA:")
    strat = memory.latest_artifact(company_id, "engine_strategy")
    if strat and (strat["content"].get("positioning") or {}).get("statement"):
        lines.append(f"  Positioning: {strat['content']['positioning']['statement']}")
        if strat["content"].get("pricing"):
            lines.append(f"  Pricing rec: {strat['content']['pricing'].get('recommendation','')}")
    else:
        lines.append("  No strategy brief generated yet.")

    lines.append("MARKETING / LEAD DATA:")
    lines.append(f"  Lead source mix: {f['lead_source_mix'] or 'unknown'}")
    lines.append(f"  Lead conversion rate: {f['lead_conversion_rate'] or 'unknown'}")
    lines.append(f"  Acquisition channels: {f['acquisition_channels'] or 'unknown'}")

    lines.append("SALES PIPELINE:")
    if dm["total"]:
        lines.append(f"  Open deals: {dm['open']} (value {fmt_money(dm['open_value'])}), won: {dm['won']}, lost: {dm['lost']}, win rate: {dm['win_rate']}%")
    else:
        lines.append("  No deals in the pipeline.")

    if ctx["competitors"]:
        lines.append(f"COMPETITORS: {', '.join(ctx['competitors'][:5])}")
    if ctx["where_you_win"]:
        lines.append("WHERE YOU WIN: " + "; ".join(ctx["where_you_win"][:3]))
    if ctx["where_youre_exposed"]:
        lines.append("WHERE YOU'RE EXPOSED: " + "; ".join(ctx["where_youre_exposed"][:3]))
    if ctx["recent_outcomes"]:
        lines.append("RECENT OUTCOMES: " + "; ".join(ctx["recent_outcomes"]))
    return "\n".join(lines)


_EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U00002190-\U000021FF\U00002B00-\U00002BFF]", re.UNICODE)


def clean_whatsapp(text: str) -> str:
    """Enforce the WhatsApp rules: no markdown, no emojis, plain lines."""
    text = _EMOJI.sub("", text)
    text = text.replace("**", "").replace("*", "").replace("`", "").replace("#", "")
    out = []
    for ln in text.splitlines():
        ln = re.sub(r"^\s*[-•]\s+", "", ln)  # strip bullet symbols
        out.append(ln.rstrip())
    # collapse 3+ blank lines
    cleaned = "\n".join(out).strip()
    return re.sub(r"\n{3,}", "\n\n", cleaned)


def _heuristic(company_id: str) -> str:
    ctx = base.company_context(company_id)
    m = ctx["metrics"]
    dm = memory.deal_metrics(company_id)
    f = ctx["facts"]

    def line(label, content):
        return f"{label}:\n{content}"

    # STRATEGY
    strat = memory.latest_artifact(company_id, "engine_strategy")
    if strat and (strat["content"].get("positioning") or {}).get("statement"):
        strategy = f"{strat['content']['positioning']['statement']} Sharpen this in outbound and on the homepage."
    else:
        strategy = "No significant update."

    # MARKETING
    if f["lead_source_mix"] or f["acquisition_channels"]:
        src = f["lead_source_mix"] or f["acquisition_channels"]
        marketing = f"Current acquisition relies on {src}. Test one additional channel to reduce concentration."
    else:
        marketing = "No significant update."

    # LEAD GENERATION
    lead_bits = []
    if m.get("lead_score") is not None:
        lead_bits.append(f"Lead score is {round(m['lead_score'])}")
    if f["lead_conversion_rate"]:
        lead_bits.append(f"conversion at {f['lead_conversion_rate']}")
    leadgen = (". ".join(lead_bits) + ". Prioritise follow-up speed to lift conversion.") if lead_bits else "No significant update."

    # SALES
    if dm["total"]:
        sales = f"Pipeline holds {dm['open']} open deals worth {fmt_money(dm['open_value'])}"
        if dm["win_rate"] is not None:
            sales += f" at a {dm['win_rate']} percent win rate"
        sales += ". Focus on the deals sitting longest in stage."
    else:
        sales = "No significant update."

    # ANALYTICS
    an_bits = []
    if m.get("revenue") is not None:
        an_bits.append(f"revenue {fmt_money(m['revenue'])}")
    if m.get("growth_pct") is not None:
        an_bits.append(f"growth {m['growth_pct']} percent per month")
    if m.get("churn_pct") is not None:
        an_bits.append(f"churn {m['churn_pct']} percent")
    analytics = ("Current position: " + ", ".join(an_bits) + ". Monitor the trend monthly.") if an_bits else "No significant update."

    # OVERALL PRIORITY
    if m.get("churn_pct") is not None and m["churn_pct"] >= 8:
        priority = "Reduce churn before increasing spend, as retention is leaking revenue."
    elif dm.get("open"):
        priority = "Advance the highest-value open deals in the pipeline today."
    elif m.get("lead_score") is not None:
        priority = "Improve lead conversion, since traffic already exists."
    else:
        priority = "Complete onboarding data so the engines can produce grounded recommendations."

    return "\n\n".join([
        line("STRATEGY", strategy), line("MARKETING", marketing),
        line("LEAD GENERATION", leadgen), line("SALES", sales),
        line("ANALYTICS", analytics),
    ]) + f"\n\nOVERALL PRIORITY: {priority}"


def generate_report(company_id: str) -> str:
    text = None
    if llm.active():
        text = llm.complete(REPORT_SYSTEM, "FACTS:\n" + _facts_text(company_id), max_tokens=700)
    if not text or len(text.strip()) < 40:
        text = _heuristic(company_id)
    return clean_whatsapp(text)


def send_whatsapp(company_id: str, to: str) -> dict:
    report = generate_report(company_id)
    sid, tok = settings.twilio_account_sid, settings.twilio_auth_token
    if not (sid and tok):
        return {"sent": False, "error": "Twilio is not configured (missing SID/token).", "report": report}
    to_fmt = to.strip()
    if not to_fmt.startswith("whatsapp:"):
        to_fmt = f"whatsapp:{to_fmt}"
    try:
        r = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, tok),
            data={"From": settings.twilio_whatsapp_from, "To": to_fmt, "Body": report},
            timeout=30,
        )
        payload = r.json()
    except Exception as e:
        return {"sent": False, "error": str(e), "report": report}
    if r.status_code in (200, 201):
        return {"sent": True, "status": payload.get("status"), "sid": payload.get("sid"), "report": report}
    return {"sent": False, "error": payload.get("message", f"Twilio error {r.status_code}"), "report": report}
