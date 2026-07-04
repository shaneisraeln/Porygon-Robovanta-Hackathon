"""Investor Intelligence Network.

A permanent, growable knowledge base of real VC firms (seeded from public
knowledge, extendable via /network/import or an external data API) plus a
fit-scoring engine that recomputes live from Company Memory. The founder never
searches — CBO discovers, researches, ranks, finds warm intros, and prepares the
entire outreach. Check/fund sizes are public estimates and are labelled as such.
"""
from __future__ import annotations

import re

from . import ai, llm, memory
from .extract import fmt_money

# Real, well-known firms with publicly-known focus. Not fabricated metrics —
# sectors/stages/geographies/notable portfolio are public knowledge; check sizes
# are rough public estimates. Grow this via import or a data provider.
SEED = [
    {"firm": "Sequoia / Peak XV", "partners": ["Roelof Botha", "Shailendra Singh"], "stages": ["Seed", "Series A", "Series B+"],
     "industries": ["ai", "saas", "fintech", "consumer", "enterprise", "healthcare", "devtools"], "geos": ["US", "India", "Global"],
     "check_size": "$1M–$20M (est.)", "fund": "Multi-stage", "portfolio": ["Stripe", "Zoom", "Razorpay", "Whatfix"],
     "recent": ["applied ai", "fintech infra"], "thesis": "Category-defining founders across software, AI and fintech.",
     "twitter": "@sequoia", "blog": "sequoiacap.com", "preferred_revenue": "Traction to early revenue"},
    {"firm": "Andreessen Horowitz (a16z)", "partners": ["Martin Casado", "Sarah Wang"], "stages": ["Seed", "Series A", "Series B+"],
     "industries": ["ai", "infra", "crypto", "fintech", "bio", "enterprise", "devtools"], "geos": ["US", "Global"],
     "check_size": "$2M–$50M (est.)", "fund": "Large multi-fund", "portfolio": ["Databricks", "Coinbase", "GitHub"],
     "recent": ["ai infrastructure", "applied ai"], "thesis": "Software is eating the world; deep technical bets in AI, infra, crypto, bio.",
     "twitter": "@a16z", "blog": "a16z.com", "preferred_revenue": "Flexible"},
    {"firm": "Accel", "partners": ["Rich Wong", "Prayank Swaroop"], "stages": ["Seed", "Series A", "Series B+"],
     "industries": ["saas", "ai", "fintech", "consumer", "enterprise", "marketplace"], "geos": ["US", "India", "Europe"],
     "check_size": "$1M–$30M (est.)", "fund": "Multi-stage", "portfolio": ["Slack", "Flipkart", "Freshworks"],
     "recent": ["b2b saas", "ai apps"], "thesis": "Backing exceptional teams from inception to IPO globally.",
     "twitter": "@accel", "blog": "accel.com", "preferred_revenue": "Early revenue"},
    {"firm": "Lightspeed", "partners": ["Ravi Mhatre", "Dev Khare"], "stages": ["Seed", "Series A", "Series B+"],
     "industries": ["ai", "saas", "fintech", "consumer", "enterprise", "crypto"], "geos": ["US", "India", "Europe", "Global"],
     "check_size": "$1M–$25M (est.)", "fund": "Multi-stage", "portfolio": ["Snap", "Affirm", "Udaan"],
     "recent": ["enterprise ai", "fintech"], "thesis": "Backing bold founders in enterprise and consumer.",
     "twitter": "@lightspeedvp", "blog": "lsvp.com", "preferred_revenue": "Flexible"},
    {"firm": "Y Combinator", "partners": ["Garry Tan"], "stages": ["Pre-seed", "Seed"],
     "industries": ["ai", "saas", "fintech", "devtools", "healthcare", "consumer", "b2b", "marketplace", "climate"], "geos": ["US", "Global"],
     "check_size": "$500K standard deal", "fund": "Accelerator", "portfolio": ["Airbnb", "Stripe", "Dropbox"],
     "recent": ["ai agents", "devtools"], "thesis": "Fund the earliest founders; make something people want.",
     "twitter": "@ycombinator", "blog": "ycombinator.com/blog", "preferred_revenue": "Pre-revenue OK"},
    {"firm": "Conviction", "partners": ["Sarah Guo"], "stages": ["Seed", "Series A"],
     "industries": ["ai", "devtools", "infra", "enterprise"], "geos": ["US", "Global"],
     "check_size": "$1M–$15M (est.)", "fund": "AI-focused", "portfolio": ["Harvey", "Sierra"],
     "recent": ["applied ai", "ai infrastructure"], "thesis": "Software in the intelligence age — AI-native companies.",
     "twitter": "@saranormous", "blog": "conviction.com", "preferred_revenue": "Early"},
    {"firm": "General Catalyst", "partners": ["Hemant Taneja"], "stages": ["Seed", "Series A", "Series B+", "Growth"],
     "industries": ["ai", "healthcare", "fintech", "enterprise", "defense"], "geos": ["US", "Europe", "India"],
     "check_size": "$2M–$50M (est.)", "fund": "Multi-stage", "portfolio": ["Stripe", "Livongo", "Ramp"],
     "recent": ["health ai", "applied ai"], "thesis": "Responsible innovation; health, fintech, applied AI.",
     "twitter": "@gcvp", "blog": "generalcatalyst.com", "preferred_revenue": "Flexible"},
    {"firm": "Bessemer", "partners": ["Byron Deeter"], "stages": ["Seed", "Series A", "Series B+"],
     "industries": ["saas", "cloud", "ai", "healthcare", "fintech"], "geos": ["US", "India", "Europe"],
     "check_size": "$1M–$30M (est.)", "fund": "Multi-stage", "portfolio": ["Shopify", "Twilio", "PagerDuty"],
     "recent": ["cloud", "vertical saas"], "thesis": "Cloud and vertical SaaS leaders.",
     "twitter": "@bessemervp", "blog": "bvp.com", "preferred_revenue": "Early recurring revenue"},
    {"firm": "Index Ventures", "partners": ["Mike Volpi"], "stages": ["Seed", "Series A", "Series B+"],
     "industries": ["ai", "saas", "fintech", "infra", "consumer"], "geos": ["US", "Europe", "Global"],
     "check_size": "$1M–$40M (est.)", "fund": "Multi-stage", "portfolio": ["Figma", "Revolut", "Wiz"],
     "recent": ["ai", "fintech"], "thesis": "Backing transatlantic category leaders.",
     "twitter": "@indexventures", "blog": "indexventures.com", "preferred_revenue": "Flexible"},
    {"firm": "Greylock", "partners": ["Reid Hoffman", "Saam Motamedi"], "stages": ["Seed", "Series A"],
     "industries": ["ai", "enterprise", "security", "infra", "consumer"], "geos": ["US"],
     "check_size": "$1M–$20M (est.)", "fund": "Early-stage", "portfolio": ["LinkedIn", "Figma", "Abnormal"],
     "recent": ["enterprise ai", "security"], "thesis": "Day-one partner to enterprise and AI founders.",
     "twitter": "@greylockvc", "blog": "greylock.com", "preferred_revenue": "Early"},
    {"firm": "Khosla Ventures", "partners": ["Vinod Khosla", "Keith Rabois"], "stages": ["Seed", "Series A", "Series B+"],
     "industries": ["ai", "deeptech", "climate", "healthcare", "fintech", "bio"], "geos": ["US"],
     "check_size": "$1M–$30M (est.)", "fund": "Multi-stage", "portfolio": ["OpenAI", "Square", "DoorDash"],
     "recent": ["ai", "hard tech"], "thesis": "Bold, contrarian bets on hard problems.",
     "twitter": "@khoslaventures", "blog": "khoslaventures.com", "preferred_revenue": "Flexible"},
    {"firm": "Founders Fund", "partners": ["Peter Thiel", "Keith Rabois"], "stages": ["Seed", "Series A", "Series B+"],
     "industries": ["ai", "deeptech", "defense", "crypto", "bio", "space"], "geos": ["US"],
     "check_size": "$1M–$50M (est.)", "fund": "Multi-stage", "portfolio": ["SpaceX", "Palantir", "Stripe"],
     "recent": ["defense tech", "ai"], "thesis": "Back companies building the future, especially hard tech.",
     "twitter": "@foundersfund", "blog": "foundersfund.com", "preferred_revenue": "Flexible"},
    {"firm": "First Round Capital", "partners": ["Josh Kopelman"], "stages": ["Pre-seed", "Seed"],
     "industries": ["saas", "ai", "fintech", "consumer", "b2b", "healthcare"], "geos": ["US"],
     "check_size": "$500K–$3M (est.)", "fund": "Seed", "portfolio": ["Uber", "Notion", "Roblox"],
     "recent": ["b2b", "ai apps"], "thesis": "First institutional check; deep early-stage support.",
     "twitter": "@firstround", "blog": "review.firstround.com", "preferred_revenue": "Pre-revenue OK"},
    {"firm": "Initialized Capital", "partners": ["Garry Tan (fmr)"], "stages": ["Pre-seed", "Seed"],
     "industries": ["saas", "ai", "fintech", "consumer", "devtools"], "geos": ["US"],
     "check_size": "$500K–$5M (est.)", "fund": "Seed", "portfolio": ["Coinbase", "Instacart"],
     "recent": ["ai", "b2b"], "thesis": "Seed-stage partner for technical founders.",
     "twitter": "@initialized", "blog": "initialized.com", "preferred_revenue": "Pre-revenue OK"},
    {"firm": "Blume Ventures", "partners": ["Karthik Reddy", "Sajith Pai"], "stages": ["Pre-seed", "Seed", "Series A"],
     "industries": ["saas", "ai", "fintech", "consumer", "healthcare", "b2b"], "geos": ["India"],
     "check_size": "$500K–$5M (est.)", "fund": "Early-stage India", "portfolio": ["Unacademy", "Slice", "Purplle"],
     "recent": ["india saas", "ai"], "thesis": "Backing India's early-stage founders.",
     "twitter": "@blumeventures", "blog": "blume.vc", "preferred_revenue": "Early"},
    {"firm": "Together Fund", "partners": ["Manav Garg", "Girish Mathrubootham"], "stages": ["Seed", "Series A"],
     "industries": ["saas", "ai", "devtools", "enterprise", "b2b"], "geos": ["India", "US", "Global"],
     "check_size": "$500K–$8M (est.)", "fund": "B2B SaaS", "portfolio": ["B2B SaaS portfolio"],
     "recent": ["b2b saas", "ai"], "thesis": "Operator-led fund for global B2B SaaS from India.",
     "twitter": "@together_fund", "blog": "togetherfund.com", "preferred_revenue": "Early recurring revenue"},
    {"firm": "Elevation Capital", "partners": ["Ravi Adusumalli"], "stages": ["Seed", "Series A"],
     "industries": ["consumer", "fintech", "saas", "ai", "healthcare"], "geos": ["India"],
     "check_size": "$1M–$10M (est.)", "fund": "Early-stage India", "portfolio": ["Paytm", "Meesho", "Spinny"],
     "recent": ["consumer", "fintech"], "thesis": "Early partner to India's breakout companies.",
     "twitter": "@elevationcap", "blog": "elevationcapital.com", "preferred_revenue": "Early"},
    {"firm": "Matrix Partners", "partners": ["Avnish Bajaj"], "stages": ["Seed", "Series A"],
     "industries": ["consumer", "fintech", "saas", "ai", "b2b"], "geos": ["India", "US"],
     "check_size": "$1M–$15M (est.)", "fund": "Early-stage", "portfolio": ["Ola", "Razorpay", "Dailyhunt"],
     "recent": ["fintech", "ai"], "thesis": "Backing founders building enduring companies.",
     "twitter": "@matrixpartners", "blog": "matrixpartners.in", "preferred_revenue": "Early"},
    {"firm": "Insight Partners", "partners": ["Deven Parekh"], "stages": ["Series A", "Series B+", "Growth"],
     "industries": ["saas", "ai", "fintech", "enterprise", "security"], "geos": ["US", "Europe", "Global"],
     "check_size": "$5M–$100M (est.)", "fund": "Growth", "portfolio": ["Shopify", "Twitter", "Wiz"],
     "recent": ["scaleup saas", "ai"], "thesis": "ScaleUp software at growth stage.",
     "twitter": "@insightpartners", "blog": "insightpartners.com", "preferred_revenue": "$1M+ ARR"},
    {"firm": "Tiger Global", "partners": ["Scott Shleifer"], "stages": ["Series A", "Series B+", "Growth"],
     "industries": ["saas", "fintech", "consumer", "ai", "enterprise"], "geos": ["Global"],
     "check_size": "$10M–$100M+ (est.)", "fund": "Growth/crossover", "portfolio": ["Stripe", "Flipkart", "Databricks"],
     "recent": ["growth software"], "thesis": "Late-stage and growth software globally.",
     "twitter": "@tigerglobal", "blog": "tigerglobal.com", "preferred_revenue": "$2M+ ARR"},
    {"firm": "Ribbit Capital", "partners": ["Micky Malka"], "stages": ["Seed", "Series A", "Series B+"],
     "industries": ["fintech", "crypto", "ai"], "geos": ["US", "Global"],
     "check_size": "$2M–$40M (est.)", "fund": "Fintech-focused", "portfolio": ["Robinhood", "Coinbase", "Revolut"],
     "recent": ["fintech", "fintech ai"], "thesis": "Reinventing financial services.",
     "twitter": "@ribbitcapital", "blog": "ribbitcap.com", "preferred_revenue": "Early"},
    {"firm": "Bessemer Healthcare / Oak HC/FT", "partners": ["Annie Lamont"], "stages": ["Seed", "Series A", "Series B+"],
     "industries": ["healthcare", "fintech", "ai"], "geos": ["US"],
     "check_size": "$5M–$50M (est.)", "fund": "Healthcare & fintech", "portfolio": ["Devoted Health", "Quartet"],
     "recent": ["health ai", "fintech"], "thesis": "Healthcare and fintech transformation.",
     "twitter": "@oakhcft", "blog": "oakhcft.com", "preferred_revenue": "Early revenue"},
    {"firm": "Lux Capital", "partners": ["Josh Wolfe"], "stages": ["Seed", "Series A", "Series B+"],
     "industries": ["deeptech", "ai", "bio", "defense", "climate", "robotics"], "geos": ["US"],
     "check_size": "$1M–$30M (est.)", "fund": "Deep tech", "portfolio": ["Anduril", "Hugging Face"],
     "recent": ["ai", "hard tech"], "thesis": "Emerging science and hard technology.",
     "twitter": "@lux_capital", "blog": "luxcapital.com", "preferred_revenue": "Flexible"},
    {"firm": "Craft Ventures", "partners": ["David Sacks"], "stages": ["Seed", "Series A", "Series B+"],
     "industries": ["saas", "ai", "marketplace", "enterprise"], "geos": ["US"],
     "check_size": "$1M–$20M (est.)", "fund": "Multi-stage", "portfolio": ["SpaceX", "Affirm", "ClickUp"],
     "recent": ["saas", "ai"], "thesis": "SaaS and marketplace businesses with strong fundamentals.",
     "twitter": "@craft_ventures", "blog": "craftventures.com", "preferred_revenue": "Early recurring"},
    {"firm": "Point Nine", "partners": ["Christoph Janz"], "stages": ["Pre-seed", "Seed"],
     "industries": ["saas", "b2b", "ai", "marketplace"], "geos": ["Europe", "Global"],
     "check_size": "$500K–$5M (est.)", "fund": "Seed SaaS", "portfolio": ["Zendesk", "Algolia", "Loom"],
     "recent": ["b2b saas", "ai"], "thesis": "Global SaaS and B2B marketplaces at seed.",
     "twitter": "@pointninecap", "blog": "pointnine.com", "preferred_revenue": "Early recurring"},
    {"firm": "Seedcamp", "partners": ["Reshma Sohoni"], "stages": ["Pre-seed", "Seed"],
     "industries": ["saas", "ai", "fintech", "devtools", "b2b"], "geos": ["Europe"],
     "check_size": "$200K–$2M (est.)", "fund": "Pre-seed/seed Europe", "portfolio": ["UiPath", "Revolut", "Wise"],
     "recent": ["ai", "fintech"], "thesis": "Europe's seed fund for ambitious founders.",
     "twitter": "@seedcamp", "blog": "seedcamp.com", "preferred_revenue": "Pre-revenue OK"},
    {"firm": "Felicis", "partners": ["Aydin Senkut"], "stages": ["Seed", "Series A"],
     "industries": ["ai", "saas", "fintech", "healthcare", "devtools"], "geos": ["US", "Global"],
     "check_size": "$1M–$15M (est.)", "fund": "Early-stage", "portfolio": ["Shopify", "Notion", "Canva"],
     "recent": ["ai", "saas"], "thesis": "Backing iconic companies early.",
     "twitter": "@felicis", "blog": "felicis.com", "preferred_revenue": "Early"},
    {"firm": "Spark Capital", "partners": ["Nabeel Hyatt"], "stages": ["Seed", "Series A", "Series B+"],
     "industries": ["consumer", "ai", "fintech", "saas", "crypto"], "geos": ["US"],
     "check_size": "$1M–$30M (est.)", "fund": "Multi-stage", "portfolio": ["Twitter", "Slack", "Affirm"],
     "recent": ["consumer ai", "fintech"], "thesis": "Partnering with founders defining categories.",
     "twitter": "@sparkcapital", "blog": "spark.vc", "preferred_revenue": "Flexible"},
]


