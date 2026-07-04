"""Composite growth metrics computed from Company Memory.

Currently home to the strengthened Lead Score (v3). Follows the same
weighted-composite discipline as the investor fit-score engine: every input is a
real stored fact, and the score is `None` ("insufficient data") when nothing is
on file — never fabricated.
"""
from __future__ import annotations

from . import memory


def clamp(n: float, lo: float = 0, hi: float = 100) -> int:
    return int(max(lo, min(hi, round(n))))


def _nums_for_key(facts: list[dict], key: str) -> list[float]:
    """All numeric values for a key, newest first (list_facts is DESC by time)."""
    return [f["num"] for f in facts if f["key"] == key and f["num"] is not None]


def _latest_text(facts: list[dict], key: str) -> str | None:
    for f in facts:
        if f["key"] == key and f["value"]:
            return f["value"]
    return None


def _channel_count(mix: str) -> int:
    """Count distinct lead channels named in a free-text/CSV source mix."""
    if not mix:
        return 0
    parts = [p.strip() for chunk in mix.replace("/", ",").replace("|", ",").replace(";", ",").split(",") for p in [chunk] if p.strip()]
    return len({p.lower() for p in parts})


def calc_lead_score(company_id: str) -> dict:
    """Strengthened Lead Score.

    Considers up to four inputs — `leads_monthly`, `lead_conversion_rate`,
    `lead_source_mix`, `lead_velocity_trend`. `lead_velocity_trend` is
    auto-derived from >=2 months of `leads_monthly` history when not supplied
    directly, so no new user prompt is needed after the second data point.

    Returns `{"lead_score": float|None, "inputs_used": [...], "detail": {...}}`.
    """
    facts = memory.list_facts(company_id)

    leads_hist = _nums_for_key(facts, "leads_monthly")   # newest first
    conversion = memory.latest_num(company_id, "lead_conversion_rate")
    velocity = memory.latest_num(company_id, "lead_velocity_trend")
    source_mix = _latest_text(facts, "lead_source_mix")

    inputs_used: list[str] = []
    detail: dict = {}

    # Auto-derive month-over-month velocity once >=2 months of history exist.
    velocity_auto = False
    if velocity is None and len(leads_hist) >= 2 and leads_hist[1]:
        velocity = round((leads_hist[0] - leads_hist[1]) / leads_hist[1] * 100, 1)
        velocity_auto = True

    components: list[tuple[float, float]] = []  # (weight, 0..100 score)

    # Conversion component — weighted against a nominal category benchmark.
    if conversion is not None:
        inputs_used.append("lead_conversion_rate")
        conv_score = clamp(35 + conversion * 10)  # 5% -> ~85, 2% -> ~55
        components.append((0.5, conv_score))
        detail["conversion_rate"] = conversion

    # Velocity component — month-over-month lead volume trend.
    if velocity is not None:
        inputs_used.append("lead_velocity_trend" + (" (derived)" if velocity_auto else ""))
        vel_score = clamp(55 + velocity * 1.5)  # +20% -> ~85, -10% -> ~40
        components.append((0.3, vel_score))
        detail["velocity_trend_pct"] = velocity

    # Volume component — raw monthly lead count.
    if leads_hist:
        inputs_used.append("leads_monthly")
        vol_score = clamp(45 + min(leads_hist[0], 200) * 0.2)  # 200 leads -> ~85
        components.append((0.2, vol_score))
        detail["leads_monthly"] = leads_hist[0]

    # Diversification bonus — multi-channel reduces single-channel dependency.
    diversification_bonus = 0.0
    if source_mix:
        inputs_used.append("lead_source_mix")
        channels = _channel_count(source_mix)
        detail["channels"] = channels
        if channels > 1:
            diversification_bonus = min(6.0, channels * 2.0)
        elif channels == 1:
            # Single-channel dependency is itself a risk signal for the Risk Agent.
            detail["single_channel_risk"] = True

    # No supporting fields at all -> honest "insufficient data".
    if not components and not source_mix:
        return {"lead_score": None, "inputs_used": [], "detail": {"reason": "insufficient data"}}

    if components:
        wsum = sum(w for w, _ in components)
        base = sum(w * s for w, s in components) / wsum
    else:
        # Only a source mix is known — thin, but not nothing.
        base = 50.0

    score = clamp(base + diversification_bonus)
    return {"lead_score": float(score), "inputs_used": inputs_used, "detail": detail}


# ---------------- Churn & retention (v2) ----------------

