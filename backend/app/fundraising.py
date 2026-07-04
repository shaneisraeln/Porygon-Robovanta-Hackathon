"""Fundraising Operating System.

Turns the fundraising page into an execution pipeline: readiness analysis,
pitch-deck and financial-model generation (from Company Memory, versioned),
investor ranking, an outreach board, meeting prep, transcript intelligence, and
a data room. Every output is grounded in memory — no placeholder investors, no
fabricated workflow state.
"""
from __future__ import annotations

import re

from . import ai, llm, memory
from .extract import detect_firms, fmt_money, split_sentences

DECK_SLIDES = ["Title", "Problem", "Solution", "Product", "Market", "Traction", "Business Model", "Team", "The Ask"]


def _fact_value(company_id: str, key: str) -> str | None:
    for f in memory.list_facts(company_id):
        if f["key"] == key:
            return f["value"]
    return None


# ---------------- Readiness ----------------

def readiness(company_id: str) -> dict:
    m = ai.derive_metrics(company_id)
    missing_metrics = []
    for key, label in [("revenue", "Revenue / ARR"), ("growth", "Growth rate"), ("monthly_spend", "Burn"), ("cash", "Cash / runway"), ("retention", "Retention")]:
        if m.get(key) is None:
            missing_metrics.append(label)

    have_deck = memory.latest_artifact(company_id, "pitch_deck") is not None or _fact_value(company_id, "pitch_deck")
    have_model = memory.latest_artifact(company_id, "financial_model") is not None or _fact_value(company_id, "financials")
    have_dataroom = _fact_value(company_id, "data_room")
    have_captable = _fact_value(company_id, "cap_table")
    missing_docs = []
    if not have_deck:
        missing_docs.append("Pitch deck")
    if not have_model:
        missing_docs.append("Financial model")
    if not have_captable:
        missing_docs.append("Cap table")
    if not have_dataroom:
        missing_docs.append("Data room")

    metric_score = (5 - len(missing_metrics)) / 5 * 100
    doc_score = (4 - len(missing_docs)) / 4 * 100
    investors = memory.list_investors(company_id)
    pipeline_score = min(100, len(investors) * 20)
    score = round(0.45 * m["fundraising_readiness"] + 0.25 * metric_score + 0.15 * doc_score + 0.15 * pipeline_score)

    analysis = []
    analysis.append(f"Fundraising readiness model: {m['fundraising_readiness']}% on metrics, "
                    f"{len(investors)} investor relationship(s), {4 - len(missing_docs)}/4 core documents ready.")
    if missing_metrics:
        analysis.append("Capture these metrics to strengthen the story: " + ", ".join(missing_metrics) + ".")
    if missing_docs:
        analysis.append("Generate or upload: " + ", ".join(missing_docs) + ".")
    return {"score": score, "metrics": m, "missing_metrics": missing_metrics, "missing_docs": missing_docs, "analysis": " ".join(analysis)}


# ---------------- Pitch deck ----------------

