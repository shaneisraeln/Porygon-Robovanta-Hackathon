"""CBO backend — FastAPI. All business logic lives here; the frontend is a thin
client. Every endpoint reads/writes real Company Memory."""
from __future__ import annotations

import base64
import json as _json

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from . import ai, competitors, connectors, dashboard, fundraising, growth, interview, investordb, llm, memory, metrics, outcomes, report
from .config import settings
from .db import init_db
from .extract import detect_firms, extract_onboarding
from .files import parse_file

app = FastAPI(title="CBO — AI Business Operating System", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()
    investordb.ensure_seed()


def require_company(company_id: str) -> dict:
    co = memory.get_company(company_id)
    if not co:
        raise HTTPException(404, "Company not found")
    return co


# ---------------- request models ----------------

class StartReq(BaseModel):
    name: str


class AnswerReq(BaseModel):
    company_id: str
    key: str
    text: str


class TextIngestReq(BaseModel):
    name: str = "note.txt"
    text: str


class AskReq(BaseModel):
    query: str


class CouncilReq(BaseModel):
    question: str


class ConnectReq(BaseModel):
    token: str | None = None


class DebriefReq(BaseModel):
    notes: str


class InterviewAnswerReq(BaseModel):
    question_id: str
    text: str = ""


class SkipReq(BaseModel):
    question_id: str


class OutreachReq(BaseModel):
    subject: str | None = None
    body: str | None = None


class TranscriptReq(BaseModel):
    transcript: str


class ImportFirmsReq(BaseModel):
    firms: list[dict]


class StatusReq(BaseModel):
    status: str


class OutcomeReq(BaseModel):
    outcome_metric: str
    outcome_value: str
    baseline_value: str = ""
    date_range: str = ""
    result_note: str = ""


class CompetitorReq(BaseModel):
    name: str
    features: str = ""
    pricing: str = ""
    positioning: str = ""
    notes: str = ""
    url: str = ""


# ---------------- health ----------------

@app.get("/health")
def health():
    li = llm.info()
    return {"ok": True, "llm": li["provider"], "llm_active": li["active"], "model": li["model"]}


# ---------------- onboarding ----------------

def _link_entity(company_id: str, f: dict) -> str | None:
    t = f["type"]
    if t == "product":
        return memory.upsert_entity(company_id, "product", "Product", "builds")
    if t == "customer":
        return memory.upsert_entity(company_id, "customer", "Customers", "serves")
    if t == "team":
        return memory.upsert_entity(company_id, "person", "Team", "employs")
    if t in ("money", "market"):
        return memory.upsert_entity(company_id, "metric", f["label"], "tracks")
    if t == "goal":
        return memory.upsert_entity(company_id, "goal", f["value"][:28], "pursues")
    if t == "investor":
        firms = detect_firms(f["value"])
        if firms:
            return memory.upsert_entity(company_id, "investor", firms[0], "fundraising")
        return memory.upsert_entity(company_id, "investor", "Investors", "fundraising")
    return None


@app.post("/onboarding/start")
def onboarding_start(req: StartReq):
    co = memory.create_company(req.name.strip() or "Company")
    return co


@app.post("/onboarding/answer")
def onboarding_answer(req: AnswerReq):
    require_company(req.company_id)
    facts = extract_onboarding(req.key, req.text)
    captured = []
    for f in facts:
        eid = _link_entity(req.company_id, f)
        memory.add_fact(req.company_id, f["type"], f["key"], f["label"], f["value"],
                        source_ref=f"Onboarding · {req.key}", num=f.get("num"), entity_id=eid,
                        source_kind="conversation", evidence=f.get("evidence", ""), confidence=f.get("confidence", 0.8), owner="founder")
        captured.append({"label": f["label"], "value": f["value"]})

    if req.key == "what":
        memory.update_company(req.company_id, what=req.text.strip())
    elif req.key == "customers":
        memory.update_company(req.company_id, customers=req.text.strip())
    elif req.key == "stage":
        memory.update_company(req.company_id, stage=req.text.strip())
    elif req.key == "investors":
        for firm in detect_firms(req.text):
            memory.upsert_investor(req.company_id, firm, name=firm, state="need-intro", probability=40, warmth=40, concerns=["Why now", "Traction"])

    return {"captured": captured}


# ---------------- company / memory reads ----------------

@app.get("/companies/{company_id}")
def get_company(company_id: str):
    co = require_company(company_id)
    return {**co, "counts": memory.counts(company_id)}


@app.get("/companies/{company_id}/brief")
def get_brief(company_id: str):
    co = require_company(company_id)
    m = ai.derive_metrics(company_id)
    return {"company": co, "metrics": m, "summary": ai.summarize_metrics(m), "items": ai.brief_generate(company_id)}


@app.post("/companies/{company_id}/brain/ask")
def brain_ask(company_id: str, req: AskReq):
    require_company(company_id)
    return ai.brain_ask(company_id, req.query)


@app.get("/companies/{company_id}/graph")
def get_graph(company_id: str):
    require_company(company_id)
    return memory.graph(company_id)


@app.get("/companies/{company_id}/facts")
def get_facts(company_id: str):
    require_company(company_id)
    return {"facts": memory.list_facts(company_id)}


@app.get("/companies/{company_id}/entity/{entity_id}/facts")
def get_entity_facts(company_id: str, entity_id: str):
    require_company(company_id)
    return {"facts": memory.facts_for_entity(company_id, entity_id)}


@app.get("/companies/{company_id}/timeline")
def get_timeline(company_id: str):
    require_company(company_id)
    return {"timeline": memory.list_timeline(company_id)}


@app.get("/companies/{company_id}/counts")
def get_counts(company_id: str):
    require_company(company_id)
    return memory.counts(company_id)


# ---------------- connectors / sources ----------------

@app.get("/companies/{company_id}/connectors")
def get_connectors(company_id: str):
    require_company(company_id)
    states = memory.list_connector_states(company_id)
    out = []
    for c in connectors.connector_catalog():
        st = states.get(c["id"], {})
        has_cred = bool(memory.get_credential(company_id, c["id"])) or (not c["requires_credential"])
        out.append({**c, "connected": bool(st.get("connected", 0)), "last_sync": st.get("last_sync"),
                    "record_count": st.get("record_count", 0), "has_credential": has_cred})
    return {"connectors": out, "counts": memory.counts(company_id)}


@app.post("/companies/{company_id}/connectors/{connector_id}/connect")
def connect(company_id: str, connector_id: str, req: ConnectReq):
    require_company(company_id)
    cls = connectors.REGISTRY.get(connector_id)
    if not cls:
        raise HTTPException(404, "Unknown connector")
    token = req.token or memory.get_credential(company_id, connector_id) or getattr(settings, f"{connector_id}_token", None)
    if cls.requires_credential and not token:
        memory.set_connector_state(company_id, connector_id, connected=0, has_credential=0)
        return {"status": "needs_auth", "message": f"{cls.name} needs an access token to sync real data. No data is fabricated."}
    if req.token:
        memory.save_credential(company_id, connector_id, req.token)
    inst = cls(company_id, token=token)
    summary = inst.run()
    memory.set_connector_state(company_id, connector_id, connected=1, last_sync=memory.now(),
                               cursor=summary.get("cursor", ""), record_count=summary.get("records", 0),
                               has_credential=1 if token else 0)
    return {"status": "connected", "summary": summary, "counts": memory.counts(company_id)}


@app.post("/companies/{company_id}/connectors/{connector_id}/sync")
def sync(company_id: str, connector_id: str):
    require_company(company_id)
    cls = connectors.REGISTRY.get(connector_id)
    if not cls:
        raise HTTPException(404, "Unknown connector")
    token = memory.get_credential(company_id, connector_id) or getattr(settings, f"{connector_id}_token", None)
    if cls.requires_credential and not token:
        return {"status": "needs_auth"}
    st = memory.get_connector_state(company_id, connector_id) or {}
    inst = cls(company_id, token=token, cursor=st.get("cursor", ""))
    summary = inst.run()
    prior = st.get("record_count", 0)
    memory.set_connector_state(company_id, connector_id, connected=1, last_sync=memory.now(),
                               cursor=summary.get("cursor", ""), record_count=prior + summary.get("records", 0))
    return {"status": "synced", "summary": summary, "counts": memory.counts(company_id)}


@app.post("/companies/{company_id}/connectors/{connector_id}/disconnect")
def disconnect(company_id: str, connector_id: str):
    require_company(company_id)
    memory.set_connector_state(company_id, connector_id, connected=0)
    return {"status": "disconnected"}


# ---------------- ingestion (manual) ----------------

@app.post("/companies/{company_id}/ingest/text")
def ingest_text(company_id: str, req: TextIngestReq):
    require_company(company_id)
    summary = connectors.ingest_records(company_id, "upload", [{"kind": "document", "at": memory.now(), "name": req.name, "text": req.text}])
    memory.set_connector_state(company_id, "upload", connected=1, last_sync=memory.now(), has_credential=1)
    return {"summary": summary, "counts": memory.counts(company_id)}


@app.post("/companies/{company_id}/ingest/upload")
async def ingest_upload(company_id: str, file: UploadFile = File(...)):
    require_company(company_id)
    data = await file.read()
    text = parse_file(file.filename or "upload", data)
    if not text.strip():
        raise HTTPException(422, "Could not extract text from this file.")
    summary = connectors.ingest_records(company_id, "upload", [{"kind": "document", "at": memory.now(), "name": file.filename, "text": text}])
    memory.set_connector_state(company_id, "upload", connected=1, last_sync=memory.now(), has_credential=1)
    return {"summary": summary, "chars": len(text), "counts": memory.counts(company_id)}


# ---------------- council ----------------

@app.post("/companies/{company_id}/council/ask")
def council(company_id: str, req: CouncilReq):
    require_company(company_id)
    if not req.question.strip():
        raise HTTPException(400, "A question is required")
    return ai.council_run(company_id, req.question)


# ---------------- investors ----------------

@app.get("/companies/{company_id}/investors")
def investors(company_id: str):
    require_company(company_id)
    invs = memory.list_investors(company_id)
    m = ai.derive_metrics(company_id)
    return {"investors": invs, "metrics": m}


@app.get("/companies/{company_id}/investors/{investor_id}")
def investor_detail(company_id: str, investor_id: str):
    require_company(company_id)
    inv = memory.get_investor(company_id, investor_id)
    if not inv:
        raise HTTPException(404, "Investor not found")
    return {"investor": inv, "next_best_action": ai.next_best_action(inv),
            "meeting_prep": ai.meeting_prep(company_id, inv), "draft_followup": ai.draft_followup(company_id, inv)}


@app.post("/companies/{company_id}/investors/{investor_id}/debrief")
def investor_debrief(company_id: str, investor_id: str, req: DebriefReq):
    require_company(company_id)
    inv = memory.get_investor(company_id, investor_id)
    if not inv:
        raise HTTPException(404, "Investor not found")
    d = ai.debrief(company_id, inv, req.notes)
    memory.add_investor_event(company_id, inv["firm"], d["summary"], d["sentiment"], "")
    memory.add_fact(company_id, "meeting", "meeting", "Investor meeting", d["summary"],
                    source_ref="Meeting debrief", source_kind="conversation", evidence=d["summary"], confidence=0.9, owner="founder")
    memory.add_timeline(company_id, connector_id="meeting", kind="Meeting debrief", title=f"Debrief: {inv['firm']}",
                        summary=d["summary"], who=[inv["firm"]], why="Meeting outcome recorded", evidence=d["summary"],
                        confidence=0.9, what_changed=f"Sentiment: {d['sentiment']}", agents=["fundraising", "investor"])
    return d


# ---------------- dynamic interview ----------------

@app.get("/companies/{company_id}/interview/next")
def interview_next(company_id: str):
    require_company(company_id)
    q = interview.next_question(company_id)
    return {"question": q, "profile": interview.profile(company_id), "done": q is None}


@app.post("/companies/{company_id}/interview/answer")
def interview_answer(company_id: str, req: InterviewAnswerReq):
    require_company(company_id)
    captured = interview.record_answer(company_id, req.question_id, req.text)
    q = interview.next_question(company_id)
    return {"captured": captured, "question": q, "profile": interview.profile(company_id), "done": q is None}


@app.post("/companies/{company_id}/interview/skip")
def interview_skip(company_id: str, req: SkipReq):
    require_company(company_id)
    interview.skip(company_id, req.question_id)
    q = interview.next_question(company_id)
    return {"question": q, "profile": interview.profile(company_id), "done": q is None}


@app.get("/companies/{company_id}/profile")
def get_profile(company_id: str):
    require_company(company_id)
    return interview.profile(company_id)


# ---------------- fundraising operating system ----------------

@app.get("/companies/{company_id}/fundraising/pipeline")
def fundraising_pipeline(company_id: str):
    require_company(company_id)
    return fundraising.pipeline_status(company_id)


@app.get("/companies/{company_id}/fundraising/readiness")
def fundraising_readiness(company_id: str):
    require_company(company_id)
    return fundraising.readiness(company_id)


@app.post("/companies/{company_id}/fundraising/deck")
def fundraising_deck(company_id: str):
    require_company(company_id)
    return fundraising.generate_pitch_deck(company_id)


@app.get("/companies/{company_id}/fundraising/deck")
def fundraising_get_deck(company_id: str):
    require_company(company_id)
    return memory.latest_artifact(company_id, "pitch_deck") or {"content": None}


@app.post("/companies/{company_id}/fundraising/financial-model")
def fundraising_model(company_id: str):
    require_company(company_id)
    return fundraising.generate_financial_model(company_id)


@app.get("/companies/{company_id}/fundraising/investors")
def fundraising_investors(company_id: str):
    require_company(company_id)
    return fundraising.investor_pipeline(company_id)


@app.get("/companies/{company_id}/fundraising/data-room")
def fundraising_dataroom(company_id: str):
    require_company(company_id)
    return fundraising.data_room(company_id)


@app.get("/companies/{company_id}/fundraising/outreach")
def fundraising_outreach(company_id: str):
    require_company(company_id)
    return {"outreach": fundraising.outreach_board(company_id)}


@app.post("/companies/{company_id}/fundraising/outreach/{investor_id}/draft")
def fundraising_draft(company_id: str, investor_id: str):
    require_company(company_id)
    return fundraising.draft_outreach(company_id, investor_id)


@app.post("/companies/{company_id}/fundraising/outreach/{investor_id}/approve")
def fundraising_approve(company_id: str, investor_id: str):
    require_company(company_id)
    memory.set_outreach_status(company_id, investor_id, "approved")
    return {"status": "approved"}


@app.post("/companies/{company_id}/fundraising/outreach/{investor_id}/send")
def fundraising_send(company_id: str, investor_id: str):
    require_company(company_id)
    return fundraising.send_outreach(company_id, investor_id)


@app.post("/companies/{company_id}/fundraising/meeting/{investor_id}/transcript")
def fundraising_transcript(company_id: str, investor_id: str, req: TranscriptReq):
    require_company(company_id)
    inv = memory.get_investor(company_id, investor_id)
    if not inv:
        raise HTTPException(404, "Investor not found")
    return fundraising.process_transcript(company_id, inv, req.transcript)


# ---------------- Investor Intelligence Network ----------------

@app.get("/network/stats")
def network_stats():
    investordb.ensure_seed()
    return {"firms": memory.investordb_count()}


@app.post("/network/import")
def network_import(req: ImportFirmsReq):
    n = investordb.import_firms(req.firms)
    return {"imported": n, "total": memory.investordb_count()}


@app.get("/companies/{company_id}/network/discover")
def network_discover(company_id: str):
    require_company(company_id)
    return investordb.discover(company_id)


@app.get("/companies/{company_id}/network/{firm_id}")
def network_research(company_id: str, firm_id: str):
    require_company(company_id)
    r = investordb.research(company_id, firm_id)
    if not r:
        raise HTTPException(404, "Firm not found")
    return r


@app.post("/companies/{company_id}/network/{firm_id}/approach")
def network_approach(company_id: str, firm_id: str):
    require_company(company_id)
    firm = memory.investordb_get(firm_id)
    if not firm:
        raise HTTPException(404, "Firm not found")
    r = investordb.research(company_id, firm_id)
    fit = r["fit"]
    iid = memory.upsert_investor(company_id, firm["firm"], name=firm["partners"][0] if firm.get("partners") else firm["firm"],
                                 partner=firm["partners"][0] if firm.get("partners") else "", sector=", ".join(firm.get("industries", [])[:3]),
                                 stage=", ".join(firm.get("stages", [])[:2]), state="need-intro" if not r["warm_intro"]["available"] else "warm",
                                 probability=fit["probability"], warmth=50 if r["warm_intro"]["available"] else 35,
                                 concerns=fit["reasons_against"][:3] or ["Why now"])
    # Draft outreach immediately — "Just approve."
    memory.upsert_outreach(company_id, iid, f"{memory.get_company(company_id)['name']} — {firm['firm']} fit", r["suggested_email"], "drafted")
    memory.add_timeline(company_id, connector_id="cbo", kind="Investor", title=f"Added {firm['firm']} to pipeline",
                        summary=f"Fit {fit['fit_score']}% · outreach drafted.", who=[firm["firm"]], why="CBO recommended approach",
                        evidence=r["suggested_strategy"], confidence=0.8, what_changed="Investor entered active pipeline", agents=["fundraising", "investor"])
    return {"investor_id": iid, "fit": fit, "drafted": True}


# ---------------- Growth Agent & Outcome Tracking (v3) ----------------

@app.get("/companies/{company_id}/growth/recommendations")
def growth_recommendations(company_id: str):
    require_company(company_id)
    return growth.generate_recommendations(company_id)


@app.post("/companies/{company_id}/growth/recommendations/{rid}/status")
def growth_set_status(company_id: str, rid: str, req: StatusReq):
    require_company(company_id)
    try:
        status = outcomes.set_status(company_id, rid, req.status)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"recommendation_id": rid, "status": status}


