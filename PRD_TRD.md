# CBO (AI Business Operating System) — Complete PRD & TRD

---

## Executive Summary
CBO is an **AI Business Operating System** designed to run a startup alongside its founder. Rather than behaving like a passive dashboard, CBO ingests every data point a company produces (emails, calendar events, code commits, documents, finance data), structures it into a unified, versioned memory graph, and proactively drives execution (onboarding, morning briefs, executive councils, investor outreach, meeting prep, and data room management).

A key product pillar of CBO is the **"No Fabricated Data"** policy. Every score, timeline event, investor recommendation, and strategy is calculated from actual Company Memory, connected integration tokens, or user inputs — not mocks.

---

## PART 1: Product Requirements Document (PRD)

### 1. Vision & Core Philosophy
* **Founder's Co-pilot:** Works in the background to analyze operations, fundraising viability, and strategic execution.
* **Thin-Client Frontend:** Renders real state from the backend. The UI is a direct window into the company's memory.
* **Adaptive Systems:** Interfaces (like onboarding) adjust dynamically to startup stage, context, and existing database records.

---

### 2. Feature & Functional Requirements

#### A. Stage-Aware Dynamic Onboarding & Interview Engine (`/onboarding`)
* **Purpose:** Interview the founder like a venture capitalist or accelerator partner. Collect business metrics, goals, and team details.
* **Stage-Based Routing:** The initial question captures the startup's current phase (`Idea`, `Building MVP`, `Product Live`, `Early Customers`, `Revenue`, `Fundraising`, `Growth`). Every subsequent question is served dynamically according to that stage's path:
  * **Idea Stage:** Validation efforts, alternatives, problem definition, vision.
  * **MVP Stage:** Code repository, core features, launch timing, pilots.
  * **Live/Early Customers Stage:** User counts, monthly activity, retention rates, business model.
  * **Revenue/Growth Stage:** MRR/ARR, month-over-month growth rate, monthly burn, cash-in-bank, pricing strategy, customer acquisition cost (CAC).
  * **Fundraising Stage:** Target raising amount, target round type, valuation expectations, target investor lists, pitch deck uploads.
* **Smart Skipping:** Questions are skipped automatically if the answer is already satisfied in memory or by an active connector (e.g., Stripe answers revenue; GitHub answers codebase link).
* **Live Confidence Panel:** A sidebar updates in real-time to show overall knowledge confidence and per-dimension scores (`Product`, `Customers`, `Market`, `Competition`, `Traction`, `Team`, `Revenue`, `Business Model`, `Funding Readiness`).
* **Continuous Loop:** Onboarding never "ends". The system identifies dimensions with confidence scores $< 40\%$ and queues them as follow-up questions later.

#### B. The Morning Brief (`/`)
* **Purpose:** A personalized briefing generated daily from memory and live event logs, summarizing what needs attention.
* **Brief Categorization:** Categorizes items into:
  * **Priority / Action Items:** High-priority actions, posture choices, or setup prompts.
  * **Approvals / Outreach Tasks:** Prompts to review or send drafted investor emails.
  * **Risks:** High-severity events like high burn rates without revenue, investor conversations cooling down, or platform issues.
  * **Opportunities:** Favorable signals such as compound growth rate benchmarks or positive investor interactions.
* **Expandable Summaries:** Selecting an item displays why it appeared, what changed, why it matters, next steps, and its primary source reference.
* **Global Statistics:** Displays the daily date, company health score, fundraising readiness score, and count indicators of active alerts.

#### C. Company Brain & Knowledge Graph (`/brain`)
* **Purpose:** Search and audit interface for the company's core memory.
* **Grounded Q&A (RAG):** Natural language questions (e.g., *"What is our runway?"*) search vector database chunks and sqlite facts. It outputs a grounded answer, a confidence score, and a list of sources.
* **Knowledge Graph Visualizer:** An interactive SVG layout representing company entities (`company`, `product`, `customer`, `investor`, `metric`, `goal`, etc.) and their relationships (e.g., *Company* $\rightarrow$ `employs` $\rightarrow$ *Team*). Selecting a node filters the memory list to display only facts linked to that node.
* **Factual Memory Inspector:** Lists every atomic fact, complete with its label, value, version number, source type (e.g., conversation, document), owner, confidence score, and exact source text.
* **Manual Data Ingestion:** A text box allowing the user to paste documents, update notes, or manual inputs, which CBO automatically extracts into memory facts.
* **Memory Timeline Feed:** A live event stream showing sync actions, code commits, payments, and meeting logs.