def generate_pitch_deck(company_id: str) -> dict:
    co = memory.get_company(company_id)
    m = ai.derive_metrics(company_id)
    g = lambda k: _fact_value(company_id, k)

    slides = []

    def slide(title, bullets, missing=False):
        slides.append({"title": title, "bullets": [b for b in bullets if b], "needs_input": missing or not any(bullets)})

    slide("Title", [co["name"] if co else "", co.get("what") if co else "", co.get("stage") if co else ""])
    slide("Problem", [g("problem"), g("why_now")], missing=not g("problem"))
    slide("Solution", [co.get("what") if co else "", g("features")], missing=not (co and co.get("what")))
    slide("Product", [g("features"), g("progress"), g("website")])
    slide("Market", [f"Geography: {g('geography')}" if g("geography") else "", f"TAM: {fmt_money(m['tam'])}" if m["tam"] else "", f"Competitors: {g('competitors')}" if g("competitors") else ""], missing=not (g("geography") or m["tam"]))
    traction = []
    if m["revenue"]:
        traction.append(f"Revenue: {fmt_money(m['revenue'])}")
    if m["growth"] is not None:
        traction.append(f"Growth: {ai.numfmt(m['growth'])}% MoM")
    if m["customers"] is not None:
        traction.append(f"Customers: {ai.numfmt(m['customers'])}")
    if m["retention"] is not None:
        traction.append(f"Retention: {ai.numfmt(m['retention'])}%")
    slide("Traction", traction, missing=not traction)
    slide("Business Model", [g("business_model"), g("pricing")], missing=not g("business_model"))
    slide("Team", [f"{ai.numfmt(m['headcount'])} people" if m["headcount"] is not None else "", g("vision")], missing=m["headcount"] is None)
    ask = []
    if m["raise_target"]:
        ask.append(f"Raising {fmt_money(m['raise_target'])}")
    if g("round"):
        ask.append(f"Round: {g('round')}")
    if m["monthly_spend"]:
        ask.append(f"Use of funds: extend runway at {fmt_money(m['monthly_spend'])}/mo burn")
    slide("The Ask", ask, missing=not ask)

    # Optional LLM polish of bullets from the SAME grounded content.
    if llm.active():
        ctx = "\n".join(f"{s['title']}: {'; '.join(s['bullets'])}" for s in slides)
        out = llm.complete("You refine an investor pitch deck. Tighten each slide's bullets. Do not invent facts beyond the context.", ctx)
        if out:
            slides_meta = {"llm_refined": True}
        else:
            slides_meta = {}
    else:
        slides_meta = {}

    completeness = round(sum(0 if s["needs_input"] else 1 for s in slides) / len(slides) * 100)
    content = {"slides": slides, "completeness": completeness, **slides_meta}
    art = memory.save_artifact(company_id, "pitch_deck", f"{co['name']} pitch deck" if co else "Pitch deck", content)
    memory.add_timeline(company_id, connector_id="cbo", kind="Document", title=f"Pitch deck generated (v{art['version']})",
                        summary=f"{completeness}% complete from Company Memory.", why="Fundraising artifact generated",
                        evidence="", confidence=0.8, what_changed="Pitch deck available", agents=["fundraising"])
    return art


# ---------------- Financial model ----------------

def generate_financial_model(company_id: str) -> dict:
    m = ai.derive_metrics(company_id)
    monthly_rev = (m["revenue"] / 12) if m["revenue"] else 0.0
    growth = (m["growth"] or 0) / 100.0
    burn = m["monthly_spend"] or 0.0
    cash = m["cash"] if m.get("cash") else None
    months = []
    rev = monthly_rev
    bank = cash
    for i in range(1, 13):
        rev = rev * (1 + growth)
        net = rev - burn
        if bank is not None:
            bank += net
        months.append({"month": i, "revenue": round(rev), "burn": round(burn), "net": round(net), "cash": round(bank) if bank is not None else None})
    runway = None
    if cash and burn > monthly_rev:
        runway = round(cash / (burn - monthly_rev))
    content = {"assumptions": {"starting_mrr": round(monthly_rev), "growth_mom_pct": m["growth"], "burn": burn, "cash": cash},
               "projection": months, "runway_months": runway, "grounded": bool(m["revenue"] or burn)}
    art = memory.save_artifact(company_id, "financial_model", "12-month model", content)
    return art


# ---------------- Investor pipeline (ranked, from memory) ----------------