@app.post("/companies/{company_id}/growth/recommendations/{rid}/outcome")
def growth_log_outcome(company_id: str, rid: str, req: OutcomeReq):
    require_company(company_id)
    return outcomes.log_outcome(company_id, rid, req.outcome_metric, req.outcome_value,
                                req.baseline_value, req.date_range, req.result_note)


@app.get("/companies/{company_id}/growth/outcomes")
def growth_outcomes(company_id: str):
    require_company(company_id)
    return {"outcomes": outcomes.get_recent_outcomes(company_id, limit=50)}


@app.get("/companies/{company_id}/leads/score")
def leads_score(company_id: str):
    require_company(company_id)
    return metrics.calc_lead_score(company_id)


# ---------------- Business Intelligence Dashboard v2 ----------------

@app.get("/companies/{company_id}/dashboard")
def get_dashboard(company_id: str):
    require_company(company_id)
    return dashboard.build_dashboard(company_id)


# ---------------- Growth Engines (6-engine hub) ----------------

from .engines import (strategy as eng_strategy, marketing as eng_marketing,  # noqa: E402
                      leadgen as eng_leadgen, sales as eng_sales,
                      analytics as eng_analytics, success as eng_success)


class ChatReq(BaseModel):
    message: str


class TicketReq(BaseModel):
    subject: str
    body: str