def ensure_seed():
    if memory.investordb_count() == 0:
        for rec in SEED:
            memory.investordb_upsert(rec)


# ---------------- company signals ----------------

_SECTOR_SYNONYMS = {
    "health": ["healthcare", "health", "medical", "bio", "clinical", "patient"],
    "fintech": ["fintech", "finance", "payments", "banking", "lending", "insurance"],
    "ai": ["ai", "ml", "machine learning", "artificial intelligence", "llm", "agents"],
    "saas": ["saas", "software", "b2b", "platform"],
    "devtools": ["developer", "devtools", "api", "infrastructure", "infra"],
    "consumer": ["consumer", "social", "marketplace", "commerce", "d2c"],
    "climate": ["climate", "carbon", "energy", "sustainability", "emissions"],
    "crypto": ["crypto", "web3", "blockchain", "defi"],
    "security": ["security", "cyber", "privacy"],
    "enterprise": ["enterprise", "b2b"],
}


def _company_signals(company_id: str) -> dict:
    co = memory.get_company(company_id) or {}
    m = ai.derive_metrics(company_id)
    text = " ".join([co.get("what", ""), co.get("customers", ""),
                     (memory.list_facts(company_id) and "" or "")]).lower()
    # gather industry/segment/problem facts
    for f in memory.list_facts(company_id):
        if f["key"] in ("what", "segment", "problem", "industry", "features"):
            text += " " + f["value"].lower()
    sectors = set()
    for canon, words in _SECTOR_SYNONYMS.items():
        if any(w in text for w in words):
            sectors.add(canon)
    geo = ""
    for f in memory.list_facts(company_id):
        if f["key"] == "geography":
            geo = f["value"]
            break
    if not geo:
        if re.search(r"\b(india|bangalore|bengaluru|mumbai|delhi|gurgaon|hyderabad)\b", text):
            geo = "India"
        elif re.search(r"\b(europe|london|berlin|paris|uk|germany|france|amsterdam)\b", text):
            geo = "Europe"
        elif re.search(r"\b(us|usa|america|san francisco|sf|new york|silicon valley)\b", text):
            geo = "US"
    # canonical stage
    stage = co.get("stage") or ""
    target = _target_stage(company_id, stage)
    return {"sectors": sectors, "geo": geo, "stage": target, "raw_stage": stage, "metrics": m, "text": text}


