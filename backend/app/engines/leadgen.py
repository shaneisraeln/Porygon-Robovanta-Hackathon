"""Lead Gen Engine — ranked acquisition tactics, honest about channel fit."""
from __future__ import annotations

from .. import research
from . import base

KIND = "engine_leadgen"

_SYSTEM = (
    "You are a lead generation specialist focused on scrappy, high-fit acquisition tactics — digital ads, "
    "WhatsApp/messaging campaigns, referral programs, and physical/local marketing — for small businesses "
    "without big ad budgets.\n"
    "Rules:\n"
    "- Only recommend WhatsApp tactics if a fact suggests the audience uses WhatsApp (region, community, behavior).\n"
    "- Only recommend physical/offline tactics if a fact indicates a physical presence, location, or in-person "
    "community.\n"
    "- If lead sources are concentrated in one channel, flag this as a risk before suggesting new tactics.\n"
    "- Rank tactics by effort-to-impact — cheapest, fastest wins first.\n"
    "- If a channel has zero supporting evidence, list it under withheld_channels instead of guessing.\n"
    "- Tone: direct and tactical — a founder should act on this today.\n"
    "Return valid JSON only, matching this schema:\n"
    '{"channel_risk_flag": str | null,'
    ' "recommendations": [{"channel": "digital|whatsapp|physical|referral", "tactic": str, "rationale": str, "confidence": "high|medium|low"}],'
    ' "withheld_channels": [{"channel": str, "reason": str}]}'
)


def _query(ctx: dict) -> str:
    c, f = ctx["company"], ctx["facts"]
    return f"where to find {c['customers'] or 'customers'} for {c['what'] or c['name']} {f['geography']}".strip()


def _india_or_local(ctx: dict) -> bool:
    geo = (ctx["facts"]["geography"] or "").lower()
    return any(w in geo for w in ("india", "local", "city", "region", "sea", "asia", "africa", "latam"))


def _heuristic(company_id: str, ctx: dict) -> dict:
    c, f = ctx["company"], ctx["facts"]
    cust = c["customers"] or "your customers"
    recs, withheld = [], []

    # Channel concentration risk.
    mix = f["lead_source_mix"]
    risk = None
    from ..metrics import _channel_count
    if mix and _channel_count(mix) == 1:
        risk = f"All leads come from one channel ({mix}) — diversify before it saturates."

    recs.append({"channel": "referral", "tactic": "Ask every happy customer for 2 referrals with a small reward.",
                 "rationale": "Cheapest, highest-trust channel for an early business.", "confidence": "high"})
    recs.append({"channel": "digital", "tactic": f"Run one targeted campaign aimed at {cust} with a single clear offer.",
                 "rationale": "Reaches your buyer directly; start with a small test budget.", "confidence": "medium"})

    # WhatsApp only if audience likely uses it.
    if _india_or_local(ctx):
        recs.append({"channel": "whatsapp", "tactic": "Run a WhatsApp broadcast to interested contacts with a short offer + one follow-up.",
                     "rationale": f"Your market ({f['geography']}) commonly uses WhatsApp.", "confidence": "medium"})
    else:
        withheld.append({"channel": "whatsapp", "reason": "No signal your audience uses WhatsApp — add region/community facts."})

    # Physical only if a location/community signal exists.
    if f["geography"] or "shop" in (c["what"] or "").lower() or "store" in (c["what"] or "").lower():
        recs.append({"channel": "physical", "tactic": "Attend or host a local event / partner with a nearby business.",
                     "rationale": "You have a local/physical signal on file.", "confidence": "low"})
    else:
        withheld.append({"channel": "physical", "reason": "No physical presence or local community on file."})

    return {"channel_risk_flag": risk, "recommendations": recs, "withheld_channels": withheld}


def generate(company_id: str) -> dict:
    base_ctx = base.company_context(company_id)
    ctx = base.company_context(company_id, web_query=_query(base_ctx))
    return base.run_engine(company_id, KIND, "Lead generation plan", _SYSTEM, ctx, _heuristic)


def latest(company_id: str) -> dict | None:
    return base.load_or_note(company_id, KIND)
