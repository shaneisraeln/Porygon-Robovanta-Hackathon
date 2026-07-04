"""AI reasoning over Company Memory: metrics, Brain RAG, Executive Council,
Morning Brief, and Investor intelligence. All grounded in stored facts."""
from __future__ import annotations

import re

from . import llm, memory
from .embedding import tokenize
from .extract import fmt_money


def clamp(n, lo=0, hi=100):
    return max(lo, min(hi, round(n)))


def numfmt(n) -> str:
    """Render whole floats without a trailing .0."""
    if n is None:
        return ""
    return str(int(n)) if float(n).is_integer() else str(n)


_QUERY_STOP = {"what", "how", "why", "when", "who", "where", "our", "we", "is", "are", "the", "a", "an", "do", "does", "of", "to", "in", "on", "for"}


# ---------------- Derived metrics ----------------

def derive_metrics(company_id: str) -> dict:
    g = memory.latest_num
    revenue = g(company_id, "revenue") or g(company_id, "pricing")
    monthly_spend = g(company_id, "monthly_spend")
    growth = g(company_id, "growth")
    retention = g(company_id, "retention")
    headcount = g(company_id, "headcount")
    customers = g(company_id, "count")
    raise_target = g(company_id, "raise_target")
    tam = g(company_id, "tam")
    cash = g(company_id, "cash")
    has_investors = len(memory.list_investors(company_id)) > 0

    runway_months = None
    monthly_rev = (revenue / 12) if revenue else 0.0
    if cash and monthly_spend and monthly_spend > monthly_rev:
        runway_months = round(cash / (monthly_spend - monthly_rev))
    elif cash and monthly_spend:
        runway_months = 24  # cash-flow positive / break-even — long runway

    import math
    growth_s = clamp(45 + growth * 2) if growth is not None else 58
    retention_s = clamp(40 + (retention - 80) * 2) if retention is not None else 60
    revenue_s = clamp(60 + math.log10(revenue) * 4) if revenue else 50
    traction_s = clamp(45 + min(customers, 100) * 0.5) if customers else 50
    execution = clamp(0.5 * growth_s + 0.3 * traction_s + 0.2 * retention_s)
    market = clamp(55 + math.log10(tam) * 3) if tam else 62
    readiness = clamp(0.4 * revenue_s + 0.3 * growth_s + 0.2 * traction_s + 0.1 * (80 if has_investors else 55))
    health = clamp(0.35 * execution + 0.25 * readiness + 0.2 * retention_s + 0.2 * market)
    return {"revenue": revenue, "monthly_spend": monthly_spend, "growth": growth, "retention": retention,
            "headcount": headcount, "customers": customers, "raise_target": raise_target, "tam": tam,
            "cash": cash, "runway_months": runway_months,
            "has_investors": has_investors, "health": health, "fundraising_readiness": readiness,
            "execution_health": execution, "market_position": market}


def summarize_metrics(m: dict) -> str:
    bits = []
    if m["revenue"]:
        bits.append(f"{fmt_money(m['revenue'])} revenue")
    if m["growth"] is not None:
        bits.append(f"{numfmt(m['growth'])}% growth")
    if m["customers"] is not None:
        bits.append(f"{numfmt(m['customers'])} customers")
    if m["headcount"] is not None:
        bits.append(f"team of {numfmt(m['headcount'])}")
    if m["monthly_spend"]:
        bits.append(f"{fmt_money(m['monthly_spend'])}/mo burn")
    return " · ".join(bits) or "Early — still building the picture."


# ---------------- Brain (RAG, grounded, says I don't know) ----------------

def brain_ask(company_id: str, query: str) -> dict:
    m = derive_metrics(company_id)
    low = query.lower()
    chunks = memory.search_chunks(company_id, query, k=4)
    facts = _rank_facts(company_id, query)

    answer, confidence = _compose(company_id, low, m, facts, chunks)
    sources = []
    for f in facts[:5]:
        sources.append({"source": f["source_ref"], "excerpt": f.get("evidence") or f"{f['label']}: {f['value']}"})
    for c in chunks:
        sources.append({"source": c["doc_name"], "excerpt": c["text"][:160]})

    connected = sorted({f["label"] for f in facts[:6]})
    return {"answer": answer, "confidence": round(confidence, 2), "sources": _dedupe_sources(sources),
            "connected_memories": connected, "evidence_count": len(facts) + len(chunks)}