class DealReq(BaseModel):
    name: str
    value: float = 0
    stage: str = "Lead"


class DealStageReq(BaseModel):
    stage: str


class WhatsAppReq(BaseModel):
    to: str


class OAuthAppReq(BaseModel):
    client_id: str
    client_secret: str


# Strategy
@app.get("/companies/{company_id}/engines/strategy")
def engine_strategy_get(company_id: str):
    require_company(company_id)
    return eng_strategy.latest(company_id) or {"empty": True}


@app.post("/companies/{company_id}/engines/strategy")
def engine_strategy_generate(company_id: str):
    require_company(company_id)
    return eng_strategy.generate(company_id)


# Marketing
@app.get("/companies/{company_id}/engines/marketing")
def engine_marketing_get(company_id: str):
    require_company(company_id)
    return eng_marketing.latest(company_id) or {"empty": True}


@app.post("/companies/{company_id}/engines/marketing")
def engine_marketing_generate(company_id: str):
    require_company(company_id)
    return eng_marketing.generate(company_id)


# Lead Gen
@app.get("/companies/{company_id}/engines/leadgen")
def engine_leadgen_get(company_id: str):
    require_company(company_id)
    return eng_leadgen.latest(company_id) or {"empty": True}


@app.post("/companies/{company_id}/engines/leadgen")
def engine_leadgen_generate(company_id: str):
    require_company(company_id)
    return eng_leadgen.generate(company_id)