def _target_stage(company_id: str, stage: str) -> str:
    s = stage.lower()
    # explicit round overrides
    for f in memory.list_facts(company_id):
        if f["key"] == "round":
            r = f["value"].lower()
            if "pre" in r:
                return "Pre-seed"
            if "seed" in r:
                return "Seed"
            if "series a" in r:
                return "Series A"
            if "series b" in r or "series c" in r:
                return "Series B+"
    if "idea" in s or "mvp" in s or "building" in s:
        return "Pre-seed"
    if "live" in s or "early" in s:
        return "Seed"
    if "revenue" in s:
        return "Seed"
    if "growth" in s or "scal" in s:
        return "Series B+"
    if "fundrais" in s:
        return "Seed"
    return "Seed"


def _geo_match(company_geo: str, firm_geos: list[str]) -> bool:
    if "Global" in firm_geos:
        return True
    if not company_geo:
        return True  # unknown geo → don't penalize
    cg = company_geo.lower()
    for g in firm_geos:
        if g.lower() in cg or cg in g.lower():
            return True
    if any(x in cg for x in ["india", "bangalore", "mumbai", "delhi"]) and "India" in firm_geos:
        return True
    if any(x in cg for x in ["us", "usa", "america", "sf", "valley", "new york"]) and "US" in firm_geos:
        return True
    if any(x in cg for x in ["uk", "europe", "berlin", "london", "paris"]) and "Europe" in firm_geos:
        return True
    return False


