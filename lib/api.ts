// Thin client for the CBO backend. The frontend contains NO business logic —
// it renders whatever the backend returns. Every call hits a real endpoint
// backed by Company Memory.

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

// ---- shared shapes (mirror backend JSON) ----
export interface Company { id: string; name: string; what: string; customers: string; stage: string; counts?: Counts }
export interface Counts { entities: number; facts: number; relationships: number; timeline: number; chunks: number; documents: number; investors: number }
export interface Fact { id: string; type: string; key: string; label: string; value: string; num: number | null; source_kind: string; source_ref: string; evidence: string; confidence: number; version: number; owner: string; entity_id: string | null }
export interface Entity { id: string; type: string; name: string }
export interface Edge { from_id: string; to_id: string; relation: string }
export interface TimelineEvent { id: string; at: number; connector_id: string; kind: string; title: string; summary: string; who: string[]; why: string; evidence: string; confidence: number; what_changed: string; agents: string[]; entity_ids: string[] }
export interface Metrics { revenue: number | null; monthly_spend: number | null; growth: number | null; retention: number | null; headcount: number | null; customers: number | null; raise_target: number | null; tam: number | null; has_investors: boolean; health: number; fundraising_readiness: number; execution_health: number; market_position: number }
export interface BriefItem { section: string; title: string; why: string; changed: string; matters: string; next: string; severity: "high" | "medium" | "low"; source?: { ref: string; excerpt: string } | null }
export interface Brief { company: Company; metrics: Metrics; summary: string; items: BriefItem[] }
export interface AskResult { answer: string; confidence: number; sources: { source: string; excerpt: string }[]; connected_memories: string[]; evidence_count: number }
export interface ConnectorInfo { id: string; name: string; category: string; blurb: string; requires_credential: boolean; oauth?: boolean; connected: boolean; last_sync: number | null; record_count: number; has_credential: boolean }
export interface Investor { id: string; name: string; firm: string; partner: string; sector: string; stage: string; geography: string; state: string; warmth: number; probability: number; last_touch: string; concerns: string[]; history: { at: string; note: string; tone: string }[]; sentiment?: string }
export interface Verdict { agent: string; stance: string; evidence: string[]; pros: string[]; cons: string[]; recommendation: string; confidence: number; framework?: string }
export interface CouncilResult { question: string; plan: { intent: string; selected_agents: string[]; rationale: string }; verdicts: Verdict[]; debate: { agent: string; point: string }[]; synthesis: { headline: string; rationale: string; confidence: number; next_actions: string[]; dissent: string[] }; governance: { approved: boolean; checks: { check: string; status: string; note: string }[] } }