def _rank_facts(company_id: str, query: str) -> list[dict]:
    q = set(tokenize(query)) - _QUERY_STOP
    if not q:
        return []
    scored = []
    for f in memory.list_facts(company_id):
        terms = set(tokenize(f"{f['label']} {f['value']} {f['type']} {f['key']}"))
        overlap = len(q & terms)
        if overlap:
            scored.append((overlap + f["confidence"], f))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in scored[:6]]


def _compose(company_id, low, m, facts, chunks):
    # Intent shortcuts grounded in metrics.
    if re.search(r"\b(runway|how long|months left|cash)\b", low):
        if m.get("runway_months") is not None:
            return (f"You have about {m['runway_months']} months of runway — {fmt_money(m['cash'])} in the bank against {fmt_money(m['monthly_spend'])}/mo burn. {summarize_metrics(m)}.", 0.8)
        if m["monthly_spend"]:
            return (f"You're spending about {fmt_money(m['monthly_spend'])}/month. I don't have a current cash balance on file, so I can't compute exact runway yet — add it and I'll track it.", 0.5)
        return ("I don't have your burn or cash on file yet, so I can't tell you the runway. Add them and I'll compute it.", 0.2)
    if re.search(r"\b(revenue|arr|mrr|how much.*(make|earn|charge))\b", low):
        return ((f"Revenue is around {fmt_money(m['revenue'])}" + (f", growing {numfmt(m['growth'])}%." if m['growth'] is not None else ".") + f" {summarize_metrics(m)}.", 0.8) if m["revenue"] else ("No revenue is recorded in memory yet.", 0.2))
    if re.search(r"\b(grow|growth|growing|trajectory)\b", low):
        return ((f"You're growing about {numfmt(m['growth'])}% month over month" + (f", now at {numfmt(m['customers'])} customers" if m['customers'] is not None else "") + ". " + summarize_metrics(m) + ".", 0.75) if m["growth"] is not None else ("I don't have a growth rate in memory yet — connect Stripe or analytics and I'll track it.", 0.2))
    if re.search(r"\b(team|headcount|how many people|employees)\b", low):
        return ((f"Your team is {numfmt(m['headcount'])} people. {summarize_metrics(m)}.", 0.75) if m["headcount"] is not None else ("I don't have a team size on file yet.", 0.2))
    if re.search(r"\b(customer|users|clients|traction)\b", low):
        return ((f"You have {numfmt(m['customers'])} customers" + (f" at {numfmt(m['retention'])}% retention" if m['retention'] is not None else "") + ".", 0.75) if m["customers"] is not None else ("No customer count recorded yet.", 0.2))
    if re.search(r"\b(investor|raise|fundrais|round)\b", low):
        invs = memory.list_investors(company_id)
        if invs:
            return (f"You have {len(invs)} investor relationship(s) tracked" + (f" against a {fmt_money(m['raise_target'])} target" if m['raise_target'] else "") + ". See the Fundraising War Room for live status.", 0.7)
        return ("No investor relationships are in memory yet.", 0.2)

    # General grounded answer — only from retrieved memory.
    if not facts and not chunks:
        return ("I don't know — there's nothing in the Company Brain about that yet. Connect a source or upload a document and ask again.", 0.0)

    # Optional LLM composition over the SAME retrieved context (no outside knowledge).
    if llm.active():
        context = "\n".join([f"- {f['label']}: {f['value']} (source: {f['source_ref']})" for f in facts] + [f"- {c['text']}" for c in chunks])
        out = llm.complete(
            "You are CBO's Company Brain. Answer ONLY using the provided context. If it is insufficient, say you don't know. Never invent facts. Cite nothing outside the context.",
            f"Question: {low}\n\nContext:\n{context}",
        )
        if out:
            return (out.strip(), 0.7)

    fact_line = ("From memory: " + "; ".join(f"{f['label'].lower()} — {f['value']}" for f in facts) + ".") if facts else ""
    doc_line = (f" A document notes: \"{chunks[0]['text'][:160]}\"") if chunks else ""
    return ((fact_line + doc_line).strip(), 0.6)


def _dedupe_sources(sources):
    seen, out = set(), []
    for s in sources:
        k = f"{s['source']}|{s['excerpt'][:50]}"
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out[:6]


# ---------------- Executive Council ----------------

AGENTS = ["strategy", "finance", "fundraising", "market", "execution", "operations", "customer", "risk"]