def calc_churn(company_id: str) -> dict:
    """Churn rate as a percentage, from the most authoritative source on file.

    Priority: explicit `churn_rate` -> derived from start/end customer counts ->
    inferred from `retention`. Returns `None` when none are present."""
    churn = memory.latest_num(company_id, "churn_rate")
    if churn is not None:
        return {"churn_rate": round(float(churn), 1), "source": "churn_rate"}

    start = memory.latest_num(company_id, "customers_start_of_period")
    end = memory.latest_num(company_id, "customers_end_of_period")
    if start and end is not None and start > 0:
        val = max(0.0, (start - end) / start * 100)
        return {"churn_rate": round(val, 1), "source": "customer_counts"}

    retention = memory.latest_num(company_id, "retention")
    if retention is not None:
        return {"churn_rate": round(max(0.0, 100 - retention), 1), "source": "retention"}

    return {"churn_rate": None, "source": None}


def calc_customer_health(company_id: str, m: dict) -> dict:
    """0-100 composite from churn/retention and customer base depth."""
    churn = calc_churn(company_id)["churn_rate"]
    retention = m.get("retention")
    customers = m.get("customers")

    if churn is None and retention is None:
        return {"score": None, "inputs_used": [], "detail": {"reason": "insufficient data"}}

    inputs, parts = [], []
    if retention is not None:
        inputs.append("retention")
        parts.append((0.6, clamp(retention)))
    elif churn is not None:
        inputs.append("churn_rate")
        parts.append((0.6, clamp(100 - churn)))
    if customers is not None:
        inputs.append("customers")
        parts.append((0.4, clamp(45 + min(customers, 100) * 0.5)))

    wsum = sum(w for w, _ in parts)
    score = clamp(sum(w * s for w, s in parts) / wsum) if wsum else None
    return {"score": float(score), "inputs_used": inputs, "detail": {"churn_rate": churn, "retention": retention}}


# ---------------- CAC : LTV (v2) ----------------

def calc_cac_ltv(company_id: str, m: dict) -> dict:
    """LTV = revenue-per-customer x (1 / churn). Ratio benchmarked, not hardcoded.

    Returns `None`s where inputs are missing — never fabricates the ratio."""
    cac = memory.latest_num(company_id, "cac")
    churn = calc_churn(company_id)["churn_rate"]
    revenue = m.get("revenue")
    customers = m.get("customers")

    ltv = None
    if revenue and customers and churn and churn > 0:
        arpu_annual = revenue / customers
        ltv = round(arpu_annual * (1 / (churn / 100)))

    ratio = None
    if ltv is not None and cac and cac > 0:
        ratio = round(ltv / cac, 1)

    if ratio is not None:
        verdict = "healthy" if ratio >= 3 else ("thin" if ratio >= 1 else "unsustainable")
    else:
        verdict = None

    return {"cac": cac, "ltv": ltv, "ratio": ratio, "verdict": verdict}


# ---------------- Growth score & revenue opportunity (v2) ----------------

def calc_growth_score(company_id: str, m: dict) -> dict:
    """0-100 growth composite from MoM growth and traction depth."""
    growth = m.get("growth")
    customers = m.get("customers")
    if growth is None and customers is None:
        return {"score": None, "inputs_used": [], "detail": {"reason": "insufficient data"}}

    inputs, parts = [], []
    if growth is not None:
        inputs.append("growth")
        parts.append((0.65, clamp(45 + growth * 2)))
    if customers is not None:
        inputs.append("customers")
        parts.append((0.35, clamp(45 + min(customers, 100) * 0.5)))

    wsum = sum(w for w, _ in parts)
    score = clamp(sum(w * s for w, s in parts) / wsum) if wsum else None
    return {"score": float(score), "inputs_used": inputs, "detail": {"growth": growth}}


def calc_revenue_opportunity(company_id: str, m: dict) -> dict:
    """Annualized revenue at risk to churn (the recoverable opportunity).

    Grounded in real revenue + churn; `None` when either is missing."""
    revenue = m.get("revenue")
    churn = calc_churn(company_id)["churn_rate"]
    if not revenue or churn is None:
        return {"amount": None, "detail": {"reason": "insufficient data"}}
    amount = round(revenue * (churn / 100))
    return {"amount": float(amount), "detail": {"revenue": revenue, "churn_rate": churn,
            "basis": "Annual revenue exposed to current churn — the opportunity a retention play recovers."}}
