# CBO — Progress Tracker

Living checklist. We mark each item done as we finish it.
**Legend:** ✅ done · 🟡 in progress · ⬜ not started · 🔵 needs your input

_Last updated: session start of engine build._

---

## Phase 0 — Foundation (already built) ✅

- [x] Company Memory (facts, entities, relationships, timeline, artifacts)
- [x] Onboarding / interview engine (stage-aware) + churn & lead questions
- [x] Company Brain (grounded Q&A, knowledge graph, timeline)
- [x] Connectors: Gmail, Calendar, Drive, GitHub, Notion, Slack, Stripe, upload
- [x] Connectors: Instagram, Facebook
- [x] OAuth "sign-in" scaffolding (activates with provider keys; token fallback)
- [x] Executive Council — 9 agents + named frameworks
- [x] Business Dashboard v2 — 9 KPI tiles + executive summary
- [x] Metrics: Lead Score, Churn, Customer Health, CAC:LTV, Growth Score, Revenue Opportunity
- [x] Competitor Analysis (manual + web auto-discovery)
- [x] Growth Agent — recommendations with playbooks, lifecycle, outcome loop
- [x] Web Research layer (keyless DuckDuckGo + optional providers)
- [x] Investors + Fundraising OS (pipeline, deck, model, outreach, data room)

---

## Phase 1 — Local AI brain ✅

- [x] Add `ollama` provider to `llm.py`
- [x] Config: `LLM_PROVIDER` (auto), `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_FAST_MODEL`
- [x] `llm.active()` auto-detects a running local model; graceful fallback (local → cloud → heuristic)
- [x] Auto-resolves to whatever model is installed (no exact-tag config needed)
- [x] Strips "thinking" traces from reasoning models
- [x] Tested end-to-end — `qwen2.5:7b` generating real output, `/health` shows `llm: ollama, active: true`

---

## Phase 2 — Growth page becomes a 6-tab hub ✅

- [x] `engines/base.py` shared engine framework (context → LLM/heuristic → save → return)
- [x] `/growth` 6-tab shell (Strategy · Marketing · Lead Gen · Sales · Analytics · Customer Success)
- [x] Moved Growth Agent recommendations + outcome loop into the Marketing tab ("Tracked plays")
- [x] `enginesApi` client in `lib/api.ts`

---

## Phase 3 — The six engines

### Strategy Engine ✅
- [x] Backend `engines/strategy.py` (market summary, positioning, pricing, GTM)
- [x] Endpoint GET/POST `/engines/strategy`
- [x] Strategy tab UI
- [x] Saves positioning back to memory for other engines
- [x] Verified end-to-end with local AI (real positioning + GTM generated)

### Marketing Engine ✅
- [x] Backend `engines/marketing.py` (audience, message, channel mix, calendar)
- [x] Endpoint GET/POST `/engines/marketing`
- [x] Marketing tab UI (+ tracked plays)

### Lead Gen Engine ✅
- [x] Backend `engines/leadgen.py` (prospect finder via web, digital/WhatsApp/offline tactics, lead magnets)
- [x] Endpoint GET/POST `/engines/leadgen`
- [x] Lead Gen tab UI

### Sales Engine ✅
- [x] Backend `engines/sales.py` (funnel, outreach sequences, objection handling, close tips)
- [x] Endpoint GET/POST `/engines/sales`
- [x] Sales tab UI

### Analytics Engine ✅
- [x] Backend `engines/analytics.py` (live KPIs, forecast, competitive insight, AI narrative + roadmap)
- [x] Endpoint GET/POST `/engines/analytics`
- [x] Analytics tab UI — verified live (9 tiles + forecast)

### Customer Success Engine ✅
- [x] Backend `engines/success.py` (CRM, tickets, FAQ, chatbot via grounded RAG)
- [x] Endpoints: overview + chat + ticket
- [x] Customer Success tab UI (CRM + support desk + AI chatbot) — verified live

---

## Phase 4 — Polish & deferred items 🟡

