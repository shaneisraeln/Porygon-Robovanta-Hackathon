"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireCompany } from "@/components/RequireCompany";
import { useStore } from "@/lib/store";
import {
  api, enginesApi, dealsApi, growthApi, fmtMoney,
  StrategyResult, MarketingResult, LeadGenResult, SalesResult, AnalyticsResult,
  SuccessOverview, SuccessBrief, ChatResult, Recommendation, RecStatus, Deal, DealsResponse, Conf,
} from "@/lib/api";

const TABS = [
  { key: "strategy", label: "Strategy" },
  { key: "marketing", label: "Marketing" },
  { key: "leadgen", label: "Lead Gen" },
  { key: "sales", label: "Sales" },
  { key: "analytics", label: "Analytics" },
  { key: "success", label: "Customer Success" },
] as const;

const TAGLINE: Record<string, string> = {
  strategy: "Market research, positioning, pricing and your go-to-market game plan.",
  marketing: "A channel-by-channel promotion plan — grounded, honest, executable this week.",
  leadgen: "Ranked acquisition tactics — digital, WhatsApp, referral and offline, only where they fit.",
  sales: "Your live deal pipeline + an AI pipeline review that flags what needs action now.",
  analytics: "Measured facts, labeled forecasts, competitive insight and an executive read.",
  success: "A CRM, support desk, AI chatbot, and a health/triage brief.",
};

// ---------------- shared UI ----------------

const CONF_STYLE: Record<string, string> = { high: "text-good", medium: "text-warn", low: "text-faint" };
function ConfPill({ c }: { c?: Conf }) {
  if (!c) return null;
  return <span className={`text-[11px] ${CONF_STYLE[c]}`}>{c} confidence</span>;
}

function Meta({ by, version }: { by?: string; version?: number }) {
  if (!by) return null;
  const label = by === "local-ai" ? "Local AI" : by === "heuristic" ? "Built-in advisor" : by;
  return <span className="text-[11px] text-faint">{label}{version ? ` · v${version}` : ""}</span>;
}

function GenerateBar({ label, busy, onGen, by, version }: { label: string; busy: boolean; onGen: () => void; by?: string; version?: number }) {
  return (
    <div className="mb-5 flex items-center justify-between">
      <Meta by={by} version={version} />
      <button onClick={onGen} disabled={busy} className="rounded-xl bg-ink px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">
        {busy ? "Generating…" : label}
      </button>
    </div>
  );
}

function Loading({ text = "Loading…" }: { text?: string }) {
  return <div className="flex items-center gap-3 py-8 text-sm text-muted animate-fade"><span className="h-2 w-2 animate-breathe rounded-full bg-accent" />{text}</div>;
}

function Empty({ text, busy, onGen }: { text: string; busy: boolean; onGen: () => void }) {
  return (
    <div className="rounded-2xl border border-dashed border-line bg-surface p-8 text-center">
      <p className="text-[15px] text-muted">{text}</p>
      <button onClick={onGen} disabled={busy} className="mt-4 rounded-xl bg-ink px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">
        {busy ? "Generating…" : "Generate now"}
      </button>
    </div>
  );
}

function Card({ title, right, children }: { title: string; right?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-5">
      <div className="mb-2 flex items-center justify-between"><p className="text-[11px] uppercase tracking-wider text-faint">{title}</p>{right}</div>
      {children}
    </div>
  );
}

function Bullets({ items }: { items?: string[] }) {
  if (!items?.length) return null;
  return <ul className="space-y-1.5">{items.map((t, i) => <li key={i} className="text-[14px] text-muted">• {t}</li>)}</ul>;
}

function Flags({ items }: { items?: string[] }) {
  if (!items?.length) return null;
  return (
    <div className="rounded-xl border border-warn/30 bg-warn/[0.05] p-3">
      <p className="text-[11px] uppercase tracking-wider text-warn">Insufficient data</p>
      <ul className="mt-1 space-y-1">{items.map((t, i) => <li key={i} className="text-[13px] text-muted">• {t}</li>)}</ul>
    </div>
  );
}

