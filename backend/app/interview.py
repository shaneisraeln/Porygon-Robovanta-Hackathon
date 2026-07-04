"""Dynamic Interview Engine.

Not a static form. CBO interviews the founder like a YC partner: the first
question establishes stage, then every subsequent question is chosen to maximize
missing business knowledge for THAT stage. Questions whose answers are already
known (from prior answers, uploads, or connected tools) are skipped. The
interview never truly ends — confidence per dimension drives follow-ups.
"""
from __future__ import annotations

from . import memory
from .config import settings
from .extract import detect_firms, fmt_money, parse_count, parse_money, parse_percent

# Canonical stages -> interview "group" that selects the question path.
STAGE_GROUP = {
    "Idea": "idea", "Building MVP": "mvp", "Product Live": "live", "Early Customers": "live",
    "Revenue": "revenue", "Fundraising": "fundraising", "Growth": "revenue",
}
STAGE_OPTIONS = ["Idea", "Building MVP", "Product Live", "Early Customers", "Revenue", "Fundraising", "Growth"]


def _q(id, attribute, prompt, groups, *, kind="text", options=None, value_kind="text", fact=None, weight=5, prereq=None):
    return {"id": id, "attribute": attribute, "prompt": prompt, "groups": groups, "kind": kind,
            "options": options, "value_kind": value_kind, "fact": fact, "weight": weight, "prereq": prereq}