# Sales
@app.get("/companies/{company_id}/engines/sales")
def engine_sales_get(company_id: str):
    require_company(company_id)
    return eng_sales.latest(company_id) or {"empty": True}


@app.post("/companies/{company_id}/engines/sales")
def engine_sales_generate(company_id: str):
    require_company(company_id)
    return eng_sales.generate(company_id)


# Analytics
@app.get("/companies/{company_id}/engines/analytics")
def engine_analytics_get(company_id: str):
    require_company(company_id)
    return eng_analytics.live(company_id)


@app.post("/companies/{company_id}/engines/analytics")
def engine_analytics_generate(company_id: str):
    require_company(company_id)
    return eng_analytics.generate(company_id)


# Customer Success
@app.get("/companies/{company_id}/engines/success")
def engine_success_get(company_id: str):
    require_company(company_id)
    return {**eng_success.overview(company_id), "faqs": eng_success.faqs(company_id)}


@app.post("/companies/{company_id}/engines/success/chat")
def engine_success_chat(company_id: str, req: ChatReq):
    require_company(company_id)
    if not req.message.strip():
        raise HTTPException(400, "A message is required")
    return eng_success.chat(company_id, req.message)


@app.post("/companies/{company_id}/engines/success/ticket")
def engine_success_ticket(company_id: str, req: TicketReq):
    require_company(company_id)
    if not req.subject.strip():
        raise HTTPException(400, "A subject is required")
    return eng_success.add_ticket(company_id, req.subject, req.body)