#### D. Knowledge Sources & Connectors (`/sources`)
* **Purpose:** Connect external APIs to feed the ingestion pipeline.
* **Cataloged Connectors:** 
  * *Communication:* Gmail, Calendar, Slack.
  * *Documents:* Google Drive, Notion, Manual Uploads.
  * *Product & Engineering:* GitHub.
  * *CRM:* HubSpot.
  * *Finance:* Stripe, QuickBooks.
* **Pipeline Status Indicator:** Displays the pipeline stages: `Connect` $\rightarrow$ `Sync` $\rightarrow$ `Extract` $\rightarrow$ `Entities` $\rightarrow$ `Relationships` $\rightarrow$ `Graph` $\rightarrow$ `Vectors` $\rightarrow$ `Timeline` $\rightarrow$ `Agents`.
* **State Management:** Displays active counts (Entities, Facts, Relationships, Timeline items, Chunks) and connector-specific status tags (Connected, Syncing, Last synced timestamp).
* **Credential Gates:** Connectors requiring keys prompt the user for API tokens rather than faking connections.

#### E. The Executive Council (`/council`)
* **Purpose:** Run strategic decisions through a multi-agent debate chamber.
* **Strategic Intent Classification:** The system parses questions (e.g., *"Should we raise capital now?"*) to identify the intent (e.g., `raise`, `hire`, `pivot`, `spend`, `general`).
* **Functional Agent Verdicts:** Eight virtual agents render independent opinions:
  * **Strategy:** Evaluates strategic alignment and execution health.
  * **Finance:** Checks burn, monthly spend, cash levels, and runway length.
  * **Fundraising:** Evaluates readiness and existing investor pipeline relations.
  * **Market:** Evaluates addressable market size (TAM) and competition.
  * **Execution:** Assesses shipping velocity, headcount constraints, and bottleneck items.
  * **Operations:** Evaluates organizational efficiency.
  * **Customer:** Measures stickiness, customer volume, and retention cohorts.
  * **Risk:** Audits critical warning flags (e.g., high burn with zero revenue, cooling relationships).
* **Debate & Consensus Generation:** Opposing agent viewpoints (highest vs. lowest confidence stances) are structured as a chat script. A final synthesis provides a consensus headline, rationale, confidence index, actionable next steps, and governance checks (e.g., Runway Guardrails).

#### F. Investor Intelligence Network (`/investors`)
* **Purpose:** A matchmaking database pairing the company with institutional investors.
* **Scoring fit engine:** Scores VC firms against live company metrics (sectors, stage, geography, target round, and revenue parameters).
* **Detailed Research Dossiers:** 
  * VC overview: Check size, preferred stages, target geographies, and recent portfolio.
  * Stated investment thesis.
  * CBO Strategy recommendation (e.g., Approach immediately vs. Wait 75 days to hit traction thresholds).
  * Pros and Cons lists explaining fit scores.
  * Anticipated partner objections and likely questions.
  * Target email templates and board meeting agendas.
  * Warm intro path discovery (e.g., Founder $\rightarrow$ Team Member $\rightarrow$ VC Partner).

#### G. Fundraising Operating System & War Room (`/fundraising`)
* **Purpose:** A centralized command center to execute seed, series, or debt rounds.
* **Execution Tracker:** Interactive 18-stage pipeline board (Linear-style) mapping actions from `Company Understood`, `Pitch Deck Generated`, `Intros Found`, `Outreach Sent`, `Meetings Booked` down to `Diligence`, `Term Sheet`, and `Round Closed`.
* **Readiness Dial:** Radial gauge assessing readiness based on missing documentation and business metrics.
* **Automated Deck & Model Builders:** 
  * *Pitch Deck Generator:* Creates a 9-slide framework (`Title`, `Problem`, `Solution`, `Product`, `Market`, `Traction`, `Business Model`, `Team`, `The Ask`) pulling bullets directly from memory. Marks slides as "needs input" if memory is blank.
  * *Financial Model Generator:* Generates 12-month projections of MRR, monthly spend, cash balances, and runway lengths based on growth rates.
* **Outreach Approval Board:** Tracks the email drafting process (`not_started`, `drafted`, `approved`, `sent`). Emails are reviewable in-app and can be approved for delivery.
* **Meeting Intelligence & Debriefs:** Pastes meeting notes or transcripts. Automatically parses them into:
  * Questions asked.
  * Objections and concerns raised.
  * Commitments and promises made.
  * Key follow-up actions.
  * Drafted follow-up email.