def investor_pipeline(company_id: str) -> dict:
    invs = memory.list_investors(company_id)
    co = memory.get_company(company_id)
    industry = (co.get("what", "") + " " + (_fact_value(company_id, "segment") or "")).lower() if co else ""
    ranked = []
    for inv in invs:
        fit = inv["probability"] * 0.5 + inv["warmth"] * 0.3
        state_bonus = {"likely": 20, "warm": 14, "viewed-deck": 8, "due-follow-up": 6, "need-intro": 2, "cooling": -10}.get(inv["state"], 0)
        sector_bonus = 8 if inv.get("sector") and inv["sector"].lower() in industry else 0
        score = round(min(100, fit + state_bonus + sector_bonus))
        reasons = [f"{ai.numfmt(inv['probability'])}% probability", f"warmth {ai.numfmt(inv['warmth'])}", ai.STATE_LABELS.get(inv["state"], inv["state"])]
        ranked.append({**inv, "fit_score": score, "fit_reasons": reasons})
    ranked.sort(key=lambda x: x["fit_score"], reverse=True)
    return {"investors": ranked, "note": "Ranked from Company Memory (onboarding, connected sources, documents). Connect Gmail/Crunchbase to discover net-new investors."}


# ---------------- Outreach board ----------------

def outreach_board(company_id: str) -> list[dict]:
    invs = memory.list_investors(company_id)
    rows = {o["investor_id"]: o for o in memory.list_outreach(company_id)}
    out = []
    for inv in invs:
        o = rows.get(inv["id"])
        out.append({"investor_id": inv["id"], "firm": inv["firm"], "name": inv["name"], "state": inv["state"],
                    "probability": round(inv["probability"]), "status": o["status"] if o else "not_started",
                    "subject": o["subject"] if o else "", "body": o["body"] if o else ""})
    order = {"not_started": 0, "drafted": 1, "approved": 2, "sent": 3, "replied": 4, "meeting": 5}
    out.sort(key=lambda r: order.get(r["status"], 0))
    return out


def draft_outreach(company_id: str, investor_id: str) -> dict:
    inv = memory.get_investor(company_id, investor_id)
    if not inv:
        return {"error": "not found"}
    body = ai.draft_followup(company_id, inv)
    co = memory.get_company(company_id)
    subject = f"{co['name'] if co else 'Our'} — quick intro" if inv["state"] == "need-intro" else f"{co['name'] if co else 'Our'} — update"
    memory.upsert_outreach(company_id, investor_id, subject, body, "drafted")
    return {"investor_id": investor_id, "subject": subject, "body": body, "status": "drafted"}


def send_outreach(company_id: str, investor_id: str) -> dict:
    o = memory.get_outreach(company_id, investor_id)
    if not o:
        return {"status": "no_draft", "message": "Draft the email first."}
    token = memory.get_credential(company_id, "gmail")
    if not token:
        return {"status": "needs_auth", "message": "Connect Gmail to send. CBO won't fake a send."}
    # A real send needs the investor's verified email address, which isn't in
    # memory yet — we don't fabricate delivery.
    return {"status": "needs_recipient", "message": "Add the investor's email to send via Gmail. Nothing is sent without a real recipient."}


# ---------------- Meeting transcript intelligence ----------------