@app.post("/companies/{company_id}/engines/success/faqs")
def engine_success_faqs(company_id: str):
    require_company(company_id)
    return {"faqs": eng_success.generate_faqs(company_id)}


@app.get("/companies/{company_id}/engines/success/brief")
def engine_success_brief_get(company_id: str):
    require_company(company_id)
    return eng_success.latest(company_id) or {"empty": True}


@app.post("/companies/{company_id}/engines/success/brief")
def engine_success_brief_gen(company_id: str):
    require_company(company_id)
    return eng_success.generate(company_id)


# ---------------- Sales deal pipeline ----------------

@app.get("/companies/{company_id}/deals")
def get_deals(company_id: str):
    require_company(company_id)
    return {"deals": memory.list_deals(company_id), "metrics": memory.deal_metrics(company_id),
            "stages": memory.DEAL_STAGES}


@app.post("/companies/{company_id}/deals")
def create_deal(company_id: str, req: DealReq):
    require_company(company_id)
    if not req.name.strip():
        raise HTTPException(400, "A deal name is required")
    return memory.create_deal(company_id, req.name.strip(), req.value, req.stage)


@app.post("/companies/{company_id}/deals/{deal_id}/stage")
def move_deal(company_id: str, deal_id: str, req: DealStageReq):
    require_company(company_id)
    d = memory.move_deal(company_id, deal_id, req.stage)
    if not d:
        raise HTTPException(404, "Deal not found")
    return d