* **Secure Data Room Checklist:** Automatically verifies if critical assets are ready (`Pitch Deck`, `Financial Model`, `Cap Table`, `Roadmap`, `KPIs`).

---

## PART 2: Technical Requirements Document (TRD)

### 1. Architecture Overview
CBO uses a decoupled client-server architecture:
1. **Frontend (Next.js Thin Client):** React 19, TypeScript, Tailwind CSS, and Zustand (for session caching). The client holds zero business logic or persistent data. All metrics, decisions, and graph nodes are calculated in real-time on the server.
2. **Backend (FastAPI Service):** Python 3.10+ engine handling memory persistence, embedding generations, connector synchronization, agent reasoning, and document parsing. It defaults to SQLite (SQL database) and local embeddings for seamless zero-config operation.

```
       [ Next.js Frontend (Next.js 16/React 19) ]
                         │
                         │ HTTP (JSON / REST API)
                         ▼
             [ FastAPI Backend Server ]
                         │
      ┌──────────────────┼──────────────────┬─────────────────┐
      ▼                  ▼                  ▼                 ▼
[SQLite DB]      [RAG Vector Index]   [Graph Network]   [AI Agents]
(Facts & Session) (Local Embeddings)  (Entities/Edges)  (Council/Debate)
```

---

### 2. Frontend Component Implementations & UI Layouts

#### A. Top Navigation Bar (`components/TopNav.tsx`)
* **Layout Structure:** Flexbox container pinned to the top of the viewport (`sticky top-0 z-40`). Built with backdrop blur styles (`bg-canvas/85 backdrop-blur-xl`) and a bottom boundary line (`border-b border-line`).
* **Visual Logo:** Renders the "CBO" brand icon:
  * A dark-themed square badge (`bg-ink h-7 w-7 rounded-lg`) containing a centered circular light element with a breathing pulse animation (`h-2 w-2 rounded-full bg-accent animate-breathe`).
* **Session Brand Text:** Renders `CBO / {CompanyName}` in the header using muted gray typography.
* **Link Navigation:** Map iteration over links (`Brief`, `Brain`, `Sources`, `Council`, `Investors`, `Fundraising`). Compares `l.href` against Next.js's `usePathname()` hook to apply active typography styling (`font-medium text-ink` for active, `text-muted hover:text-ink` for inactive).

#### B. Onboarding Authentication Guard (`components/RequireCompany.tsx`)
* **Behavior:** A higher-order component wrapping workspace routes. It subscribes to the Zustand session store (`companyId`, `hydrated`).
* **Gate Logic:** Renders a central breathing indicator (`h-2 w-2 bg-accent rounded-full animate-breathe`) while loading. Once hydrated, if `companyId` is null, it fires `router.replace("/onboarding")` to redirect the user.

#### C. Morning Brief Alert Item (`components/BriefRow.tsx`)
* **Component Design:** A collapsible layout component displaying individual brief points.
* **Visual States:**
  * Displays severity indicators using color-coded dot elements (`h-1.5 w-1.5 rounded-full`) mapping to warning levels: `high` $\rightarrow$ `bg-danger`, `medium` $\rightarrow$ `bg-warn`, `low` $\rightarrow$ `bg-good`.
  * Title block renders the alert source badge (e.g., `PRIORITY`, `RISK`, `NEEDS YOU`), header title (`text-[17px] font-medium`), contextual change description, and a target action preview.
  * Features a right-aligned indicator arrow (`›`) that rotates $90^\circ$ when expanded.
* **Expansion details:** Clicking the row expands a details panel with an entry transition (`animate-fade`). It details the rationale, observed metric variations, core impact statements, and citations from connected documents or files.

#### D. Knowledge Graph Network SVG Component (`components/KnowledgeGraph.tsx`)
* **SVG Structure:** Renders a static concentric network visualization using raw SVG shapes (`viewBox="0 0 400 360"`).
* **Positioning Math:**
  * Finds the core company entity and locks it to coordinate (`cx=200, cy=180`).
  * Filters and sorts external entities (e.g., people, metrics, investors, products) based on relationship degrees.
  * Positions the top 16 connected nodes along a radius path ($r=128$) using trigonometric calculations:
    $$\theta = \left(\frac{i}{\text{nodes}}\right) \times 2\pi - \frac{\pi}{2}$$
    $$x = cx + \cos(\theta) \times r,\quad y = cy + \sin(\theta) \times r$$