# ---------------- scoring ----------------

def _canon_set(tokens: list[str]) -> set[str]:
    """Map raw industry words to canonical sectors so firm/company match fairly."""
    out = set()
    for t in tokens:
        t = t.lower()
        matched = False
        for canon, words in _SECTOR_SYNONYMS.items():
            if t == canon or t in words or any(w in t for w in words):
                out.add(canon)
                matched = True
        if not matched:
            out.add(t)
    return out


def _score(sig: dict, firm: dict) -> dict:
    reasons_for, reasons_against = [], []
    score = 18.0
    firm_sectors = _canon_set(firm["industries"])
    focused = len(firm["industries"]) <= 4

    # Stage fit
    if sig["stage"] in firm["stages"]:
        score += 22
        reasons_for.append(f"Invests at your stage ({sig['stage']})")
    else:
        reasons_against.append(f"Prefers {', '.join(firm['stages'])}, you're at {sig['stage']}")

    # Sector fit (relative to your focus + firm specialization)
    overlap = sig["sectors"] & firm_sectors
    if sig["sectors"]:
        frac = len(overlap) / len(sig["sectors"])
        score += frac * 24
        if overlap:
            reasons_for.append("Sector match: " + ", ".join(sorted(overlap)))
            if focused:
                score += 8
                reasons_for.append(f"{firm['firm'].split(' ')[0]} specializes here")
        else:
            reasons_against.append("Sector focus differs from your space")

    # Recent-thesis bonus
    recent = _canon_set(firm.get("recent", []))
    if sig["sectors"] & recent:
        score += 10
        reasons_for.append("Active recently in your sector — thesis is hot here")

    # Geo fit (neutral when geo unknown)
    if sig["geo"]:
        if _geo_match(sig["geo"], firm["geos"]):
            score += 10
            reasons_for.append(f"Invests in your geography ({sig['geo']})")
        else:
            score -= 10
            reasons_against.append(f"Mostly invests in {', '.join(firm['geos'])}")

    # Traction fit
    m = sig["metrics"]
    pref = firm.get("preferred_revenue", "").lower()
    if m.get("revenue"):
        score += 6
        reasons_for.append(f"You have revenue ({fmt_money(m['revenue'])})")
    elif "pre-revenue" in pref:
        score += 3
    elif "arr" in pref or "recurring" in pref:
        score -= 6
        reasons_against.append("Wants recurring revenue — yours isn't on file yet")

    if m.get("retention") is None and sig["stage"] in ("Seed", "Series A"):
        score -= 4
        reasons_against.append("Need stronger retention evidence")

    fit = max(5, min(98, round(score)))
    probability = round(fit * 0.7)
    return {"fit_score": fit, "probability": probability, "reasons_for": reasons_for, "reasons_against": reasons_against}