# ---------------- Consolidated executive report → WhatsApp ----------------

@app.get("/companies/{company_id}/report")
def report_preview(company_id: str):
    require_company(company_id)
    return {"report": report.generate_report(company_id)}


@app.post("/companies/{company_id}/report/whatsapp")
def report_whatsapp(company_id: str, req: WhatsAppReq):
    require_company(company_id)
    if not req.to.strip():
        raise HTTPException(400, "A recipient WhatsApp number is required (e.g. +919876543210)")
    return report.send_whatsapp(company_id, req.to)


# ---------------- integration setup (OAuth apps, managed from the UI, not .env) ----------------

@app.get("/settings/integrations")
def list_integrations():
    out = []
    for provider, info in connectors.OAUTH_PROVIDER_INFO.items():
        out.append({"provider": provider, "name": info["name"], "enables": info["enables"],
                    "configured": bool(connectors.resolve_oauth_client(provider))})
    return {"integrations": out, "redirect_uri": connectors._redirect_uri()}


@app.post("/settings/integrations/{provider}")
def save_integration(provider: str, req: OAuthAppReq):
    if provider not in connectors.OAUTH_PROVIDER_INFO:
        raise HTTPException(404, "Unknown provider")
    if not (req.client_id.strip() and req.client_secret.strip()):
        raise HTTPException(400, "Both client ID and client secret are required")
    memory.set_oauth_app(provider, req.client_id.strip(), req.client_secret.strip())
    return {"provider": provider, "configured": True}