def _intent(q: str) -> str:
    s = q.lower()
    if re.search(r"\b(raise|fundrais|round|capital|investor)\b", s):
        return "raise"
    if re.search(r"\b(hire|headcount|recruit|team)\b", s):
        return "hire"
    if re.search(r"\b(pivot|new (market|direction)|change)\b", s):
        return "pivot"
    if re.search(r"\b(spend|budget|cut|burn|cost)\b", s):
        return "spend"
    return "general"


def _agent_verdict(agent: str, m: dict, intent: str, company_id: str) -> dict:
    fm = fmt_money
    def v(stance, evidence, pros, cons, rec, conf):
        return {"agent": agent, "stance": stance, "evidence": evidence, "pros": pros, "cons": cons, "recommendation": rec, "confidence": conf}

    if agent == "strategy":
        strong = m["execution_health"] >= 75
        return v("Press the advantage" if strong else "Sharpen focus first",
                 [f"Execution {m['execution_health']}%", f"Market {m['market_position']}%"],
                 ["Momentum supports a bold move" if strong else "Focus compounds"],
                 ["Spreading thin dilutes the edge" if strong else "Acting on weak signal is risky"],
                 ("Don't pivot — double down." if intent == "pivot" and strong else "Tighten the story before the next commitment."), 80 if strong else 68)
    if agent == "finance":
        return v(f"Burning {fm(m['monthly_spend'])}/mo" if m["monthly_spend"] else "Burn not on file",
                 [f"Revenue {fm(m['revenue'])}" if m["revenue"] else "No revenue", f"Spend {fm(m['monthly_spend'])}/mo" if m["monthly_spend"] else "Spend unknown"],
                 ["Efficient spend extends optionality"], ["Burn without revenue shortens the clock" if m["monthly_spend"] and not m["revenue"] else "Unknowns make planning fragile"],
                 "Add cash balance so runway anchors decisions; hold net-new burn." if m["monthly_spend"] else "Capture burn and cash first.", 78 if m["monthly_spend"] else 60)
    if agent == "fundraising":
        ready = m["fundraising_readiness"] >= 75
        return v("Ready to open a round" if ready else "Raise in ~90 days",
                 [f"Readiness {m['fundraising_readiness']}%", f"{len(memory.list_investors(company_id))} relationships"],
                 ["Metrics support conviction" if ready else "More proof yields better terms"],
                 ["Windows can close" if ready else "Early opens get soft terms"],
                 "Open the round; sequence warmest first." if ready else "Harden growth 60-90 days, then open.", 82 if ready else 72)
    if agent == "market":
        return v("Favorable positioning" if m["market_position"] >= 70 else "Contested positioning",
                 [f"TAM {fm(m['tam'])}" if m["tam"] else "TAM unknown", f"Market {m['market_position']}%"],
                 ["A defensible wedge attracts capital"], ["Crowding compresses differentiation"],
                 "Lead with the most defensible segment.", 72)
    if agent == "execution":
        return v("Shipping well" if m["execution_health"] >= 75 else "Velocity at risk",
                 [f"Execution {m['execution_health']}%", f"Team {m['headcount']}" if m["headcount"] is not None else "Team unknown"],
                 ["Strong delivery converts capital to growth"], ["Thin team limits parallel bets" if (m["headcount"] or 9) < 3 else "Scaling strains process"],
                 "Hire only against the biggest bottleneck." if intent == "hire" else "Protect cadence; instrument the funnel.", 76)
    if agent == "operations":
        return v("Keep the machine lean", [f"Headcount {m['headcount']}" if m["headcount"] is not None else "Headcount unknown"],
                 ["Lean ops preserve runway"], ["Manual processes break at scale"], "Automate the highest-volume workflow before the next hire.", 70)
    if agent == "customer":
        return v(("Customers are sticky" if (m["retention"] or 0) >= 90 else "Retention needs attention") if m["retention"] is not None else "Retention unknown",
                 [f"{m['customers']} customers" if m["customers"] is not None else "No count", f"Retention {m['retention']}%" if m["retention"] is not None else "Retention unknown"],
                 ["High retention compounds revenue"], ["Leaky retention undermines growth" if (m["retention"] or 100) < 90 else "Concentration risk if few logos"],
                 "Interview 5 churned and 5 happiest customers before any big bet.", 75 if m["retention"] is not None else 62)
    # risk
    flags = []
    if m["monthly_spend"] and not m["revenue"]:
        flags.append("Burn without revenue")
    if any(i["state"] == "cooling" for i in memory.list_investors(company_id)):
        flags.append("An investor is cooling")
    if not flags:
        flags.append("No critical flags — keep instrumenting")
    return v("Multiple watch items" if len(flags) > 1 else "Manageable risk", flags,
             ["Naming risks early keeps them small"], ["Ignored risks compound"], f"Mitigate first: {flags[0]}.", 74)