# fact = (entity_type, key, label). Questions are ordered = priority within a path.
QUESTIONS = [
    # Always first.
    _q("stage", "stage", "What stage is your startup currently in?", "*", kind="choice", options=STAGE_OPTIONS,
       value_kind="choice", fact=("strategy", "stage", "Company stage"), weight=10),

    # Shared early context.
    _q("what", "product", "In a sentence — what are you building?", {"idea", "mvp", "live", "revenue", "fundraising"},
       fact=("product", "what", "What we're building"), weight=9),

    # --- IDEA path ---
    _q("problem", "problem", "What problem are you solving?", {"idea", "mvp"}, fact=("strategy", "problem", "Problem we solve"), weight=8),
    _q("who", "customers", "Who experiences this problem most acutely?", {"idea", "mvp"}, fact=("customer", "segment", "Customer segment"), weight=7),
    _q("why_now", "why_now", "Why is this problem important now?", {"idea"}, fact=("strategy", "why_now", "Why now"), weight=6),
    _q("alternatives", "competition", "How are people solving it today?", {"idea", "mvp"}, fact=("market", "alternatives", "Current alternatives"), weight=6),
    _q("validation", "validation", "Have you validated the idea? How?", {"idea"}, fact=("strategy", "validation", "Validation"), weight=7),
    _q("interviews", "validation", "Roughly how many potential users have you spoken with?", {"idea"}, value_kind="count", fact=("customer", "interviews", "User interviews"), weight=6),
    _q("prd", "product", "Do you have a PRD, spec, or prototype? (upload if so)", {"idea", "mvp"}, kind="upload", fact=("product", "prd", "PRD / spec"), weight=5),
    _q("vision", "vision", "What's the long-term vision?", {"idea"}, fact=("goal", "vision", "Vision"), weight=5),
    _q("business_model_idea", "business_model", "How do you expect to make money?", {"idea", "mvp"}, fact=("money", "business_model", "Business model"), weight=7),
    _q("geography", "market", "What geography / market are you targeting?", {"idea", "mvp"}, fact=("market", "geography", "Target geography"), weight=4),
    _q("funding_required", "funding", "How much funding do you think you need to get to the next milestone?", {"idea", "mvp"}, value_kind="money", fact=("investor", "funding_required", "Funding required"), weight=6),

    # --- BUILDING MVP path ---
    _q("website", "product", "What's your website? (or describe where it lives)", {"mvp", "live", "revenue"}, fact=("product", "website", "Website"), weight=4),
    _q("github", "product", "GitHub repo or codebase link? (connect GitHub to track velocity)", {"mvp", "live"}, fact=("product", "github_repo", "Codebase"), weight=4),
    _q("progress", "product", "How far along is the build right now?", {"mvp"}, fact=("product", "progress", "Build progress"), weight=7),
    _q("expected_launch", "execution", "When do you expect to launch?", {"mvp"}, fact=("goal", "launch", "Expected launch"), weight=5),
    _q("core_features", "product", "What are the 2–3 core features?", {"mvp"}, fact=("product", "features", "Core features"), weight=6),
    _q("tech", "product", "What's your tech stack?", {"mvp"}, fact=("product", "tech_stack", "Tech stack"), weight=3),
    _q("pilots", "customers", "Any pilot customers or design partners?", {"mvp"}, value_kind="count", fact=("customer", "pilots", "Pilot customers"), weight=6),
    _q("competitors", "competition", "Who are your main competitors?", {"mvp", "live", "revenue", "fundraising"}, fact=("market", "competitors", "Competitors"), weight=5),

    # --- PRODUCT LIVE / EARLY CUSTOMERS path ---
    _q("users", "customers", "How many users or customers do you have?", {"live", "revenue"}, value_kind="count", fact=("customer", "count", "Active customers"), weight=8),
    _q("active", "customers", "How many are active (weekly/monthly)?", {"live"}, value_kind="count", fact=("customer", "active", "Active users"), weight=6),
    _q("retention", "customers", "What does retention look like? (rough % is fine)", {"live", "revenue"}, value_kind="percent", fact=("customer", "retention", "Retention"), weight=7),
    _q("growth_feel", "traction", "How does growth feel lately?", {"live"}, kind="choice",
       options=["Not charging yet", "Flat", "Growing steadily", "Growing fast", "Exploding"], value_kind="growth", fact=("money", "growth", "Growth rate"), weight=7),
    _q("revenue_live", "revenue", "Are you generating revenue yet? Roughly how much?", {"live"}, value_kind="money", fact=("money", "revenue", "Revenue"), weight=7),
    _q("business_model_live", "business_model", "What's your business model / how do you charge?", {"live", "revenue"}, fact=("money", "business_model", "Business model"), weight=6),
    _q("marketing", "gtm", "What are your main acquisition channels?", {"live", "revenue"}, fact=("strategy", "marketing", "Acquisition channels"), weight=5),

    # --- REVENUE / GROWTH path ---
    _q("mrr", "revenue", "What's your MRR or ARR right now?", {"revenue"}, value_kind="money", fact=("money", "revenue", "Revenue"), weight=9),
    _q("growth_rate", "traction", "How fast is revenue growing month over month?", {"revenue"}, value_kind="percent", fact=("money", "growth", "Growth rate"), weight=8),
    _q("burn", "revenue", "What's your monthly burn?", {"revenue", "fundraising"}, value_kind="money", fact=("money", "monthly_spend", "Monthly spend (burn)"), weight=8),
    _q("cash", "revenue", "How much cash do you have in the bank?", {"revenue", "fundraising"}, value_kind="money", fact=("money", "cash", "Cash in bank"), weight=8),
    _q("pricing", "revenue", "How do you price?", {"revenue"}, fact=("money", "pricing", "Pricing"), weight=5),
    _q("cac", "gtm", "Roughly what does it cost to acquire a customer (CAC)?", {"revenue"}, value_kind="money", fact=("money", "cac", "CAC"), weight=5),
    _q("sales_motion", "gtm", "What's your sales motion (self-serve, sales-led)?", {"revenue"}, fact=("strategy", "sales_motion", "Sales motion"), weight=4),
    _q("financials", "revenue", "Have financial statements? (upload to enrich the model)", {"revenue", "fundraising"}, kind="upload", fact=("money", "financials", "Financial statements"), weight=4),

    # --- FUNDRAISING path ---
    _q("round", "funding", "What round are you raising?", {"fundraising"}, kind="choice",
       options=["Pre-seed", "Seed", "Series A", "Series B+"], value_kind="choice", fact=("investor", "round", "Current round"), weight=9),
    _q("amount", "funding", "How much are you raising?", {"fundraising"}, value_kind="money", fact=("investor", "raise_target", "Raise target"), weight=9),
    _q("valuation", "funding", "Target valuation (or cap)?", {"fundraising"}, value_kind="money", fact=("investor", "valuation", "Target valuation"), weight=7),
    _q("existing_conversations", "funding", "Any investor conversations going already? (names help)", {"fundraising"}, fact=("investor", "conversations", "Existing conversations"), weight=8),
    _q("target_investors", "funding", "Which investors or firms are you targeting?", {"fundraising"}, fact=("investor", "target_investors", "Target investors"), weight=7),
    _q("pitch_deck", "funding", "Do you have a pitch deck? (upload it)", {"fundraising"}, kind="upload", fact=("investor", "pitch_deck", "Pitch deck"), weight=8),
    _q("data_room", "funding", "Do you have a data room set up?", {"fundraising"}, fact=("investor", "data_room", "Data room"), weight=5),

    # --- Shared closers ---
    _q("team", "team", "How big is the team, and what are the key roles?", "*", value_kind="count", fact=("team", "headcount", "Team size"), weight=6),
    _q("goals", "goals", "What's your #1 goal for the next 6 months?", "*", fact=("goal", "goal", "6-month goal"), weight=6),
]