def _warm_intro(company_id: str, firm_name: str) -> dict:
    # A warm path exists if any person in memory is linked to this firm.
    g = memory.graph(company_id)
    firm_entity = next((e for e in g["entities"] if e["type"] == "investor" and e["name"].lower() in firm_name.lower()), None)
    if firm_entity:
        # someone connected to the firm node
        people = [e for e in g["entities"] if e["type"] == "person"]
        if people:
            return {"available": True, "via": people[0]["name"], "path": f"{people[0]['name']} → {firm_entity['name']}"}
        return {"available": True, "via": "your network", "path": "Existing relationship in memory"}
    return {"available": False, "via": None, "path": "No warm path yet — connect Gmail/LinkedIn or ask for an intro"}


# ---------------- public API ----------------

def discover(company_id: str) -> dict:
    ensure_seed()
    sig = _company_signals(company_id)
    firms = memory.investordb_all()
    ranked = []
    for f in firms:
        sc = _score(sig, f)
        warm = _warm_intro(company_id, f["firm"])
        ranked.append({"id": f["id"], "firm": f["firm"], "partners": f["partners"], "stages": f["stages"],
                       "industries": f["industries"], "geos": f["geos"], "check_size": f["check_size"],
                       "thesis": f["thesis"], "warm_intro": warm, **sc})
    ranked.sort(key=lambda x: x["fit_score"], reverse=True)
    worth = [r for r in ranked if r["fit_score"] >= 65]
    excellent = [r for r in ranked if r["fit_score"] >= 80]
    return {"total": len(ranked), "worth_count": len(worth), "excellent_count": len(excellent),
            "signals": {"stage": sig["stage"], "sectors": sorted(sig["sectors"]), "geo": sig["geo"]},
            "investors": ranked}