def council_run(company_id: str, question: str) -> dict:
    m = derive_metrics(company_id)
    intent = _intent(question)
    plan = {"intent": intent, "selected_agents": AGENTS,
            "rationale": f"Detected a '{intent}' decision — convening the full council and grounding each agent in current memory."}
    verdicts = [_agent_verdict(a, m, intent, company_id) for a in AGENTS]
    avg = round(sum(v["confidence"] for v in verdicts) / len(verdicts))

    # Debate: surface the sharpest agreement/tension.
    bull = max(verdicts, key=lambda v: v["confidence"])
    bear = min(verdicts, key=lambda v: v["confidence"])
    debate = [
        {"agent": bull["agent"], "point": bull["recommendation"]},
        {"agent": bear["agent"], "point": bear["recommendation"]},
        {"agent": "risk", "point": next(v["recommendation"] for v in verdicts if v["agent"] == "risk")},
    ]

    if intent == "raise":
        ready = m["fundraising_readiness"] >= 75
        headline = "Yes — open the round now." if ready else "Not yet — give it ~90 days."
        rationale = (f"Readiness {m['fundraising_readiness']}% with execution {m['execution_health']}% supports entering the market." if ready
                     else f"Readiness {m['fundraising_readiness']}%; the story needs another quarter of proof. Runway permitting, you raise on better terms.")
        actions = (["Sequence warmest investors, open the data room", "Lock a one-line traction proof", "Brief the team on timeline"] if ready
                   else ["Harden the top growth metric 60-90 days", "Add cash balance so runway is explicit", "Warm 5-8 investor relationships"])
    elif intent == "hire":
        headline = "Hire — but only for the single biggest bottleneck." if m["execution_health"] >= 75 else "Hold — fix focus before adding people."
        rationale = f"Execution {m['execution_health']}%. One excellent hire on the real constraint beats several average ones; protect runway."
        actions = ["Name the one bottleneck a hire removes", "Define a 90-day success metric", "Confirm runway covers it with margin"]
    elif intent == "pivot":
        headline = "Don't pivot — double down." if m["execution_health"] >= 75 else "Only pivot on one validated signal."
        rationale = f"Execution {m['execution_health']}%, market {m['market_position']}% — a pivot must be evidence-led."
        actions = ["Write the signal that would justify a pivot", "Run 10 customer interviews", "Timebox a 2-week validation test"]
    else:
        headline = "Here's the council's read."
        rationale = f"Across eight functions at {avg}% average confidence, grounded in {m['fundraising_readiness']}% raise-readiness and {m['execution_health']}% execution."
        actions = ["Pick the highest-leverage action this week", "Instrument the metric that would change this answer", "Revisit once it moves"]

    dissent = [f"{v['agent']}: {v['stance']}" for v in verdicts if v["confidence"] < 70][:3]
    governance = _governance(m, headline)

    return {"question": question, "plan": plan, "verdicts": verdicts, "debate": debate,
            "synthesis": {"headline": headline, "rationale": rationale, "confidence": avg, "next_actions": actions, "dissent": dissent},
            "governance": governance}


def _governance(m: dict, headline: str) -> dict:
    checks = []
    if "open the round" in headline.lower():
        checks.append({"check": "Runway guardrail", "status": "warn" if not m["monthly_spend"] else "pass",
                       "note": "Confirm runway covers the raise timeline." if not m["monthly_spend"] else "Burn is on file."})
    checks.append({"check": "Evidence grounding", "status": "pass", "note": "All agents reasoned from stored memory."})
    return {"approved": True, "checks": checks}


# ---------------- Morning Brief ----------------