export const api = {
  startOnboarding: (name: string) => req<Company>("/onboarding/start", { method: "POST", body: JSON.stringify({ name }) }),
  answer: (company_id: string, key: string, text: string) =>
    req<{ captured: { label: string; value: string }[] }>("/onboarding/answer", { method: "POST", body: JSON.stringify({ company_id, key, text }) }),
  getCompany: (id: string) => req<Company>(`/companies/${id}`),
  brief: (id: string) => req<Brief>(`/companies/${id}/brief`),
  ask: (id: string, query: string) => req<AskResult>(`/companies/${id}/brain/ask`, { method: "POST", body: JSON.stringify({ query }) }),
  graph: (id: string) => req<{ entities: Entity[]; edges: Edge[] }>(`/companies/${id}/graph`),
  facts: (id: string) => req<{ facts: Fact[] }>(`/companies/${id}/facts`),
  entityFacts: (id: string, eid: string) => req<{ facts: Fact[] }>(`/companies/${id}/entity/${eid}/facts`),
  timeline: (id: string) => req<{ timeline: TimelineEvent[] }>(`/companies/${id}/timeline`),
  connectors: (id: string) => req<{ connectors: ConnectorInfo[]; counts: Counts }>(`/companies/${id}/connectors`),
  connect: (id: string, cid: string, token?: string) =>
    req<{ status: string; message?: string; summary?: Record<string, unknown>; counts?: Counts }>(`/companies/${id}/connectors/${cid}/connect`, { method: "POST", body: JSON.stringify({ token: token || null }) }),
  sync: (id: string, cid: string) => req<{ status: string; summary?: Record<string, unknown>; counts?: Counts }>(`/companies/${id}/connectors/${cid}/sync`, { method: "POST" }),
  disconnect: (id: string, cid: string) => req<{ status: string }>(`/companies/${id}/connectors/${cid}/disconnect`, { method: "POST" }),
  oauthStart: (id: string, cid: string) => req<{ configured: boolean; authorize_url?: string; message?: string }>(`/companies/${id}/connectors/${cid}/oauth/start`),
  ingestText: (id: string, name: string, text: string) => req<{ summary: Record<string, number>; counts: Counts }>(`/companies/${id}/ingest/text`, { method: "POST", body: JSON.stringify({ name, text }) }),
  ingestUpload: async (id: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${BASE}/companies/${id}/ingest/upload`, { method: "POST", body: fd });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Upload failed");
    return res.json() as Promise<{ summary: Record<string, number>; chars: number; counts: Counts }>;
  },
  council: (id: string, question: string) => req<CouncilResult>(`/companies/${id}/council/ask`, { method: "POST", body: JSON.stringify({ question }) }),
  investors: (id: string) => req<{ investors: Investor[]; metrics: Metrics }>(`/companies/${id}/investors`),
  investor: (id: string, iid: string) => req<{ investor: Investor; next_best_action: string; meeting_prep: MeetingPrep; draft_followup: string }>(`/companies/${id}/investors/${iid}`),
  debrief: (id: string, iid: string, notes: string) => req<Debrief>(`/companies/${id}/investors/${iid}/debrief`, { method: "POST", body: JSON.stringify({ notes }) }),
};

export interface MeetingPrep { background: string; partner_interests: string[]; likely_objections: { objection: string; answer: string }[]; likely_questions: string[]; weak_spots: string[]; talking_points: string[] }
export interface Debrief { summary: string; sentiment: string; follow_up: string; tasks: string[] }

// ---- Phase 3: interview + fundraising ----
export interface InterviewQuestion { id: string; prompt: string; kind: "text" | "choice" | "upload"; options: string[] | null; attribute: string; context?: string }
export interface Dimension { key: string; label: string; confidence: number }
export interface Profile { stage: string | null; dimensions: Dimension[]; knowledge_confidence: number; missing: string[] }
export interface InterviewStep { question: InterviewQuestion | null; profile: Profile; done: boolean; captured?: { label: string; value: string }[] }

export interface PipelineStage { key: string; label: string; status: "done" | "active" | "todo" | "blocked"; progress: number; action: string; depends_on: string[] }
export interface Pipeline { stages: PipelineStage[]; overall_pct: number; done: number; total: number }
export interface Readiness { score: number; metrics: Metrics; missing_metrics: string[]; missing_docs: string[]; analysis: string }
export interface DeckSlide { title: string; bullets: string[]; needs_input: boolean }
export interface Deck { id: string; kind: string; version: number; title: string; content: { slides: DeckSlide[]; completeness: number } }
export interface RankedInvestor extends Investor { fit_score: number; fit_reasons: string[] }
export interface DataRoom { items: { key: string; label: string; present: boolean }[]; ready_pct: number }
export interface OutreachRow { investor_id: string; firm: string; name: string; state: string; probability: number; status: string; subject: string; body: string }
export interface TranscriptResult { sentiment: string; questions: string[]; concerns: string[]; risks: string[]; promises: string[]; follow_ups: string[]; follow_up_email: string; next_actions: string[] }

export const interviewApi = {
  next: (id: string) => req<InterviewStep>(`/companies/${id}/interview/next`),
  answer: (id: string, question_id: string, text: string) => req<InterviewStep>(`/companies/${id}/interview/answer`, { method: "POST", body: JSON.stringify({ question_id, text }) }),
  skip: (id: string, question_id: string) => req<InterviewStep>(`/companies/${id}/interview/skip`, { method: "POST", body: JSON.stringify({ question_id }) }),
  profile: (id: string) => req<Profile>(`/companies/${id}/profile`),
};

export const fundraisingApi = {
  pipeline: (id: string) => req<Pipeline>(`/companies/${id}/fundraising/pipeline`),
  readiness: (id: string) => req<Readiness>(`/companies/${id}/fundraising/readiness`),
  generateDeck: (id: string) => req<Deck>(`/companies/${id}/fundraising/deck`, { method: "POST" }),
  getDeck: (id: string) => req<Deck | { content: null }>(`/companies/${id}/fundraising/deck`),
  generateModel: (id: string) => req<{ content: { projection: { month: number; revenue: number; burn: number; net: number; cash: number | null }[]; runway_months: number | null } }>(`/companies/${id}/fundraising/financial-model`, { method: "POST" }),
  investors: (id: string) => req<{ investors: RankedInvestor[]; note: string }>(`/companies/${id}/fundraising/investors`),
  dataRoom: (id: string) => req<DataRoom>(`/companies/${id}/fundraising/data-room`),
  outreach: (id: string) => req<{ outreach: OutreachRow[] }>(`/companies/${id}/fundraising/outreach`),
  draft: (id: string, iid: string) => req<OutreachRow>(`/companies/${id}/fundraising/outreach/${iid}/draft`, { method: "POST" }),
  approve: (id: string, iid: string) => req<{ status: string }>(`/companies/${id}/fundraising/outreach/${iid}/approve`, { method: "POST" }),
  send: (id: string, iid: string) => req<{ status: string; message?: string }>(`/companies/${id}/fundraising/outreach/${iid}/send`, { method: "POST" }),
  transcript: (id: string, iid: string, transcript: string) => req<TranscriptResult>(`/companies/${id}/fundraising/meeting/${iid}/transcript`, { method: "POST", body: JSON.stringify({ transcript }) }),
};

// ---- Investor Intelligence Network ----
export interface WarmIntro { available: boolean; via: string | null; path: string }
export interface NetworkInvestor { id: string; firm: string; partners: string[]; stages: string[]; industries: string[]; geos: string[]; check_size: string; thesis: string; warm_intro: WarmIntro; fit_score: number; probability: number; reasons_for: string[]; reasons_against: string[] }
export interface Discover { total: number; worth_count: number; excellent_count: number; signals: { stage: string; sectors: string[]; geo: string }; investors: NetworkInvestor[] }
export interface FirmRecord { id: string; firm: string; partners: string[]; stages: string[]; industries: string[]; geos: string[]; check_size: string; fund: string; portfolio: string[]; recent: string[]; thesis: string; twitter: string; blog: string; preferred_revenue: string; source: string }
export interface Research { firm: FirmRecord; fit: { fit_score: number; probability: number; reasons_for: string[]; reasons_against: string[] }; warm_intro: WarmIntro; suggested_strategy: string; suggested_timing: string; projected_probability: number | null; suggested_narrative: string; suggested_deck_version: string; suggested_email: string; suggested_agenda: string[]; likely_questions: string[]; likely_objections: string[]; recommended_follow_up: string }

export const networkApi = {
  stats: () => req<{ firms: number }>("/network/stats"),
  discover: (id: string) => req<Discover>(`/companies/${id}/network/discover`),
  research: (id: string, firmId: string) => req<Research>(`/companies/${id}/network/${firmId}`),
  approach: (id: string, firmId: string) => req<{ investor_id: string; fit: { fit_score: number }; drafted: boolean }>(`/companies/${id}/network/${firmId}/approach`, { method: "POST" }),
};

// ---- Growth Agent & Outcome Tracking (v3) ----
export type RecStatus = "recommended" | "in_progress" | "completed" | "measured";
export interface Outcome { recommendation_id: string; outcome_metric: string; outcome_value: string; baseline_value: string; date_range: string; result_note: string; logged_at?: number }
export interface Recommendation { recommendation_id: string; category: string; title: string; detail: string; rationale: string; priority: number; confidence: number; evidence: string[]; playbook: string[]; expected_impact: string; effort: string; timeframe: string; status: RecStatus; outcome: Outcome | null; learning: string | null }
export interface LeadScore { lead_score: number | null; inputs_used: string[]; detail: Record<string, unknown> }
export interface GrowthResult { recommendations: Recommendation[]; lead_score: LeadScore; recent_outcomes: Outcome[]; note: string }

export const growthApi = {
  recommendations: (id: string) => req<GrowthResult>(`/companies/${id}/growth/recommendations`),
  setStatus: (id: string, rid: string, status: RecStatus) =>
    req<{ recommendation_id: string; status: RecStatus }>(`/companies/${id}/growth/recommendations/${rid}/status`, { method: "POST", body: JSON.stringify({ status }) }),
  logOutcome: (id: string, rid: string, body: { outcome_metric: string; outcome_value: string; baseline_value?: string; date_range?: string; result_note?: string }) =>
    req<Outcome>(`/companies/${id}/growth/recommendations/${rid}/outcome`, { method: "POST", body: JSON.stringify(body) }),
  outcomes: (id: string) => req<{ outcomes: Outcome[] }>(`/companies/${id}/growth/outcomes`),
  leadScore: (id: string) => req<LeadScore>(`/companies/${id}/leads/score`),
};

// ---- Business Intelligence Dashboard v2 ----
export type TileStatus = "ok" | "warn" | "insufficient";
export interface RecTile { recommendation_id: string; title: string; status: RecStatus; confidence: number; outcome_badge: string }
export interface RiskAlert { title: string; detail: string; severity: "high" | "medium" | "low" }
export interface DashboardTile {
  key: string; label: string; kind: "score" | "money" | "ratio" | "list";
  value: number | null; display?: string; status: TileStatus; detail: string;
  items?: (RecTile | RiskAlert)[];
}
export interface Dashboard { tiles: DashboardTile[]; executive_summary: string; metrics: Metrics; generated_at: number }

export const dashboardApi = {
  get: (id: string) => req<Dashboard>(`/companies/${id}/dashboard`),
};

// ---- Competitor Analysis (v2) ----
export interface CompetitorRecord { name: string; features: string; pricing: string; positioning: string; notes: string }
export interface ComparisonRow { dimension: string; us: string; competitors: { name: string; value: string }[] }
export interface Comparison {
  us: { name: string; features: string; pricing: string; positioning: string };
  competitors: CompetitorRecord[];
  table: ComparisonRow[];
  where_you_win: string[];
  where_youre_exposed: string[];
  insufficient: boolean;
  note: string;
  discovered?: number;
  added?: string[];
  provider?: string;
}

export const competitorApi = {
  get: (id: string) => req<Comparison>(`/companies/${id}/competitors`),
  add: (id: string, body: { name: string; features?: string; pricing?: string; positioning?: string; notes?: string }) =>
    req<Comparison>(`/companies/${id}/competitors`, { method: "POST", body: JSON.stringify(body) }),
  discover: (id: string) => req<Comparison>(`/companies/${id}/competitors/discover`, { method: "POST" }),
};

export function fmtMoney(n: number | null): string {
  if (n === null || n === undefined) return "—";
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) { const v = n / 1e6; return `$${Number.isInteger(v) ? v : v.toFixed(1)}M`; }
  if (n >= 1e3) return `$${Math.round(n / 1e3)}K`;
  return `$${Math.round(n)}`;
}