def research(company_id: str, firm_id: str) -> dict:
    firm = memory.investordb_get(firm_id)
    if not firm:
        return {}
    sig = _company_signals(company_id)
    sc = _score(sig, firm)
    warm = _warm_intro(company_id, firm["firm"])
    m = sig["metrics"]
    co = memory.get_company(company_id) or {}

    # Strategy + timing (executive thinking).
    strategy, timing, projected = _strategy(sc, sig)
    narrative = _narrative(co, m, firm, sc)
    email = _email(co, m, firm, warm)
    agenda = ["Intro & company snapshot", "Problem & why now", "Product demo / traction",
              f"Market & {firm['firm'].split(' ')[0]} fit", "The ask & use of funds", "Q&A"]
    likely_q = ["What's your growth rate and how durable is it?", "What does retention look like by cohort?",
                f"Why are you a fit for {firm['firm']}?", "Why now, and why your team?", "What does this round unlock?"]
    objections = sc["reasons_against"] or ["Defend how current metrics sustain"]
    deck_version = f"{sig['stage']} deck — lead with " + ("traction" if m.get("revenue") else "vision & team")
    follow_up = "Send a tailored update referencing their recent thesis; propose a 30-min partner intro."

    return {"firm": firm, "fit": sc, "warm_intro": warm, "suggested_strategy": strategy, "suggested_timing": timing,
            "projected_probability": projected, "suggested_narrative": narrative, "suggested_deck_version": deck_version,
            "suggested_email": email, "suggested_agenda": agenda, "likely_questions": likely_q,
            "likely_objections": objections, "recommended_follow_up": follow_up}