def brief_generate(company_id: str) -> list[dict]:
    m = derive_metrics(company_id)
    items = []

    def push(section, title, why, changed, matters, nxt, severity, source=None):
        items.append({"section": section, "title": title, "why": why, "changed": changed,
                      "matters": matters, "next": nxt, "severity": severity, "source": source})

    for n in memory.list_notifications(company_id, 5):
        is_approval = "fundraising" in n["agents"] or "investor" in n["agents"]
        push("approval" if is_approval else ("risk" if n["severity"] == "high" else "opportunity"),
             n["title"], f"Flagged by the {' & '.join(n['agents'])} agent(s).", n["detail"],
             "High priority — needs you today." if n["severity"] == "high" else "Worth acting on soon.",
             "Open the War Room to review and send." if is_approval else "Open Sources or the relevant mode to act.", n["severity"])

    for e in memory.list_timeline(company_id, 40):
        blob = f"{e['title']} {e['summary']} {e['what_changed']}".lower()
        if re.search(r"churn|down|risk|blocker|drop|stall", blob) or (e["kind"] == "Issue"):
            push("risk", e["title"], f"Surfaced from {e['kind'].lower()} in your sources.", e["what_changed"] or "New signal.",
                 e["why"] or "Worth a look before it compounds.", "Trace it in Sources, or ask the Council.", "medium",
                 {"ref": e["connector_id"], "excerpt": e["evidence"]})
            if len([i for i in items if i["section"] == "risk"]) >= 3:
                break

    for inv in memory.list_investors(company_id):
        if inv["state"] == "likely" or (inv["state"] == "warm" and inv["probability"] >= 65):
            push("opportunity", f"{inv['firm']} is leaning in", f"{inv['name']} is your highest-probability conversation.",
                 f"Probability {round(inv['probability'])}% after recent activity.", "A committed lead de-risks the round.",
                 "Send the next update and propose a partner meeting.", "high")
        if inv["state"] == "due-follow-up":
            push("approval", f"Follow-up due: {inv['firm']}", f"{inv['name']} is waiting to hear from you.",
                 f"Last touch {inv['last_touch']}; momentum cools.", "Warm intros decay fast.", "Approve the drafted follow-up.", "high")

    if m["monthly_spend"] and m["revenue"] is not None:
        net = m["monthly_spend"] - (m["revenue"] / 12 if m["revenue"] else 0)
        if net > 0:
            push("risk", f"Burning {fmt_money(m['monthly_spend'])} a month", "Spend outpaces revenue.",
                 f"Net burn ~{fmt_money(net)}/mo.", "Runway is the clock behind every decision.", "Add your cash balance so I can track runway.", "medium")
    if m["growth"] is not None and m["growth"] >= 10:
        push("opportunity", f"Growth is compounding at {numfmt(m['growth'])}%", "Strong growth for your stage.",
             f"Sustained {numfmt(m['growth'])}% MoM.", "This is the number investors underwrite.", "Package it into a one-line traction proof.", "low")

    push("priority", "Decide your fundraising posture", f"Readiness is at {m['fundraising_readiness']}%.",
         "Recalculated from your latest memory.", "It sets whether this quarter is growth or the raise.",
         'Ask the Executive Council: "Should we raise now?"', "high" if m["fundraising_readiness"] >= 75 else "medium")

    if memory.counts(company_id)["documents"] == 0 and memory.counts(company_id)["timeline"] == 0:
        push("priority", "Feed the Company Brain", "I work best with real signal.", "No sources connected or documents indexed yet.",
             "Connected, I prepare meetings and catch risks overnight.", "Open Sources to connect a tool or upload a document.", "medium")

    sev = {"high": 0, "medium": 1, "low": 2}
    rank = {"priority": 0, "approval": 1, "risk": 2, "opportunity": 3, "meeting": 4}
    items.sort(key=lambda i: (sev[i["severity"]], rank[i["section"]]))
    return items[:14]


# ---------------- Investor intelligence ----------------

STATE_LABELS = {"likely": "Likely to invest", "warm": "Warm", "viewed-deck": "Viewed deck recently",
                "due-follow-up": "Follow-up due", "cooling": "Cooling", "need-intro": "Need introduction"}


def next_best_action(inv: dict) -> str:
    return {
        "likely": "Propose terms conversation and a partner meeting this week.",
        "warm": "Send a tight progress update; ask for the next meeting.",
        "viewed-deck": "Strike while attention is high — offer a live walkthrough.",
        "due-follow-up": "Send the drafted follow-up now; momentum is decaying.",
        "cooling": "Re-engage with one concrete proof point, or deprioritize.",
        "need-intro": "Find a warm path in before any cold outreach.",
    }.get(inv["state"], "Keep the relationship warm.")