* **SVG Styling & Interactive Elements:**
  * Renders a dashed gray layout track (`circle r={r} strokeDasharray="2 5"`).
  * Renders connection edges using line paths (`line stroke="#eceaf6"`) connecting radial nodes.
  * Node points are rendered as circles (`circle r={active ? 8 : 6}`) colored by category type (`investor` $\rightarrow$ red, `product` $\rightarrow$ indigo, `metric` $\rightarrow$ gray, etc.).
  * Renders node text labels with smart alignment: `textAnchor="end"` for nodes on the left ($x < cx$) and `textAnchor="start"` for nodes on the right.
  * Fires the `onSelect(nodeId)` state callback on click, rendering selected items with bold text and highlighted lines.

#### E. Chronological Event Feed (`components/Timeline.tsx`)
* **Component Design:** A vertical list structure.
* **Properties & Logic:**
  * Maps event types (emails, commits, meetings, updates) to distinct colors.
  * **Relative Time Calculations:** Formats event times using a helper function:
    ```typescript
    function ago(atSeconds: number): string {
      const ms = Math.max(0, Date.now() - (atSeconds * 1000));
      const m = Math.floor(ms / 60000);
      if (m < 1) return "just now";
      if (m < 60) return `${m}m ago`;
      const h = Math.floor(m / 60);
      if (h < 24) return `${h}h ago`;
      return `${Math.floor(h / 24)}d ago`;
    }
    ```
  * Iterates over chronological lists to render timeline items, complete with titles, source tags, participant labels, and processing agent tags.

---

### 3. Backend Implementation & Core Python Systems

#### A. Database Schema & Data Models (`backend/app/db.py` & `backend/app/memory.py`)
Memory uses a relational schema containing:
* **Company Table:** Stores the company name, description, client target segments, and current stage.
* **Facts Table:** Contains atomic, versioned knowledge facts.
  ```sql
  CREATE TABLE facts (
      id TEXT PRIMARY KEY,
      company_id TEXT,
      type TEXT,         -- product, customer, team, metric, goal, investor
      key TEXT,          -- what, stage, mrr, burn, retention, etc.
      label TEXT,        -- User-facing fact label
      value TEXT,        -- Fact string value
      num REAL,          -- Numeric value for metrics calculations
      source_kind TEXT,  -- conversation, document, connector
      source_ref TEXT,   -- Onboarding link, document name, email subject
      evidence TEXT,     -- Raw source sentence snippet
      confidence REAL,   -- Fact reliability score (0.0 to 1.0)
      version INTEGER,   -- Incremental version identifier
      owner TEXT,        -- founder, agent, system
      entity_id TEXT,    -- Graph entity mapping ID
      created_at REAL
  );
  ```
* **Entities & Relationships Tables:** Define graph network nodes and edges (e.g., `from_id`, `to_id`, relation name).
* **Connector States Table:** Tracks synchronization metadata (last cursor, sync timestamps, records processed).
* **Outreach Table:** Stores drafted, approved, and sent emails.

#### B. Dynamic Interview Algorithm (`backend/app/interview.py`)
* **State Machine Queue:** Holds a static list of candidate questions, each defined by attributes like stage, prompt text, target groups, fact key mappings, priority weight, and input types (`text`, `choice`, `upload`).
* **Next Question Selection Math:**
  1. Identifies the company's current stage using stored facts. If none, returns the initial `stage` selection question.
  2. Queries the set of satisfied fact keys $\mathbb{K}$ from memory and connected tools.
  3. Filters candidate questions based on active stage group tags, excluding questions that have been answered, skipped, or satisfied.
  4. Sorts the remaining candidates in descending order by weight, returning the highest-priority question.
* **Confidence Math:** Measures data coverage across dimensions:
  $$\text{Dimension Score} = \text{round}\left( \max(\text{Confidence of present keys}) \times 100 \right)$$
  $$\text{Knowledge Confidence} = \text{round}\left( \frac{\sum \text{Dimension Scores}}{\text{Number of Dimensions}} \right)$$