# Connectors that satisfy a fact key (so we don't ask).
CONNECTOR_SATISFIES = {
    "stripe": ["revenue"], "hubspot": ["count"], "github": ["github_repo"],
    "gmail": ["conversations"], "gcal": ["conversations"],
}

# Knowledge dimensions surfaced as confidence scores (Rule 4).
DIMENSIONS = {
    "business_model": (["business_model", "pricing"], 1.0),
    "product": (["what", "features", "progress", "github_repo"], 1.0),
    "customers": (["count", "segment", "active", "pilots", "interviews"], 1.0),
    "revenue": (["revenue", "mrr", "monthly_spend", "cash"], 1.0),
    "market": (["geography", "alternatives", "tam"], 1.0),
    "competition": (["competitors", "alternatives"], 1.0),
    "team": (["headcount"], 1.0),
    "traction": (["growth", "retention"], 1.0),
    "funding_readiness": (["raise_target", "round", "pitch_deck", "valuation"], 1.0),
}


def link_fact_entity(company_id: str, fact_type: str, label: str, value: str) -> str | None:
    if fact_type == "product":
        return memory.upsert_entity(company_id, "product", "Product", "builds")
    if fact_type == "customer":
        return memory.upsert_entity(company_id, "customer", "Customers", "serves")
    if fact_type == "team":
        return memory.upsert_entity(company_id, "person", "Team", "employs")
    if fact_type in ("money", "market"):
        return memory.upsert_entity(company_id, "metric", label, "tracks")
    if fact_type == "goal":
        return memory.upsert_entity(company_id, "goal", value[:28], "pursues")
    if fact_type == "investor":
        firms = detect_firms(value)
        return memory.upsert_entity(company_id, "investor", firms[0] if firms else "Investors", "fundraising")
    return None


def _known_keys(company_id: str) -> set[str]:
    keys = {f["key"] for f in memory.list_facts(company_id)}
    # Connectors satisfy certain keys.
    states = memory.list_connector_states(company_id)
    for cid, st in states.items():
        if st.get("connected"):
            keys.update(CONNECTOR_SATISFIES.get(cid, []))
    return keys


def _current_stage(company_id: str) -> str | None:
    for f in memory.list_facts(company_id):
        if f["key"] == "stage":
            return f["value"]
    return None


def _value_for(q: dict, text: str) -> tuple[str, float | None]:
    vk = q["value_kind"]
    if vk == "money":
        m = parse_money(text)
        return (fmt_money(m), m) if m is not None else (text, None)
    if vk == "count":
        n = parse_count(text)
        return (str(n), float(n)) if n is not None else (text, None)
    if vk == "percent":
        p = parse_percent(text)
        return (f"{p}%", p) if p is not None else (text, None)
    if vk == "growth":
        table = [("explod", 40, "Exploding"), ("fast", 20, "Growing fast"), ("stead", 8, "Growing steadily"),
                 ("flat", 2, "Flat"), ("not charg", 0, "Not charging yet")]
        low = text.lower()
        hit = next((t for t in table if t[0] in low), None)
        return (f"{hit[1]}% ({hit[2]})", float(hit[1])) if hit else (text, None)
    return (text, None)