@app.delete("/settings/integrations/{provider}")
def delete_integration(provider: str):
    memory.delete_oauth_app(provider)
    return {"provider": provider, "configured": bool(connectors.resolve_oauth_client(provider))}


# ---------------- Competitor Analysis (v2) ----------------

@app.get("/companies/{company_id}/competitors")
def get_competitors(company_id: str):
    require_company(company_id)
    return competitors.comparison(company_id)


@app.post("/companies/{company_id}/competitors")
def add_competitor(company_id: str, req: CompetitorReq):
    require_company(company_id)
    if not req.name.strip():
        raise HTTPException(400, "A competitor name is required")
    competitors.add_competitor(company_id, req.name.strip(), req.features, req.pricing, req.positioning, req.notes, req.url)
    return competitors.comparison(company_id)


@app.post("/companies/{company_id}/competitors/discover")
def discover_competitors(company_id: str):
    require_company(company_id)
    return competitors.discover_competitors(company_id)


# ---------------- OAuth one-click connect ----------------

def _oauth_state(company_id: str, connector_id: str) -> str:
    raw = _json.dumps({"c": company_id, "k": connector_id}).encode()
    return base64.urlsafe_b64encode(raw).decode()


def _decode_state(state: str) -> dict:
    try:
        return _json.loads(base64.urlsafe_b64decode(state.encode()).decode())
    except Exception:
        return {}


@app.get("/companies/{company_id}/connectors/{connector_id}/oauth/start")
def oauth_start(company_id: str, connector_id: str):
    require_company(company_id)
    if connector_id not in connectors.REGISTRY:
        raise HTTPException(404, "Unknown connector")
    if not connectors.oauth_supported(connector_id):
        return {"configured": False,
                "message": f"One-click sign-in isn't configured for {connector_id}. Set its CLIENT_ID/CLIENT_SECRET in the backend .env, or paste a token."}
    url = connectors.oauth_authorize_url(connector_id, _oauth_state(company_id, connector_id))
    return {"configured": True, "authorize_url": url}


@app.get("/oauth/callback")
def oauth_callback(code: str = "", state: str = ""):
    st = _decode_state(state)
    company_id, connector_id = st.get("c"), st.get("k")
    front = settings.frontend_base.rstrip("/")
    if not (code and company_id and connector_id):
        return RedirectResponse(f"{front}/sources?connect=error")
    token = connectors.oauth_exchange(connector_id, code)
    if not token:
        return RedirectResponse(f"{front}/sources?connect=failed")
    memory.save_credential(company_id, connector_id, token)
    cls = connectors.REGISTRY.get(connector_id)
    try:
        summary = cls(company_id, token=token).run()
        memory.set_connector_state(company_id, connector_id, connected=1, last_sync=memory.now(),
                                   cursor=summary.get("cursor", ""), record_count=summary.get("records", 0), has_credential=1)
    except Exception:
        memory.set_connector_state(company_id, connector_id, connected=1, last_sync=memory.now(), has_credential=1)
    return RedirectResponse(f"{front}/sources?connect=success&source={connector_id}")