#### C. Investor Fit Score Matcher (`backend/app/investordb.py`)
Calculates compatibility between VC firms and company parameters:
1. **Industry Extraction:** Maps company statements and problem facts to canonical sectors ($\mathbb{S}$) using a synonym dictionary.
2. **Scoring Logic:**
   * **Base Score:** Starts at 18.0.
   * **Stage Check:** If targeted raise stage matches a VC preferences, add +22.0. Else, record a stage warning.
   * **Sector Match:** Calculates overlap:
     $$\text{Overlap} = \mathbb{S}_{\text{company}} \cap \mathbb{S}_{\text{VC}}$$
     Add $+24.0 \times \left(\frac{|\text{Overlap}|}{|\mathbb{S}_{\text{company}}|}\right)$. If overlap exists and the VC specializes in fewer than 4 sectors, add an extra $+8.0$.
   * **Recent Bets:** If the VC has invested in overlap sectors recently, add +10.0.
   * **Geography Check:** If company geo matches the VC's target list, add +10.0. Else, subtract -10.0.
   * **Traction Check:** If revenue is present, add +6.0. If the VC requires recurring revenue but the company has none, subtract -6.0.
   * **Result Constraints:** Clamp the final score between 5.0 and 98.0.
   * **Outreach Probability:** Calculates the intro probability:
     $$\text{Probability} = \text{round}(\text{Fit Score} \times 0.7)$$

#### D. Meeting Transcript Regex Extractor (`backend/app/fundraising.py`)
Analyzes raw text transcripts or meeting notes using pattern matching:
* **Objections & Risks:** Identifies sections containing keywords:
  `concern|worried|not sure|hesitant|risk|too early|competitive|threat|burn|runway|churn|depend`
* **Promises & Commitments:** Detects future action expressions:
  `we will|we'll|i'll send|we can|promise|commit|by next`
* **Next Steps:** Parses follow-up intentions:
  `follow up|send|share|intro|next step|circle back|schedule`
* **Sentiment Analysis:** Flags positive/negative sentiment triggers (e.g., `excited`, `loved` vs. `pass`, `too early`).

#### E. AI Brain RAG Pipeline (`backend/app/ai.py`)
1. **Fact Retrieval:** Tokenizes natural language queries, filters stop words, and matches terms against company facts.
2. **Text Chunk Search:** Scores document passages using term matching as a local fallback vector index.
3. **Response Assembly:**
   * Directly answers common queries (e.g., runway, burn, team size, revenue) using metric calculators.
   * For general queries, passes context facts and chunks to the LLM interface (when active), prompting it to write a response strictly grounded in the retrieved details. If the LLM is offline, formats a structured response from the retrieved facts.

---

### 4. API Endpoint Map (`backend/app/main.py`)

| Endpoint Path | HTTP Method | Input Payload | Response Payload | Description |
|---|---|---|---|---|
| `/health` | GET | None | `{"ok": bool, "llm": str}` | Server status check |
| `/onboarding/start` | POST | `StartReq(name)` | `Company` | Initializes new company records |
| `/onboarding/answer` | POST | `AnswerReq(company_id, key, text)` | `{"captured": [{"label":str, "value":str}]}` | Parses and saves onboarding facts |
| `/companies/{id}` | GET | None | `Company` | Returns metadata and stats |
| `/companies/{id}/brief` | GET | None | `Brief` | Generates the Morning Brief alert list |
| `/companies/{id}/brain/ask`| POST | `AskReq(query)` | `AskResult` | Grounded RAG query handler |
| `/companies/{id}/graph` | GET | None | `{"entities": [Entity], "edges": [Edge]}` | Returns network graph nodes and edges |
| `/companies/{id}/facts` | GET | None | `{"facts": [Fact]}` | Returns company fact lists |
| `/companies/{id}/timeline` | GET | None | `{"timeline": [TimelineEvent]}` | Returns chronological timeline feed |
| `/companies/{id}/connectors`| GET | None | `{"connectors": [Connector]}`| Returns active connectors list |
| `/companies/{id}/connectors/{c_id}/connect`| POST | `ConnectReq(token)`| `{"status": str}` | Connects and syncs external tools |
| `/companies/{id}/ingest/text`| POST | `TextIngestReq(name, text)`| `{"summary": dict}` | Extracts facts from pasted text |
| `/companies/{id}/ingest/upload`| POST | `Multipart File` | `{"summary": dict, "chars": int}`| Parses uploaded document files |
| `/companies/{id}/council/ask`| POST | `CouncilReq(question)`| `CouncilResult` | Strategic council consensus engine |
| `/companies/{id}/investors` | GET | None | `{"investors": [Investor]}` | Returns investor relationship records |
| `/companies/{id}/investors/{iid}/debrief`| POST | `DebriefReq(notes)`| `Debrief` | Parses meeting notes and updates memory |
| `/companies/{id}/interview/next`| GET | None | `InterviewStep` | Returns the next onboarding question |
| `/companies/{id}/fundraising/pipeline`| GET | None | `Pipeline` | Returns fundraising pipeline stage states |
| `/companies/{id}/fundraising/readiness`| GET | None | `Readiness` | Calculates fundraising readiness |
| `/companies/{id}/fundraising/deck`| POST | None | `Deck` | Generates a memory-grounded pitch deck |
| `/companies/{id}/fundraising/financial-model`| POST | None| `FinancialModel` | Generates runway projections |
| `/companies/{id}/fundraising/outreach/{iid}/draft`| POST | None | `OutreachRow` | Drafts a tailored investor email |
| `/companies/{id}/fundraising/outreach/{iid}/approve`| POST | None | `{"status": "approved"}`| Approves a drafted outreach email |
| `/companies/{id}/fundraising/meeting/{iid}/transcript`| POST | `TranscriptReq(text)`| `TranscriptResult` | Extracts metrics and actions from transcripts |
| `/network/stats` | GET | None | `{"firms": int}` | Returns seed investor network count |
| `/network/import` | POST | `ImportFirmsReq(firms)` | `{"imported": int, "total": int}`| Imports new investor firms into db |
| `/companies/{id}/network/discover`| GET | None | `Discover` | Discovers and ranks seed VCs |
| `/companies/{id}/network/{fid}/approach`| POST | None | `{"investor_id": str}`| Adds a discovered VC to the pipeline |