// ---------------- Strategy ----------------

function StrategyTab({ companyId }: { companyId: string }) {
  const [d, setD] = useState<StrategyResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  useEffect(() => { enginesApi.strategyGet(companyId).then(setD).catch(() => {}).finally(() => setLoading(false)); }, [companyId]);
  const gen = async () => { setBusy(true); try { setD(await enginesApi.strategyGen(companyId)); } finally { setBusy(false); } };

  if (loading) return <Loading text="Reading your business…" />;
  if (!d || d.empty) return <Empty text="No strategy yet. Generate a positioning, pricing recommendation and a GTM sequence." busy={busy} onGen={gen} />;

  return (
    <div>
      <GenerateBar label="Regenerate" busy={busy} onGen={gen} by={d.generated_by} version={d.version} />
      <div className="grid gap-4">
        {d.positioning && (
          <Card title="Positioning" right={<ConfPill c={d.positioning.confidence} />}>
            <p className="text-[15px] leading-relaxed text-ink">{d.positioning.statement}</p>
            {d.positioning.grounded_in?.length ? <p className="mt-2 text-[12px] text-faint">Grounded in: {d.positioning.grounded_in.join(" · ")}</p> : null}
          </Card>
        )}
        {d.pricing && (
          <Card title="Pricing" right={<ConfPill c={d.pricing.confidence} />}>
            <p className="text-[14px] font-medium text-ink">{d.pricing.recommendation}</p>
            <p className="mt-1 text-[13px] text-muted">{d.pricing.rationale}</p>
          </Card>
        )}
        {d.gtm_sequence?.length ? (
          <Card title="Go-to-market sequence">
            <ol className="space-y-2">
              {d.gtm_sequence.map((s, i) => (
                <li key={i} className="flex gap-2 text-[14px]">
                  <span className="grid h-4 w-4 shrink-0 place-items-center rounded-full bg-accent/10 text-[10px] font-medium text-accent">{i + 1}</span>
                  <span><span className="text-ink">{s.step}</span> <span className="text-faint">— {s.why_this_first}</span></span>
                </li>
              ))}
            </ol>
          </Card>
        ) : null}
        <Flags items={d.insufficient_data_flags} />
      </div>
    </div>
  );
}

// ---------------- Marketing ----------------

const CHANNEL_LABEL: Record<string, string> = {
  content_seo: "Content / SEO", paid: "Paid ads", organic_social: "Organic social",
  pr_partnerships: "PR & partnerships", brand: "Brand",
};

function MarketingTab({ companyId }: { companyId: string }) {
  const [d, setD] = useState<MarketingResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  useEffect(() => { enginesApi.marketingGet(companyId).then(setD).catch(() => {}).finally(() => setLoading(false)); }, [companyId]);
  const gen = async () => { setBusy(true); try { setD(await enginesApi.marketingGen(companyId)); } finally { setBusy(false); } };

  return (
    <div>
      {loading ? <Loading /> : (!d || d.empty) ? (
        <Empty text="No marketing plan yet. Generate a channel-by-channel plan grounded in your data." busy={busy} onGen={gen} />
      ) : (
        <>
          <GenerateBar label="Regenerate" busy={busy} onGen={gen} by={d.generated_by} version={d.version} />
          <div className="grid gap-3 sm:grid-cols-2">
            {d.channels && Object.entries(d.channels).map(([key, ch]) => (
              <div key={key} className={`rounded-2xl border bg-surface p-4 ${ch.status === "insufficient_data" ? "border-dashed border-line" : "border-line"}`}>
                <div className="flex items-center justify-between">
                  <p className="text-[14px] font-medium text-ink">{CHANNEL_LABEL[key] ?? key}</p>
                  {ch.status === "insufficient_data" ? <span className="text-[11px] text-faint">insufficient data</span> : <ConfPill c={ch.confidence} />}
                </div>
                {ch.status === "ok" ? (
                  <>
                    <p className="mt-1.5 text-[14px] text-ink">{ch.tactic}</p>
                    <p className="mt-1 text-[13px] text-muted">{ch.rationale}</p>
                  </>
                ) : <p className="mt-1.5 text-[13px] text-faint">Not enough data to justify this channel yet.</p>}
              </div>
            ))}
          </div>
        </>
      )}
      <div className="mt-8"><TrackedPlays companyId={companyId} /></div>
    </div>
  );
}