def process_transcript(company_id: str, inv: dict, transcript: str) -> dict:
    sents = split_sentences(transcript)
    questions, concerns, risks, promises, followups = [], [], [], [], []
    for s in sents:
        low = s.lower()
        if s.strip().endswith("?") or low.startswith(("how", "what", "why", "when", "who", "can you", "do you")):
            questions.append(s)
        if re.search(r"concern|worried|not sure|hesitant|risk|too early|competitive", low):
            concerns.append(s)
        if re.search(r"risk|threat|burn|runway|churn|depend", low):
            risks.append(s)
        if re.search(r"we will|we'll|i'll send|we can|promise|commit|by next", low):
            promises.append(s)
        if re.search(r"follow up|send|share|intro|next step|circle back|schedule", low):
            followups.append(s)
    positive = re.search(r"excited|love|impressed|strong|great|interested|term sheet", transcript.lower())
    negative = re.search(r"pass|not a fit|too early|concerned|decline", transcript.lower())
    sentiment = "negative" if negative else "positive" if positive else "neutral"

    # Update memory.
    memory.add_fact(company_id, "meeting", "meeting_transcript", "Meeting transcript", transcript[:200],
                    source_ref=f"Transcript · {inv['firm']}", source_kind="document", evidence=transcript[:200], confidence=0.9, owner="founder")
    memory.add_investor_event(company_id, inv["firm"], f"Meeting: {sentiment} sentiment. {len(questions)} questions, {len(concerns)} concerns.", sentiment, "")
    memory.add_timeline(company_id, connector_id="meeting", kind="Meeting", title=f"Meeting transcript · {inv['firm']}",
                        summary=f"{len(questions)} questions, {len(promises)} promises, {len(followups)} follow-ups.", who=[inv["firm"]],
                        why="Live meeting intelligence", evidence=transcript[:160], confidence=0.85,
                        what_changed=f"Sentiment {sentiment}", agents=["meeting", "fundraising", "investor"])
    for c in concerns[:5]:
        existing = inv.get("concerns", [])
        if c not in existing:
            existing.append(c[:80])
        memory.update_investor(company_id, inv["id"], concerns=existing)

    follow_up_email = ai.draft_followup(company_id, memory.get_investor(company_id, inv["id"]))
    next_actions = [f"Send follow-up to {inv['firm']}"] + [f"Address: {c[:60]}" for c in concerns[:2]] + ([f"Deliver: {p[:60]}" for p in promises[:2]])
    return {"sentiment": sentiment, "questions": questions[:6], "concerns": concerns[:6], "risks": risks[:5],
            "promises": promises[:5], "follow_ups": followups[:5], "follow_up_email": follow_up_email, "next_actions": next_actions}


# ---------------- Data room ----------------

def data_room(company_id: str) -> dict:
    arts = {a["kind"]: a for a in memory.list_artifacts(company_id)}
    docs = memory.list_documents(company_id)
    doc_names = " ".join(d["name"].lower() for d in docs)
    items = [
        {"key": "pitch_deck", "label": "Pitch deck", "present": "pitch_deck" in arts or "deck" in doc_names},
        {"key": "financial_model", "label": "Financial model", "present": "financial_model" in arts or "financ" in doc_names or bool(_fact_value(company_id, "financials"))},
        {"key": "cap_table", "label": "Cap table", "present": bool(_fact_value(company_id, "cap_table")) or "cap table" in doc_names},
        {"key": "metrics", "label": "Metrics / KPIs", "present": ai.derive_metrics(company_id)["revenue"] is not None},
        {"key": "roadmap", "label": "Product roadmap", "present": "roadmap" in doc_names or bool(_fact_value(company_id, "features"))},
        {"key": "customers", "label": "Customer references", "present": ai.derive_metrics(company_id)["customers"] is not None},
    ]
    ready = round(sum(1 for i in items if i["present"]) / len(items) * 100)
    return {"items": items, "ready_pct": ready}


# ---------------- Pipeline status (the execution tracker) ----------------