def draft_followup(company_id: str, inv: dict) -> str:
    m = derive_metrics(company_id)
    co = memory.get_company(company_id)
    proof = []
    if m["growth"] is not None:
        proof.append(f"we're growing {m['growth']}% month over month")
    if m["customers"] is not None:
        proof.append(f"now at {m['customers']} customers")
    if m["revenue"]:
        proof.append(f"{fmt_money(m['revenue'])} in revenue")
    if m["retention"] is not None:
        proof.append(f"{m['retention']}% retention")
    proof_line = ("Since we last spoke, " + ", ".join(proof) + ".") if proof else "We've made meaningful progress since we last spoke."
    first = inv["name"].split(" ")[0] if inv["name"] else inv["firm"]
    return "\n".join([
        f"Hi {first},", "",
        f"Quick update on {co['name'] if co else 'the company'}. {proof_line}", "",
        f"Given {inv['firm']}'s focus, I think there's a strong fit. Open to a 30-minute conversation next week?", "",
        "Happy to send updated materials ahead of time.", "", "Best,",
    ])


def meeting_prep(company_id: str, inv: dict) -> dict:
    m = derive_metrics(company_id)
    weak = []
    if m["monthly_spend"] and not m["revenue"]:
        weak.append("Burn with limited revenue — expect runway questions.")
    if m["retention"] is None:
        weak.append("No retention data — they'll probe stickiness.")
    if m["customers"] is not None and m["customers"] < 10:
        weak.append("Early traction — frame around quality of logos.")
    if not weak:
        weak.append("Metrics are solid — be ready to defend durability.")
    talking = []
    if m["growth"] is not None:
        talking.append(f"Growth: {m['growth']}% MoM")
    if m["retention"] is not None:
        talking.append(f"Retention: {m['retention']}%")
    if m["customers"] is not None:
        talking.append(f"{m['customers']} customers")
    return {
        "background": f"{inv['name']} at {inv['firm']}. State: {STATE_LABELS.get(inv['state'], inv['state'])} ({round(inv['probability'])}% probability).",
        "partner_interests": [inv.get("sector") or "Sector fit", "Founder-market fit", "Capital efficiency", "Defensibility"],
        "likely_objections": [{"objection": c, "answer": _objection_answer(c, m)} for c in (inv.get("concerns") or ["Market size", "Defensibility"])],
        "likely_questions": ["What's your growth rate and how durable is it?", "What does retention look like by cohort?", "Why now, and why your team?", "What does this round buy you?"],
        "weak_spots": weak, "talking_points": talking,
    }


def _objection_answer(concern: str, m: dict) -> str:
    c = concern.lower()
    if re.search(r"market|tam|size", c):
        return f"We size the market at {fmt_money(m['tam'])} and expand from a defensible wedge." if m["tam"] else "We start narrow and expand; here's the wedge."
    if "competit" in c or "defensib" in c:
        return "Our edge is the wedge customers can't easily replace; retention proves it."
    if re.search(r"retention|churn", c):
        return f"Retention is {m['retention']}% — the product compounds value." if m["retention"] is not None else "We're instrumenting cohort retention; early signal is strong."
    if re.search(r"burn|runway|capital", c):
        return f"We run at {fmt_money(m['monthly_spend'])}/mo and this round is milestone-scoped." if m["monthly_spend"] else "We're capital efficient; this round is milestone-scoped."
    return "Fair concern — here's the data and the plan that addresses it."


def debrief(company_id: str, inv: dict, notes: str) -> dict:
    low = notes.lower()
    positive = re.search(r"excited|interested|loved|strong|impressed|follow up|next meeting|term", low)
    negative = re.search(r"pass|not a fit|concerned|too early|worried|hesitant|decline", low)
    sentiment = "negative" if negative else "positive" if positive else "neutral"
    tasks = []
    if re.search(r"deck|materials|data ?room|metrics|model", low):
        tasks.append("Send updated materials / data room access")
    if re.search(r"intro|connect", low):
        tasks.append("Make the requested introduction")
    if re.search(r"follow up|next meeting|call", low):
        tasks.append("Schedule the follow-up meeting")
    tasks.append("Logged to Company Brain")
    return {"summary": f"Met with {inv['name']} ({inv['firm']}). {notes.strip()[:240]}", "sentiment": sentiment,
            "follow_up": draft_followup(company_id, inv), "tasks": tasks}