export default function GrowthPage() {
  return <RequireCompany><Growth /></RequireCompany>;
}

function Growth() {
  const companyId = useStore((s) => s.companyId)!;
  const [tab, setTab] = useState<string>("strategy");
  return (
    <div className="mx-auto max-w-4xl px-5 pb-24 pt-10 sm:px-8">
      <div className="animate-fade-up">
        <h1 className="h-display text-3xl text-ink sm:text-4xl">Growth Engines</h1>
        <p className="mt-2 max-w-reading text-[16px] leading-relaxed text-muted">{TAGLINE[tab]}</p>
      </div>
      <div className="mt-6 flex flex-wrap gap-1.5 border-b border-line pb-2">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)} className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${tab === t.key ? "bg-ink text-white" : "text-muted hover:text-ink"}`}>{t.label}</button>
        ))}
      </div>
      <div className="mt-6 animate-fade">
        {tab === "strategy" && <StrategyTab companyId={companyId} />}
        {tab === "marketing" && <MarketingTab companyId={companyId} />}
        {tab === "leadgen" && <LeadGenTab companyId={companyId} />}
        {tab === "sales" && <SalesTab companyId={companyId} />}
        {tab === "analytics" && <AnalyticsTab companyId={companyId} />}
        {tab === "success" && <SuccessTab companyId={companyId} />}
      </div>
    </div>
  );
}

// ---------------- Lead Gen ----------------

const LEAD_CH: Record<string, string> = { digital: "Digital", whatsapp: "WhatsApp", physical: "Physical / local", referral: "Referral" };

function LeadGenTab({ companyId }: { companyId: string }) {
  const [d, setD] = useState<LeadGenResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  useEffect(() => { enginesApi.leadgenGet(companyId).then(setD).catch(() => {}).finally(() => setLoading(false)); }, [companyId]);
  const gen = async () => { setBusy(true); try { setD(await enginesApi.leadgenGen(companyId)); } finally { setBusy(false); } };

  if (loading) return <Loading text="Finding prospects and fitting channels…" />;
  if (!d || d.empty) return <Empty text="No lead-gen plan yet. Generate ranked acquisition tactics fitted to your business." busy={busy} onGen={gen} />;

  return (
    <div>
      <GenerateBar label="Regenerate" busy={busy} onGen={gen} by={d.generated_by} version={d.version} />
      {d.channel_risk_flag && (
        <div className="mb-4 rounded-xl border border-danger/30 bg-danger/[0.05] p-3 text-[13px] text-ink">
          <span className="text-[11px] uppercase tracking-wider text-danger">Channel risk</span>
          <p className="mt-1">{d.channel_risk_flag}</p>
        </div>
      )}
      <div className="grid gap-3">
        {d.recommendations?.map((r, i) => (
          <div key={i} className="rounded-2xl border border-line bg-surface p-4">
            <div className="flex items-center justify-between">
              <span className="rounded-full bg-canvas px-2.5 py-0.5 text-[11px] text-muted">{LEAD_CH[r.channel] ?? r.channel}</span>
              <ConfPill c={r.confidence} />
            </div>
            <p className="mt-2 text-[14px] font-medium text-ink">{r.tactic}</p>
            <p className="mt-1 text-[13px] text-muted">{r.rationale}</p>
          </div>
        ))}
      </div>
      {d.withheld_channels?.length ? (
        <div className="mt-4">
          <Card title="Not recommended (no supporting data)">
            <div className="space-y-1.5">
              {d.withheld_channels.map((w, i) => (
                <p key={i} className="text-[13px] text-muted"><span className="text-ink">{LEAD_CH[w.channel] ?? w.channel}:</span> {w.reason}</p>
              ))}
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  );
}

// ---------------- Sales (deal pipeline + AI review) ----------------

function SalesTab({ companyId }: { companyId: string }) {
  const [data, setData] = useState<DealsResponse | null>(null);
  const [review, setReview] = useState<SalesResult | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => { dealsApi.list(companyId).then(setData).catch(() => {}); }, [companyId]);
  useEffect(() => { load(); enginesApi.salesGet(companyId).then((r) => { if (!r.empty) setReview(r); }).catch(() => {}); }, [companyId, load]);

  async function runReview() { setBusy(true); try { setReview(await enginesApi.salesGen(companyId)); } finally { setBusy(false); } }

  const m = data?.metrics;
  return (
    <div className="grid gap-5">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Open deals" value={m?.open ?? 0} />
        <Stat label="Open value" value={fmtMoney(m?.open_value ?? 0)} />
        <Stat label="Won" value={m?.won ?? 0} />
        <Stat label="Win rate" value={m?.win_rate != null ? `${m.win_rate}%` : "—"} />
      </div>

      <AddDeal companyId={companyId} stages={data?.stages ?? []} onAdd={load} />

      <Card title="Pipeline" right={<button onClick={runReview} disabled={busy} className="rounded-lg bg-ink px-3 py-1.5 text-[12px] font-medium text-white disabled:opacity-50">{busy ? "Reviewing…" : "AI pipeline review"}</button>}>
        {data?.deals.length ? (
          <div className="space-y-2">
            {data.deals.map((dl) => <DealRow key={dl.id} companyId={companyId} deal={dl} stages={data.stages} onChange={load} />)}
          </div>
        ) : <p className="text-[13px] text-faint">No deals yet. Add one above to start tracking your pipeline.</p>}
      </Card>

      {review && (
        <div className="grid gap-4">
          {review.pipeline_insight && <Card title="Pipeline insight"><p className="text-[14px] text-ink">{review.pipeline_insight}</p></Card>}
          {review.urgent_actions?.length ? (
            <Card title="Needs action now">
              <div className="space-y-2.5">
                {review.urgent_actions.map((a, i) => (
                  <div key={i} className="border-b border-line pb-2 last:border-0">
                    <p className="text-[14px] font-medium text-ink">{a.deal_name} <span className="text-faint">· {a.stage} · {a.days_in_stage}d</span></p>
                    <p className="text-[13px] text-accent">→ {a.recommended_action}</p>
                    <p className="text-[12px] text-muted">{a.rationale}</p>
                  </div>
                ))}
              </div>
            </Card>
          ) : null}
          {review.on_track?.length ? (
            <Card title="On track"><Bullets items={review.on_track.map((o) => `${o.deal_name} — ${o.stage}`)} /></Card>
          ) : null}
          <Flags items={review.insufficient_data_flags} />
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-xl border border-line bg-surface p-3"><p className="text-[11px] uppercase tracking-wider text-faint">{label}</p><p className="text-2xl font-semibold text-ink">{value}</p></div>;
}

function AddDeal({ companyId, stages, onAdd }: { companyId: string; stages: string[]; onAdd: () => void }) {
  const [name, setName] = useState("");
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    try { await dealsApi.create(companyId, { name: name.trim(), value: Number(value) || 0 }); setName(""); setValue(""); onAdd(); }
    finally { setBusy(false); }
  }
  const field = "rounded-xl border border-line bg-canvas px-3 py-2 text-[14px] outline-none placeholder:text-faint focus:border-accent";
  return (
    <form onSubmit={add} className="flex flex-wrap items-center gap-2">
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="New deal (customer name)" className={`${field} flex-1`} />
      <input value={value} onChange={(e) => setValue(e.target.value)} placeholder="Value" inputMode="numeric" className={`${field} w-28`} />
      <button type="submit" disabled={busy || !name.trim()} className="rounded-xl bg-ink px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Add deal</button>
    </form>
  );
}

const STAGE_COLOR: Record<string, string> = { Lead: "#6b6b76", Qualified: "#0891b2", Demo: "#b7791f", Proposal: "#5b54e8", Won: "#1a8f5c", Lost: "#d1453b" };

function DealRow({ companyId, deal, stages, onChange }: { companyId: string; deal: Deal; stages: string[]; onChange: () => void }) {
  async function move(stage: string) { await dealsApi.moveStage(companyId, deal.id, stage); onChange(); }
  return (
    <div className="flex items-center gap-3 border-b border-line pb-2 last:border-0">
      <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: STAGE_COLOR[deal.stage] ?? "#6b6b76" }} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-[14px] text-ink">{deal.name} {deal.value ? <span className="text-faint">· {fmtMoney(deal.value)}</span> : null}</p>
        <p className="text-[11px] text-faint">{deal.stage} · {deal.days_in_stage}d in stage</p>
      </div>
      <select value={deal.stage} onChange={(e) => move(e.target.value)} className="rounded-lg border border-line bg-surface px-2 py-1 text-[12px] outline-none focus:border-accent">
        {stages.map((s) => <option key={s} value={s}>{s}</option>)}
      </select>
    </div>
  );
}

// ---------------- Analytics ----------------

function AnalyticsTab({ companyId }: { companyId: string }) {
  const [d, setD] = useState<AnalyticsResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  useEffect(() => { enginesApi.analyticsGet(companyId).then(setD).catch(() => {}).finally(() => setLoading(false)); }, [companyId]);
  const gen = async () => { setBusy(true); try { setD(await enginesApi.analyticsGen(companyId)); } finally { setBusy(false); } };

  if (loading) return <Loading text="Crunching the numbers…" />;
  if (!d) return <Loading />;

  return (
    <div>
      <GenerateBar label={d.measured_summary ? "Refresh AI insights" : "Generate AI insights"} busy={busy} onGen={gen} by={d.generated_by} version={d.version} />
      {(d.executive_summary_ai || d.executive_summary) && <Card title="Executive summary"><p className="text-[14px] leading-relaxed text-ink">{d.executive_summary_ai || d.executive_summary}</p></Card>}

      {d.kpis?.length ? (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {d.kpis.filter((t) => t.kind !== "list").map((t) => (
            <div key={t.key} className="rounded-xl border border-line bg-surface p-3">
              <p className="text-[11px] uppercase tracking-wider text-faint">{t.label}</p>
              <p className="text-2xl font-semibold text-ink">{t.display ?? (t.value !== null ? Math.round(t.value as number) : "—")}</p>
            </div>
          ))}
        </div>
      ) : null}

      {d.measured_summary?.length ? (
        <div className="mt-4"><Card title="Measured (what happened)">
          <div className="space-y-1.5">
            {d.measured_summary.map((mm, i) => (
              <div key={i} className="flex justify-between text-[14px]"><span className="text-ink">{mm.metric}</span><span className="text-muted">{mm.value} {mm.trend !== "—" ? `· ${mm.trend}` : ""}</span></div>
            ))}
          </div>
        </Card></div>
      ) : null}

      {d.forecasts?.length ? (
        <div className="mt-4"><Card title="Forecasts (projections, not guarantees)">
          <div className="space-y-1.5">
            {d.forecasts.map((f, i) => (
              <div key={i} className="text-[14px]">
                {f.status === "insufficient_data" ? (
                  <span className="text-muted">{f.metric}: <span className="text-faint">insufficient data to forecast</span></span>
                ) : (
                  <span className="text-ink">{f.metric}: {f.projected_value} <span className="text-faint">— {f.method} ({f.confidence})</span></span>
                )}
              </div>
            ))}
          </div>
        </Card></div>
      ) : null}

      {d.numeric_forecast?.projection?.length ? (
        <div className="mt-4"><Card title="6-month projection">
          <div className="space-y-1">
            {d.numeric_forecast.projection.map((p) => (
              <div key={p.month} className="flex justify-between text-[13px]"><span className="text-faint">Month {p.month}</span><span className="text-muted">rev {fmtMoney(p.revenue)} · net {fmtMoney(p.net)}{p.cash !== null ? ` · cash ${fmtMoney(p.cash)}` : ""}</span></div>
            ))}
          </div>
          {d.numeric_forecast.runway_months != null && <p className="mt-2 text-[12px] text-faint">Runway: ~{d.numeric_forecast.runway_months} months</p>}
        </Card></div>
      ) : null}

      {d.competitive_insight?.length ? (
        <div className="mt-4"><Card title="Competitive insight">
          <div className="space-y-1.5">
            {d.competitive_insight.map((ci, i) => <p key={i} className="text-[14px] text-ink">{ci.insight} <span className="text-faint">({ci.grounded_in})</span></p>)}
          </div>
        </Card></div>
      ) : null}
    </div>
  );
}

// ---------------- Customer Success ----------------

function SuccessTab({ companyId }: { companyId: string }) {
  const [d, setD] = useState<SuccessOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const load = useCallback(() => { enginesApi.successGet(companyId).then(setD).catch(() => {}).finally(() => setLoading(false)); }, [companyId]);
  useEffect(() => { load(); }, [load]);

  if (loading) return <Loading />;
  return (
    <div className="grid gap-4">
      <div className="grid grid-cols-3 gap-3">
        <Stat label="Customers" value={d?.customers.length ?? 0} />
        <Stat label="Health" value={d?.customer_health != null ? Math.round(d.customer_health) : "—"} />
        <Stat label="Open tickets" value={d?.open_tickets ?? 0} />
      </div>

      <SuccessBriefCard companyId={companyId} />
      <SuccessChat companyId={companyId} />
      <TeachChatbot companyId={companyId} />

      {d?.customers.length ? (
        <Card title="CRM · customers">
          <div className="space-y-2">
            {d.customers.map((c) => (
              <div key={c.id} className="border-b border-line pb-2 last:border-0">
                <p className="text-[14px] font-medium text-ink">{c.name}</p>
                {c.notes.map((n, i) => <p key={i} className="text-[12px] text-muted">{n}</p>)}
              </div>
            ))}
          </div>
        </Card>
      ) : <Card title="CRM · customers"><p className="text-[13px] text-faint">No customers in memory yet. They appear as you add them or connect a source.</p></Card>}

      <TicketDesk companyId={companyId} tickets={d?.tickets ?? []} onChange={load} />
      <FaqCard companyId={companyId} initial={d?.faqs ?? []} />
    </div>
  );
}

function SuccessBriefCard({ companyId }: { companyId: string }) {
  const [d, setD] = useState<SuccessBrief | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { enginesApi.successBriefGet(companyId).then((r) => { if (!r.empty) setD(r); }).catch(() => {}); }, [companyId]);
  const gen = async () => { setBusy(true); try { setD(await enginesApi.successBriefGen(companyId)); } finally { setBusy(false); } };

  return (
    <Card title="Customer success brief" right={<button onClick={gen} disabled={busy} className="rounded-lg bg-ink px-3 py-1.5 text-[12px] font-medium text-white disabled:opacity-50">{busy ? "Analyzing…" : d ? "Refresh" : "Generate"}</button>}>
      {!d ? <p className="text-[13px] text-faint">Generate a health read, ticket triage and retention actions.</p> : (
        <div className="space-y-3">
          {d.health_read && (
            <div>
              <div className="flex items-center gap-2"><p className="text-[13px] font-medium text-ink">Health</p><ConfPill c={d.health_read.confidence} /></div>
              <p className="text-[13px] text-muted">{d.health_read.summary}</p>
              {d.health_read.at_risk_signals?.length ? <ul className="mt-1">{d.health_read.at_risk_signals.map((s, i) => <li key={i} className="text-[12px] text-warn">⚠ {s}</li>)}</ul> : null}
            </div>
          )}
          {d.ticket_triage?.length ? (
            <div>
              <p className="text-[13px] font-medium text-ink">Ticket triage</p>
              {d.ticket_triage.map((t, i) => (
                <div key={i} className="mt-1"><p className="text-[13px] text-ink">{t.subject} <span className="text-faint">· {t.priority}</span></p><p className="text-[12px] text-muted">↳ {t.suggested_reply}</p></div>
              ))}
            </div>
          ) : null}
          {d.retention_actions?.length ? <div><p className="text-[13px] font-medium text-ink">Retention actions</p><Bullets items={d.retention_actions} /></div> : null}
          <Flags items={d.insufficient_data_flags} />
        </div>
      )}
    </Card>
  );
}

function SuccessChat({ companyId }: { companyId: string }) {
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [reply, setReply] = useState<ChatResult | null>(null);
  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!msg.trim()) return;
    setBusy(true);
    try { setReply(await enginesApi.successChat(companyId, msg.trim())); } finally { setBusy(false); }
  }
  return (
    <Card title="Support chatbot (AI)">
      <p className="mb-2 text-[12px] text-faint">Answers only from your knowledge base — add help docs below to teach it more.</p>
      <form onSubmit={send} className="flex items-center gap-2 rounded-xl border border-line bg-canvas px-2 py-1.5 focus-within:border-accent">
        <input value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="Ask a customer question…" className="flex-1 bg-transparent px-2 py-1.5 text-[14px] outline-none placeholder:text-faint" />
        <button type="submit" disabled={busy} className="rounded-lg bg-ink px-3 py-1.5 text-[13px] font-medium text-white disabled:opacity-50">{busy ? "…" : "Ask"}</button>
      </form>
      {reply && (
        <div className="mt-3">
          <p className="text-[14px] leading-relaxed text-ink">{reply.answer}</p>
          {reply.sources.length > 0 && <p className="mt-2 text-[11px] text-faint">Sources: {reply.sources.map((s) => s.source).slice(0, 3).join(", ")}</p>}
        </div>
      )}
    </Card>
  );
}

function TeachChatbot({ companyId }: { companyId: string }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  async function save() {
    if (!text.trim()) return;
    setBusy(true); setNote(null);
    try {
      const res = await api.ingestText(companyId, "support-knowledge.txt", text.trim());
      setText("");
      setNote(`Added — the chatbot learned ${res.summary.facts ?? 0} new facts.`);
      setTimeout(() => setNote(null), 6000);
    } catch { setNote("Couldn't save that. Try again."); }
    finally { setBusy(false); }
  }
  return (
    <Card title="Teach the chatbot">
      <p className="mb-2 text-[13px] text-muted">Paste help docs, FAQs, pricing or policies. The more you add, the more customer questions it can answer.</p>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} placeholder="e.g. Refund policy: cancel any time, pro-rated refund within 14 days…" className="w-full resize-none rounded-xl border border-line bg-canvas px-3 py-2 text-[14px] outline-none placeholder:text-faint focus:border-accent" />
      <div className="mt-2 flex items-center justify-between">
        {note ? <span className="text-[12px] text-good">{note}</span> : <span />}
        <button onClick={save} disabled={busy || !text.trim()} className="rounded-lg bg-ink px-3 py-1.5 text-[13px] font-medium text-white disabled:opacity-50">{busy ? "Saving…" : "Add to knowledge"}</button>
      </div>
    </Card>
  );
}

function FaqCard({ companyId, initial }: { companyId: string; initial: { q: string; a: string }[] }) {
  const [faqs, setFaqs] = useState(initial);
  const [busy, setBusy] = useState(false);
  useEffect(() => { setFaqs(initial); }, [initial]);
  async function gen() { setBusy(true); try { setFaqs((await enginesApi.successGenFaqs(companyId)).faqs); } finally { setBusy(false); } }
  return (
    <Card title="FAQ" right={<button onClick={gen} disabled={busy} className="rounded-lg border border-line px-3 py-1 text-[12px] text-muted hover:border-accent hover:text-ink disabled:opacity-50">{busy ? "Writing…" : "Generate with AI"}</button>}>
      <div className="space-y-2.5">
        {faqs.map((f, i) => (<div key={i}><p className="text-[14px] font-medium text-ink">{f.q}</p><p className="text-[13px] text-muted">{f.a}</p></div>))}
      </div>
    </Card>
  );
}

function TicketDesk({ companyId, tickets, onChange }: { companyId: string; tickets: { id: string; subject: string; body: string; status: string }[]; onChange: () => void }) {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [reply, setReply] = useState<string | null>(null);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!subject.trim()) return;
    setBusy(true);
    try { const res = await enginesApi.successTicket(companyId, subject.trim(), body.trim()); setReply(res.suggested_reply); setSubject(""); setBody(""); onChange(); }
    finally { setBusy(false); }
  }
  const field = "rounded-xl border border-line bg-canvas px-3 py-2 text-[14px] outline-none placeholder:text-faint focus:border-accent";
  return (
    <Card title="Support desk">
      <form onSubmit={submit} className="grid gap-2">
        <input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Ticket subject" className={field} />
        <textarea value={body} onChange={(e) => setBody(e.target.value)} placeholder="What's the issue?" rows={2} className={field} />
        <div><button type="submit" disabled={busy || !subject.trim()} className="rounded-lg bg-ink px-3 py-1.5 text-[13px] font-medium text-white disabled:opacity-50">{busy ? "Logging…" : "Log ticket + get AI reply"}</button></div>
      </form>
      {reply && <div className="mt-3 rounded-xl border border-accent/30 bg-accent/[0.04] p-3 text-[13px] text-ink"><span className="text-[11px] uppercase tracking-wider text-accent">Suggested reply</span><p className="mt-1">{reply}</p></div>}
      {tickets.length > 0 && (
        <div className="mt-3 space-y-1.5 border-t border-line pt-3">
          {tickets.map((t) => <p key={t.id} className="text-[13px] text-muted"><span className="text-ink">{t.subject}</span> — {t.body.slice(0, 80)}</p>)}
        </div>
      )}
    </Card>
  );
}

// ---------------- Tracked growth plays (outcome loop) ----------------

const REC_PILL: Record<RecStatus, string> = {
  recommended: "bg-line/60 text-muted", in_progress: "bg-warn/10 text-warn",
  completed: "bg-accent/10 text-accent", measured: "bg-good/10 text-good",
};
const REC_FLOW: RecStatus[] = ["recommended", "in_progress", "completed", "measured"];

function TrackedPlays({ companyId }: { companyId: string }) {
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const load = useCallback(() => { growthApi.recommendations(companyId).then((d) => setRecs(d.recommendations)).catch(() => {}).finally(() => setLoading(false)); }, [companyId]);
  useEffect(() => { load(); }, [load]);
  if (loading || recs.length === 0) return null;
  return (
    <div>
      <p className="mb-3 text-[11px] uppercase tracking-wider text-faint">Tracked plays (measured against outcomes)</p>
      <div className="space-y-3">{recs.map((r) => <PlayCard key={r.recommendation_id} rec={r} companyId={companyId} onChange={load} />)}</div>
    </div>
  );
}

function PlayCard({ rec, companyId, onChange }: { rec: Recommendation; companyId: string; onChange: () => void }) {
  const [busy, setBusy] = useState(false);
  const next = REC_FLOW[REC_FLOW.indexOf(rec.status) + 1];
  const canAdvance = next && next !== "measured";
  async function advance() {
    if (!next) return;
    setBusy(true);
    try { await growthApi.setStatus(companyId, rec.recommendation_id, next); onChange(); } finally { setBusy(false); }
  }
  return (
    <div className="rounded-2xl border border-line bg-surface p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-[14px] font-medium text-ink">{rec.title}</p>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${REC_PILL[rec.status]}`}>{rec.status.replace("_", " ")}</span>
      </div>
      <p className="mt-1 text-[13px] text-muted">{rec.detail}</p>
      {rec.outcome && <p className="mt-2 text-[12px] text-good">Outcome: {rec.outcome.outcome_metric} {rec.outcome.baseline_value || "—"} → {rec.outcome.outcome_value}</p>}
      {canAdvance && <button onClick={advance} disabled={busy} className="mt-2 rounded-lg border border-line px-3 py-1 text-[12px] text-muted hover:border-accent hover:text-ink disabled:opacity-50">Mark {next.replace("_", " ")}</button>}
    </div>
  );
}
