"""Sales Engine — pipeline review over the real deal pipeline (not lead-gen)."""
from __future__ import annotations

import json

from .. import memory
from . import base

KIND = "engine_sales"

# Deals sitting longer than this in a stage get flagged as needing action.
_STALE_DAYS = {"Lead": 7, "Qualified": 10, "Demo": 7, "Proposal": 10}

_SYSTEM = (
    "You are a sales operations coach helping a small business convert leads already in their pipeline — "
    "you don't generate new leads (a separate system does that), you help close the ones that exist.\n"
    "Rules:\n"
    "- Base every recommendation on actual pipeline data: stage, time-in-stage, historical conversion patterns.\n"
    "- Compare deals against the business's OWN historical averages, not generic benchmarks, unless no history exists.\n"
    "- Flag urgency clearly: which deals need action NOW vs. which are on track.\n"
    "- If there isn't enough deal history to establish a pattern, say so rather than inventing a 'typical' cycle.\n"
    "- Tone: a no-nonsense sales manager doing a pipeline review — short, action-first sentences.\n"
    "Return valid JSON only, matching this schema:\n"
    '{"urgent_actions": [{"deal_id": str, "deal_name": str, "stage": str, "days_in_stage": number, "recommended_action": str, "rationale": str}],'
    ' "on_track": [{"deal_id": str, "deal_name": str, "stage": str}],'
    ' "pipeline_insight": str, "insufficient_data_flags": [str]}'
)


def _context(company_id: str) -> tuple[dict, str]:
    deals = memory.list_deals(company_id)
    metrics = memory.deal_metrics(company_id)
    outcomes = base._recent_outcomes(company_id)
    open_deals = [d for d in deals if d["status"] == "open"]

    lines = [f"Open deals: {len(open_deals)} | won: {metrics['won']} | lost: {metrics['lost']} | win rate: {metrics['win_rate']}%" if metrics["win_rate"] is not None else f"Open deals: {len(open_deals)} (no closed deals yet)"]
    lines.append("Pipeline:")
    for d in open_deals:
        lines.append(f"  - id={d['id']} | {d['name']} | stage={d['stage']} | days_in_stage={d['days_in_stage']} | value={d['value']}")
    if metrics["avg_stage_transition_days"]:
        lines.append("Historical avg days between stages: " + ", ".join(f"{k}={v}" for k, v in metrics["avg_stage_transition_days"].items()))
    else:
        lines.append("No historical stage-transition data yet.")
    if outcomes:
        lines.append("Recent outcomes: " + "; ".join(outcomes))
    ctx = {"deals": deals, "metrics": metrics, "open_deals": open_deals}
    return ctx, "\n".join(lines)


def _heuristic(company_id: str, ctx: dict) -> dict:
    open_deals = ctx["open_deals"]
    metrics = ctx["metrics"]
    flags = []
    if not open_deals:
        flags.append("No open deals in the pipeline — add deals to get a review.")
    if metrics["data_points"] < 4:
        flags.append("Not enough deal history yet to establish reliable stage-cycle patterns.")

    urgent, on_track = [], []
    for d in open_deals:
        limit = _STALE_DAYS.get(d["stage"], 14)
        if d["days_in_stage"] >= limit:
            urgent.append({"deal_id": d["id"], "deal_name": d["name"], "stage": d["stage"],
                           "days_in_stage": d["days_in_stage"],
                           "recommended_action": f"Follow up now — it's been {d['days_in_stage']} days in {d['stage']}.",
                           "rationale": f"Exceeds the {limit}-day mark for the {d['stage']} stage; momentum is decaying."})
        else:
            on_track.append({"deal_id": d["id"], "deal_name": d["name"], "stage": d["stage"]})

    insight = (f"{len(open_deals)} open deals; {len(urgent)} need action now."
               + (f" Win rate {metrics['win_rate']}%." if metrics["win_rate"] is not None else "")) if open_deals else "Pipeline is empty."
    return {"urgent_actions": urgent, "on_track": on_track, "pipeline_insight": insight, "insufficient_data_flags": flags}


def generate(company_id: str) -> dict:
    ctx, ctx_text = _context(company_id)
    return base.run_engine(company_id, KIND, "Pipeline review", _SYSTEM, ctx, _heuristic, ctx_text=ctx_text)


def latest(company_id: str) -> dict | None:
    return base.load_or_note(company_id, KIND)