def next_question(company_id: str) -> dict | None:
    stage = _current_stage(company_id)
    log = memory.interview_log(company_id)
    known = _known_keys(company_id)

    if not stage:
        return _public_q(QUESTIONS[0])

    group = STAGE_GROUP.get(stage, "live")
    candidates = []
    for q in QUESTIONS:
        if q["id"] == "stage":
            continue
        if q["groups"] != "*" and group not in q["groups"]:
            continue
        if q["id"] in log:  # answered or skipped
            continue
        if q["fact"] and q["fact"][1] in known:  # already known from memory/connector
            continue
        candidates.append(q)
    if not candidates:
        return None
    # Highest information value first (questions are pre-ordered by priority within path).
    candidates.sort(key=lambda q: -q["weight"])
    return _public_q(candidates[0], company_id)


def _public_q(q: dict, company_id: str | None = None) -> dict:
    out = {"id": q["id"], "prompt": q["prompt"], "kind": q["kind"], "options": q["options"], "attribute": q["attribute"]}
    # Continuous-onboarding context: acknowledge connected tools.
    if company_id and q["fact"]:
        for cid, keys in CONNECTOR_SATISFIES.items():
            st = memory.get_connector_state(company_id, cid)
            if st and st.get("connected") and q["fact"][1] in keys:
                out["context"] = f"I see {cid} is connected — I'll pull this automatically."
    return out


def record_answer(company_id: str, question_id: str, text: str) -> list[dict]:
    q = next((x for x in QUESTIONS if x["id"] == question_id), None)
    if not q:
        return []
    text = text.strip()
    memory.log_question(company_id, question_id, "answered")
    captured = []
    if q["fact"] and text:
        ftype, key, label = q["fact"]
        value, num = _value_for(q, text)
        eid = link_fact_entity(company_id, ftype, label, value)
        memory.add_fact(company_id, ftype, key, label, value, source_ref=f"Interview · {q['attribute']}",
                        num=num, entity_id=eid, source_kind="conversation", evidence=text, confidence=0.85, owner="founder")
        captured.append({"label": label, "value": value})

        # Side-effects that mirror real founder intent.
        if key == "stage":
            memory.update_company(company_id, stage=value)
        if ftype == "product" and key == "what":
            memory.update_company(company_id, what=text)
        if q["attribute"] in ("customers",) and key == "segment":
            memory.update_company(company_id, customers=text)
        # Any firms mentioned become tracked investors (real signal).
        if ftype == "investor":
            for firm in detect_firms(text):
                memory.upsert_investor(company_id, firm, name=firm, state="need-intro", probability=40, warmth=40, concerns=["Why now", "Traction"])
    return captured


def skip(company_id: str, question_id: str) -> None:
    memory.log_question(company_id, question_id, "skipped")


def profile(company_id: str) -> dict:
    facts = memory.list_facts(company_id)
    by_key: dict[str, float] = {}
    for f in facts:
        by_key[f["key"]] = max(by_key.get(f["key"], 0.0), f["confidence"])
    known = _known_keys(company_id)

    dims = []
    for name, (keys, _w) in DIMENSIONS.items():
        present = [by_key.get(k, 0.0) for k in keys if k in by_key]
        # connector-satisfied keys count as high confidence
        if any(k in known and k not in by_key for k in keys):
            present.append(0.85)
        conf = round((max(present) if present else 0.0) * 100)
        dims.append({"key": name, "label": name.replace("_", " ").title(), "confidence": conf})

    stage = _current_stage(company_id)
    knowledge_confidence = round(sum(d["confidence"] for d in dims) / len(dims)) if dims else 0
    missing = [d["label"] for d in dims if d["confidence"] < 40]
    return {"stage": stage, "dimensions": dims, "knowledge_confidence": knowledge_confidence, "missing": missing}
