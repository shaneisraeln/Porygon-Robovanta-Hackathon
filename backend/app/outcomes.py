"""Outcome Tracking & Strategy Feedback Loop (v3).

Closes PS-04's "Develop" stage: every Growth Agent recommendation can be
measured, and the measured result is written back into Company Memory as a
`campaign_outcome` fact. No new tables — the same additive-row pattern already
used for competitor and metric facts. These outcomes are later re-injected into
Council / Growth Agent reasoning by the context-assembly step in ai.py.
"""
from __future__ import annotations

import json

from . import memory

OUTCOME_TYPE = "campaign_outcome"
STATUS_TYPE = "rec_status"
STATES = ("recommended", "in_progress", "completed", "measured")


# ---------------- lifecycle status ----------------

def set_status(company_id: str, recommendation_id: str, status: str) -> str:
    if status not in STATES:
        raise ValueError(f"Invalid status '{status}'. Expected one of {STATES}.")
    memory.add_fact(
        company_id, STATUS_TYPE, recommendation_id, "Recommendation status", status,
        source_ref=f"Growth · {recommendation_id}", source_kind="conversation",
        evidence=f"Status set to {status}", confidence=1.0, owner="founder",
    )
    return status


def get_status(company_id: str, recommendation_id: str) -> str:
    """Latest lifecycle state for a recommendation; defaults to 'recommended'."""
    for f in memory.list_facts(company_id):  # newest first
        if f["type"] == STATUS_TYPE and f["key"] == recommendation_id:
            return f["value"]
    return "recommended"


# ---------------- outcomes ----------------

def _row_to_outcome(f: dict) -> dict:
    try:
        payload = json.loads(f["value"])
    except (ValueError, TypeError):
        payload = {}
    return {
        "recommendation_id": f["key"],
        "outcome_metric": payload.get("outcome_metric", ""),
        "outcome_value": payload.get("outcome_value", ""),
        "baseline_value": payload.get("baseline_value", ""),
        "date_range": payload.get("date_range", ""),
        "result_note": payload.get("result_note", ""),
        "logged_at": f["created_at"],
    }


def log_outcome(company_id: str, recommendation_id: str, outcome_metric: str,
                outcome_value: str, baseline_value: str, date_range: str,
                result_note: str) -> dict:
    """Write a measured result against a recommendation and close the loop."""
    payload = {
        "outcome_metric": outcome_metric,
        "outcome_value": outcome_value,
        "baseline_value": baseline_value,
        "date_range": date_range,
        "result_note": result_note,
    }
    summary = f"{outcome_metric}: {baseline_value or '—'} → {outcome_value}".strip()
    memory.add_fact(
        company_id, OUTCOME_TYPE, recommendation_id, "Campaign outcome", json.dumps(payload),
        source_ref=f"Outcome · {recommendation_id}", source_kind="conversation",
        evidence=result_note or summary, confidence=1.0, owner="founder",
    )
    # Measuring an outcome advances the lifecycle to its final state.
    set_status(company_id, recommendation_id, "measured")
    # Make the learning visible on the company timeline for the Brief/Council.
    memory.add_timeline(
        company_id, connector_id="growth", kind="Outcome",
        title=f"Outcome logged: {outcome_metric}", summary=summary,
        why="Growth recommendation measured — fed back into strategy.",
        evidence=result_note or summary, confidence=1.0,
        what_changed=summary, agents=["growth", "customer", "market"],
    )
    return _row_to_outcome({"key": recommendation_id, "value": json.dumps(payload), "created_at": memory.now()})


def get_outcomes_for_recommendation(company_id: str, recommendation_id: str) -> list[dict]:
    return [
        _row_to_outcome(f) for f in memory.list_facts(company_id)
        if f["type"] == OUTCOME_TYPE and f["key"] == recommendation_id
    ]


def get_recent_outcomes(company_id: str, limit: int = 10) -> list[dict]:
    out = [_row_to_outcome(f) for f in memory.list_facts(company_id) if f["type"] == OUTCOME_TYPE]
    return out[:limit]