- [x] Customer Success: "teach the chatbot" knowledge feed + note + on-demand AI FAQ generation
- [x] Pitch deck: per-slide "needs input" guidance + AI-polished bullets + next-step outreach direction
- [ ] Brain page UX polish
- [x] Real one-click OAuth — flow proven end-to-end (GitHub sign-in working).
  - [x] GitHub — live
  - Other providers (Google, Facebook/Instagram, Slack, Notion): fully supported in code —
    just add each provider's keys to `backend/.env` and restart. Skipped for now by choice.
- [x] WhatsApp executive report via Twilio — consolidated 5-engine brief (Strategy/Marketing/
  Lead Gen/Sales/Analytics), plain-text WhatsApp format, grounded. Preview + send from Dashboard.
  Verified: report generation working end-to-end with local AI. (Live send needs sandbox join — see below.)
- [ ] 🔵 Other sending: email via Gmail (build after Gmail OAuth), ads execution (needs ad-platform API)

---

## Phase 5 — Upgraded engine prompts + Sales deal pipeline ✅

Adopted the rigorous, grounded prompt style across all engines (role + cite-a-fact +
confidence + insufficient_data + JSON only). Each engine = 3 edits: system prompt,
heuristic fallback (same schema), frontend renderer.

### Sales deal pipeline (option a) — real CRM data ✅
- [x] `deals` + `deal_events` tables (stage, time-in-stage, transition history)
- [x] `memory.py` deal functions (create, list, move stage, pipeline metrics)
- [x] Deal API endpoints (list / create / move stage) — verified live
- [x] Sales tab pipeline board UI (add deal, move stage via dropdown)

### Engine prompt upgrades (new schemas + fallbacks + renderers) ✅
- [x] Strategy — positioning/pricing/gtm_sequence + confidence + insufficient_data_flags
- [x] Marketing — channel-by-channel (content_seo/paid/organic_social/pr_partnerships/brand) + status
- [x] Lead Gen — channel_risk_flag + ranked recommendations + withheld_channels
- [x] Sales — urgent_actions / on_track / pipeline_insight (reads deal pipeline) — verified live with local AI
- [x] Analytics — measured_summary / forecasts (labeled projections) / competitive_insight / exec summary
- [x] Customer Success — health_read / ticket_triage / retention_actions (new prompt + brief card)

---

## Phase 6 — Simpler connect + Colab model hosting ✅

- [x] WhatsApp report: split number into country-code + number fields
- [x] Connect UX: default is a clean one-click "Connect" (OAuth); token entry moved behind an
  "Advanced" link so users aren't asked to fetch keys. Friendlier messages when sign-in isn't set up.
- [x] Colab hosting: `colab/CBO_Colab_LLM.ipynb` runs the model on Colab's GPU + public tunnel;
  paste the URL into `OLLAMA_BASE_URL`.
- [x] Colab-drop resilience: app auto-falls back to the grounded advisor when the model URL is
  unreachable — API responses keep the same shape (verified via existing fallback). Detection
  timeout raised to 4s for remote endpoints.
- [x] Optional stand-in endpoint `app/tools/mock_ollama.py` keeps the model API "present" when
  nothing else is running.
- [x] HubSpot + Zoho CRM connectors added (CRM category, OAuth-ready).
- [x] In-app integration setup: operator pastes each provider's Client ID/Secret on the Sources
  page ("Set up one-click sign-in"), stored in DB — no `.env` editing, no restart. OAuth flow reads
  DB first, falls back to `.env`. Verified via `/settings/integrations`.

---

## Open decisions 🔵

- [ ] Target business type (assume: any business)
- [ ] Primary market/region (assume: India-friendly channels)
- [ ] Draft-only vs. actually send (assume: draft-first)
- [ ] Built-in CRM vs. connect existing (assume: built-in)
- [ ] Test company: sample vs. real (assume: sample for now)

---

## How we use this file
1. Before starting an item, set it to 🟡 (in progress).
2. When finished and verified, check the box and set ✅.
3. Add new items here as scope grows, so nothing is lost.