def pipeline_status(company_id: str) -> dict:
    m = ai.derive_metrics(company_id)
    prof = _knowledge_conf(company_id)
    counts = memory.counts(company_id)
    invs = memory.list_investors(company_id)
    outreach = memory.list_outreach(company_id)
    deck = memory.latest_artifact(company_id, "pitch_deck")
    model = memory.latest_artifact(company_id, "financial_model")
    dr = data_room(company_id)
    has_debrief = any(f["key"] in ("meeting", "meeting_transcript") for f in memory.list_facts(company_id))

    def st(done, active=False):
        return "done" if done else ("active" if active else "todo")

    stages = [
        {"key": "understood", "label": "Company understood", "status": st(prof >= 60, prof > 0), "progress": prof, "action": "Continue the interview" if prof < 60 else "", "depends_on": []},
        {"key": "memory", "label": "Company memory built", "status": st(counts["facts"] >= 8, counts["facts"] > 0), "progress": min(100, counts["facts"] * 8), "action": "Connect sources / upload docs", "depends_on": ["understood"]},
        {"key": "deck", "label": "Pitch deck generated", "status": st(bool(deck), False), "progress": deck["content"]["completeness"] if deck else 0, "action": "Generate pitch deck", "depends_on": ["memory"]},
        {"key": "model", "label": "Financial model ready", "status": st(bool(model), False), "progress": 100 if model else 0, "action": "Generate financial model", "depends_on": ["memory"]},
        {"key": "dataroom", "label": "Data room ready", "status": st(dr["ready_pct"] >= 80, dr["ready_pct"] > 0), "progress": dr["ready_pct"], "action": "Complete the data room", "depends_on": ["deck", "model"]},
        {"key": "discovered", "label": "Investors discovered", "status": st(len(invs) > 0), "progress": min(100, len(invs) * 20), "action": "Add investors / connect Gmail", "depends_on": ["memory"]},
        {"key": "ranked", "label": "Investors ranked", "status": st(len(invs) > 0), "progress": 100 if invs else 0, "action": "", "depends_on": ["discovered"]},
        {"key": "warm", "label": "Warm intros found", "status": st(any(i["state"] in ("warm", "likely") for i in invs), bool(invs)), "progress": round(sum(1 for i in invs if i["state"] in ("warm", "likely")) / len(invs) * 100) if invs else 0, "action": "Nurture relationships", "depends_on": ["ranked"]},
        {"key": "drafted", "label": "Outreach drafted", "status": st(len(outreach) > 0), "progress": round(len(outreach) / len(invs) * 100) if invs else 0, "action": "Draft outreach", "depends_on": ["ranked"]},
        {"key": "approved", "label": "Founder approved emails", "status": st(any(o["status"] in ("approved", "sent") for o in outreach)), "progress": round(sum(1 for o in outreach if o["status"] in ("approved", "sent")) / len(outreach) * 100) if outreach else 0, "action": "Review & approve drafts", "depends_on": ["drafted"]},
        {"key": "sent", "label": "Emails sent", "status": st(any(o["status"] == "sent" for o in outreach)), "progress": 0, "action": "Connect Gmail to send", "depends_on": ["approved"]},
        {"key": "meetings", "label": "Meetings booked", "status": st(any(i["state"] == "warm" for i in invs)), "progress": 0, "action": "Book from replies", "depends_on": ["sent"]},
        {"key": "prepared", "label": "Founder prepared", "status": st(any(i["state"] in ("warm", "likely") for i in invs)), "progress": 0, "action": "Open meeting prep", "depends_on": ["meetings"]},
        {"key": "completed", "label": "Meeting completed", "status": st(has_debrief), "progress": 100 if has_debrief else 0, "action": "Import transcript", "depends_on": ["prepared"]},
        {"key": "followup", "label": "Follow-up sent", "status": st(has_debrief), "progress": 0, "action": "Send follow-up", "depends_on": ["completed"]},
        {"key": "diligence", "label": "Due diligence", "status": st(dr["ready_pct"] >= 80), "progress": dr["ready_pct"], "action": "Maintain the data room", "depends_on": ["dataroom", "completed"]},
        {"key": "term_sheet", "label": "Term sheet", "status": "todo", "progress": 0, "action": "Negotiate", "depends_on": ["diligence"]},
        {"key": "closed", "label": "Round closed", "status": "todo", "progress": 0, "action": "Sign & wire", "depends_on": ["term_sheet"]},
    ]
    done = sum(1 for s in stages if s["status"] == "done")
    return {"stages": stages, "overall_pct": round(done / len(stages) * 100), "done": done, "total": len(stages)}


def _knowledge_conf(company_id: str) -> int:
    from . import interview
    return interview.profile(company_id)["knowledge_confidence"]
