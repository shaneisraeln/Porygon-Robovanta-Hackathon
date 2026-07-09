"""Marketing Engine — channel-by-channel 360° plan, grounded and honest."""
from __future__ import annotations

from . import base

KIND = "engine_marketing"

_CHANNELS = ["content_seo", "paid", "organic_social", "pr_partnerships", "brand"]

_SYSTEM = (
    "You are a 360-degree marketing strategist. You design multi-channel promotion plans — content, paid, "
    "organic social, PR/partnerships, and brand — for early-stage businesses with limited budgets and no "
    "dedicated marketing team.\n"
    "Rules:\n"
    "- One tactic per channel category, but only if the facts support it.\n"
    "- If there's no data to justify a channel (e.g. no past ad spend), set its status to 'insufficient_data' "
    "rather than generic textbook copy.\n"
    "- Every tactic must cite which specific fact makes it a good fit for THIS business — no interchangeable "
    "advice that could apply to any company.\n"
    "- Make tactics executable this week — specific, scrappy, low-cost-first.\n"
    "- Tone: energetic and concrete, like a growth marketer who's actually run small budgets.\n"
    "Return valid JSON only, matching this schema (every channel is an object):\n"
    '{"channels": {"content_seo": {"status": "ok|insufficient_data", "tactic": str, "rationale": str, "confidence": "high|medium|low"},'
    ' "paid": {...}, "organic_social": {...}, "pr_partnerships": {...}, "brand": {...}}}'
)


def _ch(status, tactic="", rationale="", conf="low"):
    return {"status": status, "tactic": tactic, "rationale": rationale, "confidence": conf}


def _heuristic(company_id: str, ctx: dict) -> dict:
    c, f = ctx["company"], ctx["facts"]
    what = c["what"] or "your product"
    cust = c["customers"] or "your ideal customers"
    channels = {}

    channels["content_seo"] = _ch("ok", f"Publish one problem-solving article a week for {cust}.",
                                   f"Grounded in your product ({what}); content compounds with no ad spend.", "medium")
    # Paid: only if there's existing acquisition/ad signal.
    if f["acquisition_channels"] and any(w in f["acquisition_channels"].lower() for w in ("ad", "paid", "google", "meta", "facebook", "instagram")):
        channels["paid"] = _ch("ok", "Run a small, tightly-targeted ad set with one clear offer.",
                                f"You already use paid channels ({f['acquisition_channels']}).", "medium")
    else:
        channels["paid"] = _ch("insufficient_data")
    channels["organic_social"] = _ch("ok", "Post 3x/week: tips, customer proof, behind-the-scenes.",
                                     "Low-cost awareness that fits an early-stage budget.", "medium")
    if ctx["competitors"] or ctx["where_you_win"]:
        channels["pr_partnerships"] = _ch("ok", "Partner with a complementary business for cross-referrals.",
                                          "You have a differentiator worth co-marketing.", "low")
    else:
        channels["pr_partnerships"] = _ch("insufficient_data")
    if c["what"]:
        channels["brand"] = _ch("ok", f"Nail one consistent message: '{what} for {cust}'.",
                                "A clear message beats scattered branding at your stage.", "medium")
    else:
        channels["brand"] = _ch("insufficient_data")
    return {"channels": channels}


def generate(company_id: str) -> dict:
    ctx = base.company_context(company_id)
    return base.run_engine(company_id, KIND, "Marketing plan", _SYSTEM, ctx, _heuristic)


def latest(company_id: str) -> dict | None:
    return base.load_or_note(company_id, KIND)