---

### 5. UI Button & Interactive Element Implementations

All interface elements are styled with Tailwind CSS utility classes to create a clean, responsive layout. Below is a detailed breakdown of core interactive buttons and inputs:

#### A. Input Forms & Search Bars
* **Implementations:** 
  * The search/question bars in `/brain`, `/council`, and `/onboarding` use a container styled with a thin border and rounded corners (`rounded-2xl border border-line bg-surface px-2 py-1.5 focus-within:border-accent shadow-sm`).
  * Inputs inside this container use clean layout classes (`flex-1 bg-transparent px-3 py-2 text-[15px] outline-none placeholder:text-faint`).
* **Button Elements:** 
  * A primary dark action button (`rounded-xl bg-ink px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity disabled:opacity-50`) triggers forms. Shows a loading spinner (`…`) and disables inputs while processing (`disabled={asking}`).

#### B. Multiple Choice Selection Buttons (`/onboarding`)
* **Implementations:**
  * Interactive choice selections render button grids: `rounded-xl border border-line bg-surface px-4 py-2.5 text-sm text-ink transition-colors hover:border-accent hover:text-accent disabled:opacity-50`.
  * The transition to active state changes boundaries (`hover:border-accent`) and text colors (`hover:text-accent`) with a subtle fade.

#### C. In-App Document File Uploader (`/onboarding`)
* **Implementations:**
  * Uses a hidden input element wrapped in a dashed label container acting as the dropzone target: `cursor-pointer rounded-2xl border border-dashed border-line bg-surface px-4 py-3 text-center text-sm text-muted hover:border-accent hover:text-ink transition-all`.
  * Disables interactions and changes label text to `Reading…` while uploading files.

#### D. Tab Navigation Switches (`/fundraising`)
* **Implementations:**
  * Uses a horizontal navigation list aligned with a bottom border (`border-b border-line`).
  * Individual tabs render as borderless buttons: `px-3 py-2 text-sm transition-colors border-b-2 -mb-px`.
  * Active states apply bold typography and dark indicator lines: `border-ink font-medium text-ink`.
  * Inactive states use muted typography and clear boundaries: `border-transparent text-muted hover:text-ink`.

#### E. Active Outreach Control Board Buttons (`/fundraising` tab `outreach`)
* **Implementations:**
  * Renders contextual status actions inline:
    * **Not Started:** Shows a dark button (`bg-ink text-white rounded-lg px-3 py-1.5`) labeled `Draft email`.
    * **Drafted:** Displays a `Review` toggle (`border border-line px-3 py-1.5 text-muted hover:text-ink`) beside an `Approve` button (`bg-ink text-white px-3 py-1.5`).
    * **Approved:** Displays a colored button (`bg-accent text-white px-3 py-1.5`) labeled `Send via Gmail`.
    * **Sent:** Renders a static checkmark label: `text-good font-medium` reading `sent ✓`.
