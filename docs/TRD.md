# CBO — Technical Requirements Document (TRD)

Companion to `PRD.md`. Describes how the system is built and how the new work will be implemented. Written to stay consistent with the existing architecture (FastAPI backend owns all logic; Next.js frontend is a thin client).

---

## 1. Architecture overview

```
[ Next.js frontend (thin client) ]
            │  HTTP / JSON
            ▼
[ FastAPI backend — all business logic ]
   ├── Company Memory (SQLite): entities, facts, relationships, timeline, artifacts
   ├── AI layer: local LLM (Ollama) | cloud (OpenAI/Anthropic) | grounded heuristic fallback
   ├── Web Research layer (research.py)
   ├── Connectors (Gmail, GitHub, Stripe, Instagram, Facebook, …)
   └── Engines (Strategy, Marketing, Lead Gen, Sales, Analytics, Customer Success)
```

**Core rule:** every AI call is grounded — it receives only relevant retrieved context plus instructions to answer from that context and flag unknowns. Math (scores, forecasts) is computed in code; the LLM explains and composes language.

---

## 2. Current codebase (already built)

### Backend (`backend/app/`)
| File | Responsibility |
|---|---|
| `db.py` | SQLite schema + connection (Postgres-ready) |
| `memory.py` | Company Memory: facts, entities, relationships, timeline, artifacts, investors |
| `config.py` | Env config; LLM + search provider + OAuth client settings |
| `llm.py` | LLM abstraction (currently OpenAI/Anthropic; local fallback reasoner) |
| `embedding.py` | In-process embeddings + cosine search |
| `extract.py`, `files.py` | Fact extraction + file parsing |
| `interview.py` | Stage-aware onboarding; churn + lead questions |
| `ai.py` | Metrics, Brain RAG, Council (9 agents + frameworks), Morning Brief, outcome learnings |
| `metrics.py` | Lead Score, churn, customer health, CAC:LTV, growth score, revenue opportunity |
| `growth.py` | Growth Agent recommendations (playbook, lifecycle, outcomes) |
| `outcomes.py` | Outcome-tracking loop + lifecycle status |
| `dashboard.py` | 9-tile dashboard aggregator |
| `competitors.py` | Competitor analysis + web auto-discovery |
| `research.py` | Web search (Tavily/Serper/Brave + keyless DuckDuckGo) |
| `connectors.py` | Connector framework + Instagram/Facebook + OAuth scaffolding |
| `fundraising.py`, `investordb.py` | Fundraising OS + investor database |
| `main.py` | FastAPI routes |

### Frontend (`app/`, `lib/`, `components/`)
Pages: Brief (`/`), Dashboard, Brain, Sources, Council, Growth, Competitors, Investors, Fundraising, Onboarding. `lib/api.ts` is the typed client; `lib/store.ts` holds only the active company id.

### Data model note
- **`facts` table** stores all knowledge (type/key/value/num + source/confidence/owner/version). New data types are added as new `type`/`key` values — **no schema migrations**.
- **`artifacts` table** stores versioned generated documents (pitch deck, financial model, and — new — engine outputs).

---

## 3. New work — technical plan

### 3.0 Local LLM (Ollama)
- Extend `llm.py` with an **`ollama`** provider that calls `http://localhost:11434/api/chat` (OpenAI-compatible endpoint also available).
- `config.py`: add `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` (default `qwen2.5:7b`), optional `OLLAMA_FAST_MODEL` (`qwen2.5:3b`).
- `llm.active()` returns true when Ollama is reachable; `llm.complete()` routes to it.
- Graceful fallback order: local Ollama → cloud (if key) → built-in grounded heuristic. Nothing breaks if Ollama is off.

