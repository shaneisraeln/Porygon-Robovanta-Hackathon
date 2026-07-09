"""Customer Success Engine — CRM, support tickets, grounded AI chatbot, and a
health/triage brief."""
from __future__ import annotations

from .. import ai, llm, memory, metrics
from . import base

TICKET_TYPE = "ticket"
KIND = "engine_success"

_SYSTEM = (
    "You are a customer success lead for a small business. You triage support tickets, assess account "
    "health, and draft helpful, on-brand replies grounded ONLY in the company's known information.\n"
    "Rules:\n"
    "- Draft replies using ONLY facts in the knowledge base; if the answer isn't known, say you'll follow "
    "up rather than inventing details.\n"
    "- Flag at-risk customers based on churn/health signals in the data; if there's no signal, don't guess.\n"
    "- Prioritize open tickets by urgency.\n"
    "- Tone: warm, clear, human — never robotic or corporate.\n"
    "Return valid JSON only, matching this schema:\n"
    '{"health_read": {"summary": str, "at_risk_signals": [str], "confidence": "high|medium|low"},'
    ' "ticket_triage": [{"subject": str, "priority": "high|medium|low", "suggested_reply": str}],'
    ' "retention_actions": [str], "insufficient_data_flags": [str]}'
)


def _brief_context(company_id: str) -> str:
    ov = overview(company_id)
    co = memory.get_company(company_id) or {}
    lines = [f"Company: {co.get('name')} — {co.get('what')}",
             f"Customer health score: {ov['customer_health']}", f"Churn: {ov['churn_pct']}%",
             f"Customers on file: {len(ov['customers'])} | open tickets: {ov['open_tickets']}"]
    if ov["tickets"]:
        lines.append("Open tickets:")
        for t in ov["tickets"][:8]:
            lines.append(f"  - {t['subject']}: {t['body'][:120]}")
    else:
        lines.append("No support tickets on file.")
    return "\n".join(lines)


def _brief_heuristic(company_id: str, ctx: dict) -> dict:
    ov = overview(company_id)
    flags, at_risk = [], []
    health = ov["customer_health"]
    churn = ov["churn_pct"]
    if health is None and churn is None:
        flags.append("No retention/churn data — add it to assess health.")
    if churn is not None and churn >= 8:
        at_risk.append(f"Churn is {churn}% — above a healthy threshold.")
    summary = (f"Health {round(health)}/100." if health is not None else "Health unknown.") + (f" Churn {churn}%." if churn is not None else "")
    triage = [{"subject": t["subject"], "priority": "high",
               "suggested_reply": "Thanks for flagging this — we're on it and will follow up shortly."} for t in ov["tickets"][:5]]
    actions = ["Check in with your top accounts personally",
               "Turn repeat questions into FAQ/help docs (teach the chatbot)"]
    if churn is not None and churn >= 8:
        actions.insert(0, "Run a win-back on recently churned accounts")
    return {"health_read": {"summary": summary or "Add customer data for a fuller read.", "at_risk_signals": at_risk,
                            "confidence": "medium" if (health is not None or churn is not None) else "low"},
            "ticket_triage": triage, "retention_actions": actions, "insufficient_data_flags": flags}


def generate(company_id: str) -> dict:
    return base.run_engine(company_id, KIND, "Customer success brief", _SYSTEM, {},
                           _brief_heuristic, ctx_text=_brief_context(company_id))


def latest(company_id: str) -> dict | None:
    return base.load_or_note(company_id, KIND)


def overview(company_id: str) -> dict:
    """Simple CRM + support snapshot from Company Memory."""
    g = memory.graph(company_id)
    crm = []
    for e in g["entities"]:
        if e["type"] != "customer":
            continue
        facts = memory.facts_for_entity(company_id, e["id"])
        crm.append({"id": e["id"], "name": e["name"],
                    "notes": [f"{f['label']}: {f['value']}" for f in facts][:3]})

    tickets = [_ticket(f) for f in memory.list_facts(company_id) if f["type"] == TICKET_TYPE]

    m = ai.derive_metrics(company_id)
    health = metrics.calc_customer_health(company_id, m)
    churn = metrics.calc_churn(company_id)["churn_rate"]
    return {
        "customers": crm,
        "tickets": tickets,
        "customer_health": health.get("score"),
        "churn_pct": churn,
        "open_tickets": len([t for t in tickets if t["status"] == "open"]),
    }


def _ticket(f: dict) -> dict:
    return {"id": f["id"], "subject": f["label"].replace("Ticket: ", ""),
            "body": f["value"], "at": f["created_at"], "status": "open"}


def add_ticket(company_id: str, subject: str, body: str) -> dict:
    memory.add_fact(company_id, TICKET_TYPE, "ticket", f"Ticket: {subject[:60]}", body[:400],
                    source_ref="Support portal", source_kind="conversation",
                    evidence=body[:160], confidence=0.9, owner="founder")
    memory.add_timeline(company_id, connector_id="support", kind="Ticket", title=f"Support ticket: {subject[:60]}",
                        summary=body[:160], why="Customer raised an issue", evidence=body[:160],
                        confidence=0.9, what_changed="New support ticket", agents=["customer"])
    # A grounded suggested reply (only from company memory; says I-don't-know otherwise).
    suggested = ai.brain_ask(company_id, f"{subject}. {body}")
    return {"subject": subject, "suggested_reply": suggested["answer"],
            "confidence": suggested["confidence"], "sources": suggested["sources"]}


def chat(company_id: str, message: str) -> dict:
    """Support chatbot: grounded RAG over Company Memory (fast local model)."""
    result = ai.brain_ask(company_id, message)
    return {"answer": result["answer"], "confidence": result["confidence"],
            "sources": result["sources"], "grounded": True}


def faqs(company_id: str) -> list[dict]:
    """Fast starter FAQs from memory (kept LLM-free so the overview loads quickly).

    Use `generate_faqs()` for AI-written FAQs on explicit demand."""
    co = memory.get_company(company_id) or {}
    saved = memory.latest_artifact(company_id, "support_faq")
    if saved and saved["content"].get("faqs"):
        return saved["content"]["faqs"]

    def fact(key: str) -> str:
        for f in memory.list_facts(company_id):
            if f["key"] == key and f["value"]:
                return f["value"]
        return ""

    return [
        {"q": "What do you offer?", "a": co.get("what") or "Add your product description in onboarding."},
        {"q": "How do I get started?", "a": "Sign up and we'll help you onboard step by step."},
        {"q": "How much does it cost?", "a": fact("pricing") or "See our pricing — reach out for a tailored quote."},
        {"q": "How can I get support?", "a": "Message us here in the support desk and we'll respond quickly."},
    ]


def generate_faqs(company_id: str) -> list[dict]:
    """AI-written FAQs (explicit, on-demand). Cached as an artifact."""
    co = memory.get_company(company_id) or {}
    if llm.active() and co.get("what"):
        from .base import parse_json
        raw = llm.complete(
            "You write a customer support FAQ. Using ONLY this company description, write 4 likely "
            "customer questions and short answers. Return JSON: [{\"q\":..., \"a\":...}]. No prose.",
            f"Company: {co.get('name')}. What: {co.get('what')}. Customers: {co.get('customers')}.",
            max_tokens=500,
        )
        parsed = parse_json(raw)
        if isinstance(parsed, list) and parsed:
            items = [{"q": str(x.get("q", "")), "a": str(x.get("a", ""))} for x in parsed if x.get("q")][:6]
            memory.save_artifact(company_id, "support_faq", "Support FAQ", {"faqs": items})
            return items
    return faqs(company_id)
