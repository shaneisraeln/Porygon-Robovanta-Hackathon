# CBO — Product Requirements Document (PRD)

**Product:** CBO — an AI-powered Business Growth Operating System
**Vision:** A founder's co-pilot that turns real company data into strategy and action across the full growth lifecycle — attract, convert, retain — with a privacy-first local AI brain.

---

## 1. Guiding principles

- **Your data stays yours.** The AI brain runs locally (on your own machine) by default. Nothing is sent to an outside AI company.
- **No made-up data.** Every number and score comes from real company information or connected sources. If something is unknown, the app says "insufficient data" instead of guessing.
- **Always useful.** Even with little data, the engines give sensible, framework-based advice — the page is never empty.
- **One connected system.** The engines feed each other (Strategy → Marketing → Lead Gen → Sales → Customer Success), all measured by Analytics.

---

## 2. What we've already built (done)

These are live in the app today.

### Foundation
- **Onboarding / Interview** — Stage-aware questions (Idea → Growth). Now also captures churn and lead-generation inputs (monthly leads, conversion rate, source mix).
- **Company Brain** — Ask questions in plain English; answers come only from stored company memory, with sources and a confidence score. Includes a knowledge graph and memory timeline.
- **Knowledge Sources (Connectors)** — Gmail, Google Calendar, Google Drive, GitHub, Notion, Slack, Stripe, **Instagram, Facebook**, and manual upload. One-click **sign-in (OAuth)** flow is wired (activates once provider keys are added; falls back to token paste).
- **Executive Council** — 9 AI advisor personas (Strategy, Finance, Fundraising, Market, Execution, Operations, Customer, Risk, **Growth**), each reasoning through a named business framework.

### Growth & intelligence
- **Business Dashboard (v2)** — 9 KPI tiles: Business Health, Growth Score, Revenue Opportunity, Lead Score, Customer Health, Market Readiness, CAC:LTV, AI Recommendations, Risk Alerts, plus an Executive Summary.
- **Metrics engine** — Lead Score, Churn, Customer Health, CAC:LTV, Growth Score, Revenue Opportunity — all computed from real facts.
- **Competitor Analysis** — Add competitors manually, or **auto-discover similar products from the web**; produces a gap table and "Where You Win / Where You're Exposed."
- **Growth Agent** — Ranked, data-grounded recommendations, each with a step-by-step **playbook**, expected impact, effort, and timeframe. Full outcome-tracking loop (recommended → in progress → completed → measured) that feeds results back into future advice.
- **Web Research layer** — Real internet search (works with no key via DuckDuckGo; sharper with a provider key).

### Fundraising
- **Investor Intelligence + Fundraising OS** — Investor pipeline, fit scoring, pitch-deck and financial-model generation, outreach board, meeting prep, data room.

---

## 3. What we're building next

### 3.0 Local AI brain (foundation for everything below)
Add support for a **local LLM (via Ollama)** so all AI features run on the user's own computer.
- Recommended model: **Qwen2.5 7B** (fast, fits the target laptop), with **Qwen2.5 3B** as a quick-reply option.
- If the local AI isn't running, the app falls back to built-in grounded advice — nothing breaks.

### 3.1 The Growth page becomes a 6-engine hub
The `/growth` page becomes a tabbed workspace with six engines. Each engine reads company memory + (optionally) live web research, thinks it through with the local AI, and produces a clear, saved plan.

**1. Strategy Engine**
- Market research summary, brand positioning statement, pricing suggestions, and an overall sales/marketing game plan.
- *Human equivalent it replaces:* weeks of market study, competitor mapping, and positioning workshops.

**2. Marketing Engine**
- A 360° marketing plan: target audience, core message, channel mix, and a campaign/content calendar.
- *Replaces:* a marketing manager designing the promotion plan.

**3. Lead Gen Engine**
- Brings leads in and warms them up: finds prospect lists via web research, suggests digital ad strategy, WhatsApp campaigns, physical/offline ideas, and lead magnets; captures and scores incoming leads.
- *Replaces:* a growth marketer running channel experiments.

**4. Sales Engine**
- Builds a sales funnel, drafts outreach sequences (email/WhatsApp), tracks deals in a pipeline, and forecasts closes.
- *Replaces:* a sales rep working a CRM and playbook.

**5. Analytics Engine**
- Dashboards, revenue/growth forecasting, competitive insights, product roadmap, and portfolio view — with plain-English explanations.
- *Replaces:* a data analyst stitching spreadsheets and BI tools.

**6. Customer Success Engine**
- A simple CRM, a support portal (tickets + FAQs), and an AI chatbot that answers from company knowledge.
- *Replaces:* a CS manager + support desk.

### 3.2 How the engines connect
Strategy sets positioning & pricing → Marketing turns it into campaigns → Lead Gen fills the funnel → Sales closes deals → Customer Success retains & expands → Analytics measures everything and loops learnings back to Strategy.

---

## 4. Also planned (smaller items)
- **Pitch deck polish** — fill "needs input" fields with guidance and web research; add clear outreach direction.
- **Brain page polish** — cleaner question/answer and graph experience.
- **Real one-click sign-in** — activate OAuth for each provider (needs provider app keys from the user).

---

## 5. Open decisions (to confirm with product owner)
| # | Decision | Working assumption |
|---|---|---|
| 1 | Target business type | Any business (not only tech startups) |
| 2 | Primary market/region | India-friendly channels (WhatsApp, offline) supported |
| 3 | Draft vs. actually send campaigns | Draft-first now; real sending via connected accounts later |
| 4 | Customer Success CRM | Simple built-in CRM inside the app |
| 5 | Test data | Use a sample company until a real one is provided |
| 6 | Local model | Qwen2.5 7B primary, 3B for quick replies |

---

## 6. Success criteria
- Every Growth tab returns useful output within seconds, even on a new company.
- All AI runs locally with no external data sharing (when Ollama is on).
- No fabricated numbers anywhere; unknowns are labeled.
- Engines share data so advice stays consistent across tabs.