### 3.1 Shared engine framework (`backend/app/engines/base.py`)
A single helper all engines use:
```
run_engine(company_id, kind, context_builder, heuristic_builder, system_prompt):
    ctx   = context_builder(company_id)          # facts + metrics + (optional) web research
    if llm.active():
        result = llm.complete(system_prompt, ctx)  # JSON output
    else:
        result = heuristic_builder(company_id, ctx) # framework-based fallback
    memory.save_artifact(company_id, kind, title, result)   # versioned
    return result
```
Keeps every engine consistent, grounded, and always-returning.

### 3.2 Engine modules (`backend/app/engines/`)
| Module | Reuses | Produces (saved as artifact) |
|---|---|---|
| `strategy.py` | `competitors`, `research`, Council strategy framework | positioning statement, pricing tiers, GTM plan, market summary |
| `marketing.py` | `growth` playbooks | audience, message, channel mix, campaign calendar |
| `leadgen.py` | `metrics` (Lead Score), `research` (prospect lists) | prospect list, digital/WhatsApp/offline tactics, lead magnets, scoring |
| `sales.py` | `ai.draft_followup`, outreach | funnel stages, outreach sequences, pipeline view, close forecast |
| `analytics.py` | `dashboard`, `fundraising` (financial model) | dashboards, forecast, competitive insight, roadmap |
| `success.py` | `ai.brain_ask` (RAG) | CRM records, support tickets, FAQ, chatbot answers |

Structured outputs that other engines consume (e.g., positioning, pricing, ICP) are also written to the `facts` table so they become inputs downstream.

### 3.3 API endpoints (new)
```
GET/POST  /companies/{id}/engines/strategy
GET/POST  /companies/{id}/engines/marketing
GET/POST  /companies/{id}/engines/leadgen
GET/POST  /companies/{id}/engines/sales
GET       /companies/{id}/engines/analytics
POST      /companies/{id}/engines/success/chat        {message}
GET/POST  /companies/{id}/engines/success/tickets
```
GET = load last saved artifact (instant). POST = regenerate.

### 3.4 Frontend
```
app/growth/page.tsx        # 6-tab shell + shared company state
  tabs/StrategyTab.tsx  MarketingTab.tsx  LeadGenTab.tsx
  tabs/SalesTab.tsx     AnalyticsTab.tsx  SuccessTab.tsx
lib/api.ts -> enginesApi.{strategy, marketing, leadgen, sales, analytics, success}
```
Existing Growth Agent recommendations + Lead Score move into the Marketing / Lead Gen tabs. Reuse existing card/pill/playbook styling. Each tab: Generate/Regenerate button + loading state + rendered cards.

### 3.5 Lead generation — technical honesty
- **Find (outbound):** `research.web_search` builds prospect lists (name, type, contact hints) from public sources.
- **Attract (inbound):** LLM drafts ad/social/WhatsApp/landing copy + lead magnets.
- **Capture & convert:** leads stored as `facts`/CRM records; Lead Score ranks them; `sales.py` drafts follow-ups.
- **Execution (sending ads/WhatsApp)** requires connected real accounts — drafted now, sent later via connectors. No fake sends.

### 3.6 Customer Success chatbot
- RAG over Company Memory using the existing `brain_ask` retrieval + local LLM composition.
- Support tickets and FAQs stored as `facts`/`timeline`; answers cite sources; says "I don't know" when unsupported.

---

## 4. Non-functional requirements
- **Privacy:** default AI path is local; no external calls when Ollama is used (except explicit web research, which the user triggers).
- **Resilience:** every engine returns a useful result even with no LLM and thin data.
- **Performance target:** engine generation returns within a few seconds on Qwen2.5 7B on the target machine (Ryzen 7 7840HS / RTX 4050 6GB / 16GB RAM).
- **No migrations:** all new data uses existing `facts`/`artifacts` tables.

---

## 5. Target environment
- OS: Windows. Backend: Python/FastAPI (uvicorn). Frontend: Next.js 16.
- Local AI: Ollama, model `qwen2.5:7b` (+ `qwen2.5:3b` for quick replies).