def _strategy(sc: dict, sig: dict) -> tuple[str, str, int | None]:
    fit = sc["fit_score"]
    gaps = sc["reasons_against"]
    traction_gap = any("retention" in g.lower() or "revenue" in g.lower() for g in gaps)
    if fit >= 80:
        return ("Approach now — strong fit. Lead with your sharpest proof point.", "Now", None)
    if fit >= 60 and traction_gap:
        projected = min(95, fit + 25)
        return (f"Don't lead with them today — they'll likely pass on current traction. Improve the flagged metrics first, then approach.",
                "In ~75 days, after strengthening traction", projected)
    if fit >= 50:
        return ("Warm up the relationship now (follow on socials, soft intro), approach when traction firms up.", "In ~45 days", min(90, fit + 18))
    return ("Lower priority — focus on higher-fit firms first.", "Later / opportunistic", None)


def _narrative(co: dict, m: dict, firm: dict, sc: dict) -> str:
    sector = (sc["reasons_for"][0] if sc["reasons_for"] else "your category")
    proof = []
    if m.get("growth") is not None:
        proof.append(f"{ai.numfmt(m['growth'])}% MoM growth")
    if m.get("revenue"):
        proof.append(f"{fmt_money(m['revenue'])} revenue")
    if m.get("retention") is not None:
        proof.append(f"{ai.numfmt(m['retention'])}% retention")
    proofline = ", ".join(proof) or "early but fast-moving signal"
    return (f"Frame {co.get('name','the company')} as a {firm['stages'][0].lower()}-ready bet in a space {firm['firm']} "
            f"is actively backing. Lead with {proofline}. Tie the vision to their thesis: \"{firm['thesis']}\"")


def _email(co: dict, m: dict, firm: dict, warm: dict) -> str:
    partner = firm["partners"][0].split(" ")[0] if firm.get("partners") else "there"
    proof = []
    if m.get("growth") is not None:
        proof.append(f"growing {ai.numfmt(m['growth'])}% MoM")
    if m.get("revenue"):
        proof.append(f"{fmt_money(m['revenue'])} revenue")
    if m.get("customers") is not None:
        proof.append(f"{ai.numfmt(m['customers'])} customers")
    proofline = ", ".join(proof) or "strong early signal"
    intro = f"(intro via {warm['via']}) " if warm["available"] and warm["via"] else ""
    return "\n".join([
        f"Subject: {co.get('name','')} — {firm['firm']} fit",
        "",
        f"Hi {partner}, {intro}",
        "",
        f"{co.get('name','We')} is building {co.get('what','').rstrip('.') or 'something in your space'}. We're {proofline}.",
        "",
        f"Given {firm['firm']}'s focus ({firm['thesis']}), I think there's a strong fit. Open to a 30-minute conversation?",
        "",
        "Materials ready to share. Best,",
    ])


def import_firms(records: list[dict]) -> int:
    n = 0
    for r in records:
        if r.get("firm"):
            memory.investordb_upsert(r)
            n += 1
    return n
