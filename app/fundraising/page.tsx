"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireCompany } from "@/components/RequireCompany";
import { useStore } from "@/lib/store";
import {
  fundraisingApi, fmtMoney, Pipeline, Readiness, Deck, RankedInvestor, DataRoom, OutreachRow, TranscriptResult,
} from "@/lib/api";

const TABS = [
  ["pipeline", "Pipeline"], ["readiness", "Readiness"], ["deck", "Pitch Deck"],
  ["investors", "Investors"], ["outreach", "Outreach"], ["meeting", "Meeting Intel"], ["dataroom", "Data Room"],
] as const;
type Tab = (typeof TABS)[number][0];

const statusColor: Record<string, string> = { done: "bg-good", active: "bg-accent", todo: "bg-line", blocked: "bg-danger" };
const statusText: Record<string, string> = { done: "text-good", active: "text-accent", todo: "text-faint", blocked: "text-danger" };

function WarRoom() {
  const companyId = useStore((s) => s.companyId)!;
  const [tab, setTab] = useState<Tab>("pipeline");

  return (
    <div className="mx-auto max-w-5xl px-5 pb-24 pt-10 sm:px-8">
      <div className="animate-fade-up">
        <h1 className="h-display text-3xl text-ink sm:text-4xl">Fundraising</h1>
        <p className="mt-2 max-w-reading text-[16px] leading-relaxed text-muted">
          Not a page that displays data — an operating system that executes the raise. Every stage is
          computed from Company Memory.
        </p>
      </div>

      <div className="mt-6 flex flex-wrap gap-1 border-b border-line">
        {TABS.map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)} className={`-mb-px border-b-2 px-3 py-2 text-sm transition-colors ${tab === k ? "border-ink font-medium text-ink" : "border-transparent text-muted hover:text-ink"}`}>{label}</button>
        ))}
      </div>

      <div className="mt-6">
        {tab === "pipeline" && <PipelineView companyId={companyId} onJump={setTab} />}
        {tab === "readiness" && <ReadinessView companyId={companyId} />}
        {tab === "deck" && <DeckView companyId={companyId} />}
        {tab === "investors" && <InvestorsView companyId={companyId} />}
        {tab === "outreach" && <OutreachView companyId={companyId} />}
        {tab === "meeting" && <MeetingView companyId={companyId} />}
        {tab === "dataroom" && <DataRoomView companyId={companyId} />}
      </div>
    </div>
  );
}

function PipelineView({ companyId, onJump }: { companyId: string; onJump: (t: Tab) => void }) {
  const [p, setP] = useState<Pipeline | null>(null);
  useEffect(() => { fundraisingApi.pipeline(companyId).then(setP).catch(() => {}); }, [companyId]);
  if (!p) return <Loading />;
  const jump: Record<string, Tab> = { deck: "deck", model: "deck", dataroom: "dataroom", discovered: "investors", ranked: "investors", drafted: "outreach", approved: "outreach", sent: "outreach", completed: "meeting", understood: "pipeline" };
  return (
    <div>
      <div className="mb-5 flex items-center gap-4">
        <div className="flex-1"><div className="h-2 w-full overflow-hidden rounded-full bg-line"><div className="h-full rounded-full bg-ink transition-all" style={{ width: `${p.overall_pct}%` }} /></div></div>
        <span className="text-sm font-semibold text-ink">{p.done}/{p.total} · {p.overall_pct}%</span>
      </div>
      <div className="divide-hair rounded-2xl border border-line bg-surface">
        {p.stages.map((s) => (
          <button key={s.key} onClick={() => jump[s.key] && onJump(jump[s.key])} className="row-hover flex w-full items-center gap-3 px-4 py-3 text-left">
            <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full ${statusColor[s.status]}`}>{s.status === "done" && <span className="text-[11px] text-white">✓</span>}</span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[15px] text-ink">{s.label}</span>
                <span className={`text-[11px] ${statusText[s.status]}`}>{s.status}</span>
              </div>
              {s.status !== "done" && s.action && <p className="text-[12px] text-faint">{s.action}{jump[s.key] ? " →" : ""}</p>}
            </div>
            {s.progress > 0 && s.status !== "done" && <span className="text-[11px] text-faint">{s.progress}%</span>}
          </button>
        ))}
      </div>
    </div>
  );
}

function ReadinessView({ companyId }: { companyId: string }) {
  const [r, setR] = useState<Readiness | null>(null);
  useEffect(() => { fundraisingApi.readiness(companyId).then(setR).catch(() => {}); }, [companyId]);
  if (!r) return <Loading />;
  return (
    <div className="space-y-5">
      <div className="flex items-center gap-5 rounded-2xl border border-line bg-surface p-5">
        <Ring v={r.score} />
        <div><p className="text-[10px] uppercase tracking-[0.18em] text-faint">Fundraising readiness</p><p className="text-2xl font-semibold text-ink">{r.score}%</p><p className="max-w-md text-sm text-muted">{r.analysis}</p></div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Card title="Missing metrics">{r.missing_metrics.length ? r.missing_metrics.map((m) => <Chip key={m} tone="warn">{m}</Chip>) : <p className="text-sm text-good">All core metrics captured ✓</p>}</Card>
        <Card title="Missing documents">{r.missing_docs.length ? r.missing_docs.map((m) => <Chip key={m} tone="danger">{m}</Chip>) : <p className="text-sm text-good">Data room complete ✓</p>}</Card>
      </div>
    </div>
  );
}

function DeckView({ companyId }: { companyId: string }) {
  const [deck, setDeck] = useState<Deck | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { fundraisingApi.getDeck(companyId).then((d) => setDeck((d as Deck).content ? (d as Deck) : null)).catch(() => {}); }, [companyId]);
  async function gen() { setBusy(true); try { setDeck(await fundraisingApi.generateDeck(companyId)); } finally { setBusy(false); } }
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted">{deck ? `Version ${deck.version} · ${deck.content.completeness}% complete (from memory)` : "Generate an investor-ready deck from Company Memory."}</p>
        <button onClick={gen} disabled={busy} className="rounded-xl bg-ink px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">{busy ? "Generating…" : deck ? "Regenerate" : "Generate deck"}</button>
      </div>
      {deck?.content.next_steps?.length ? (
        <div className="rounded-2xl border border-accent/30 bg-accent/[0.04] p-4">
          <p className="mb-1.5 text-[11px] uppercase tracking-wider text-accent">Next steps</p>
          <ul className="space-y-1">{deck.content.next_steps.map((n, i) => <li key={i} className="text-[13px] text-ink">→ {n}</li>)}</ul>
        </div>
      ) : null}
      {deck && (
        <div className="grid gap-3 sm:grid-cols-2">
          {deck.content.slides.map((s, i) => (
            <div key={i} className={`rounded-2xl border bg-surface p-4 ${s.needs_input ? "border-dashed border-warn/40" : "border-line"}`}>
              <div className="flex items-center justify-between"><p className="text-[11px] uppercase tracking-wider text-faint">Slide {i + 1}</p>{s.needs_input && <span className="text-[11px] text-warn">needs input</span>}</div>
              <h3 className="mt-0.5 text-[15px] font-semibold text-ink">{s.title}</h3>
              {s.bullets.length ? (
                <ul className="mt-2 space-y-1">{s.bullets.map((b, j) => <li key={j} className="text-[13px] text-muted">• {b}</li>)}</ul>
              ) : (
                <p className="mt-2 text-[13px] text-warn">{s.guidance || "Answer more in the interview to fill this."}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function InvestorsView({ companyId }: { companyId: string }) {
  const [data, setData] = useState<{ investors: RankedInvestor[]; note: string } | null>(null);
  useEffect(() => { fundraisingApi.investors(companyId).then(setData).catch(() => {}); }, [companyId]);
  if (!data) return <Loading />;
  if (!data.investors.length) return <Empty text="No investors in memory. Add them during the interview, connect Gmail, or upload notes — CBO never invents investors." />;
  return (
    <div className="space-y-3">
      <p className="text-[12px] text-faint">{data.note}</p>
      {data.investors.map((inv) => (
        <div key={inv.id} className="rounded-2xl border border-line bg-surface p-4">
          <div className="flex items-center justify-between">
            <div><p className="text-[15px] font-medium text-ink">{inv.firm}</p><p className="text-[13px] text-muted">{inv.name}{inv.sector ? ` · ${inv.sector}` : ""}</p></div>
            <div className="text-right"><p className="text-xl font-semibold text-ink">{inv.fit_score}</p><p className="text-[11px] text-faint">fit score</p></div>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">{inv.fit_reasons.map((r, i) => <span key={i} className="rounded-full bg-canvas px-2.5 py-1 text-[11px] text-muted">{r}</span>)}</div>
        </div>
      ))}
    </div>
  );
}

function OutreachView({ companyId }: { companyId: string }) {
  const [rows, setRows] = useState<OutreachRow[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const refresh = useCallback(() => { fundraisingApi.outreach(companyId).then((d) => setRows(d.outreach)).catch(() => {}); }, [companyId]);
  useEffect(() => { refresh(); }, [refresh]);
  async function draft(iid: string) { await fundraisingApi.draft(companyId, iid); refresh(); setOpen(iid); }
  async function approve(iid: string) { await fundraisingApi.approve(companyId, iid); refresh(); }
  async function send(iid: string) { const r = await fundraisingApi.send(companyId, iid); alert(r.message || r.status); refresh(); }
  if (!rows.length) return <Empty text="No investors to reach out to yet." />;
  return (
    <div className="space-y-3">
      {rows.map((o) => (
        <div key={o.investor_id} className="rounded-2xl border border-line bg-surface">
          <div className="flex items-center gap-3 px-4 py-3">
            <div className="min-w-0 flex-1"><p className="text-[15px] font-medium text-ink">{o.firm}</p><p className="text-[12px] text-faint">{o.status.replace("_", " ")} · {o.probability}%</p></div>
            {o.status === "not_started" && <button onClick={() => draft(o.investor_id)} className="rounded-lg bg-ink px-3 py-1.5 text-[13px] font-medium text-white hover:opacity-90">Draft email</button>}
            {o.status === "drafted" && <><button onClick={() => setOpen(open === o.investor_id ? null : o.investor_id)} className="rounded-lg border border-line px-3 py-1.5 text-[13px] text-muted hover:text-ink">Review</button><button onClick={() => approve(o.investor_id)} className="rounded-lg bg-ink px-3 py-1.5 text-[13px] font-medium text-white hover:opacity-90">Approve</button></>}
            {o.status === "approved" && <button onClick={() => send(o.investor_id)} className="rounded-lg bg-accent px-3 py-1.5 text-[13px] font-medium text-white hover:opacity-90">Send via Gmail</button>}
            {o.status === "sent" && <span className="text-[12px] text-good">sent ✓</span>}
          </div>
          {open === o.investor_id && o.body && (
            <div className="border-t border-line p-4"><p className="mb-1 text-[12px] text-faint">Subject: {o.subject}</p><pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-ink">{o.body}</pre></div>
          )}
        </div>
      ))}
    </div>
  );
}

function MeetingView({ companyId }: { companyId: string }) {
  const [investors, setInvestors] = useState<RankedInvestor[]>([]);
  const [iid, setIid] = useState<string>("");
  const [transcript, setTranscript] = useState("");
  const [res, setRes] = useState<TranscriptResult | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { fundraisingApi.investors(companyId).then((d) => { setInvestors(d.investors); setIid(d.investors[0]?.id || ""); }).catch(() => {}); }, [companyId]);
  async function analyze() { if (!iid || !transcript.trim()) return; setBusy(true); try { setRes(await fundraisingApi.transcript(companyId, iid, transcript)); } finally { setBusy(false); } }
  if (!investors.length) return <Empty text="Add an investor first to run meeting intelligence." />;
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">Paste a meeting transcript. CBO extracts questions, concerns, risks, promises and follow-ups, updates memory and the relationship, and drafts the follow-up.</p>
      <div className="flex items-center gap-2">
        <select value={iid} onChange={(e) => setIid(e.target.value)} className="rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-accent">
          {investors.map((i) => <option key={i.id} value={i.id}>{i.firm}</option>)}
        </select>
      </div>
      <textarea value={transcript} onChange={(e) => setTranscript(e.target.value)} rows={6} placeholder="Paste the transcript or your notes…" className="w-full resize-none rounded-xl border border-line bg-surface p-3 text-[14px] outline-none focus:border-accent" />
      <button onClick={analyze} disabled={busy || !transcript.trim()} className="rounded-xl bg-ink px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-40">{busy ? "Analyzing…" : "Run meeting intelligence"}</button>
      {res && (
        <div className="space-y-4 rounded-2xl border border-line bg-surface p-5">
          <p className="text-sm">Sentiment: <span className={res.sentiment === "positive" ? "text-good" : res.sentiment === "negative" ? "text-danger" : "text-muted"}>{res.sentiment}</span></p>
          <div className="grid gap-4 sm:grid-cols-2">
            <ListBlock title="Questions" items={res.questions} />
            <ListBlock title="Concerns" items={res.concerns} tone="text-warn" />
            <ListBlock title="Promises" items={res.promises} />
            <ListBlock title="Follow-ups" items={res.follow_ups} tone="text-accent" />
          </div>
          <div><p className="mb-1 text-[11px] uppercase tracking-wider text-faint">Drafted follow-up</p><pre className="whitespace-pre-wrap rounded-lg border border-line bg-canvas p-3 font-sans text-[13px] text-ink">{res.follow_up_email}</pre></div>
        </div>
      )}
    </div>
  );
}

function DataRoomView({ companyId }: { companyId: string }) {
  const [dr, setDr] = useState<DataRoom | null>(null);
  useEffect(() => { fundraisingApi.dataRoom(companyId).then(setDr).catch(() => {}); }, [companyId]);
  if (!dr) return <Loading />;
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3"><div className="flex-1 h-2 overflow-hidden rounded-full bg-line"><div className="h-full rounded-full bg-good" style={{ width: `${dr.ready_pct}%` }} /></div><span className="text-sm font-semibold text-ink">{dr.ready_pct}%</span></div>
      <div className="divide-hair rounded-2xl border border-line bg-surface">
        {dr.items.map((i) => (
          <div key={i.key} className="flex items-center gap-3 px-4 py-3">
            <span className={`grid h-5 w-5 place-items-center rounded-full ${i.present ? "bg-good" : "bg-line"}`}>{i.present && <span className="text-[11px] text-white">✓</span>}</span>
            <span className="flex-1 text-[15px] text-ink">{i.label}</span>
            <span className={`text-[12px] ${i.present ? "text-good" : "text-faint"}`}>{i.present ? "ready" : "missing"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// shared bits
function Loading() { return <div className="flex h-40 items-center justify-center"><div className="h-2 w-2 animate-breathe rounded-full bg-accent" /></div>; }
function Empty({ text }: { text: string }) { return <div className="rounded-2xl border border-line bg-surface p-8 text-center text-sm text-muted">{text}</div>; }
function Card({ title, children }: { title: string; children: React.ReactNode }) { return <div className="rounded-2xl border border-line bg-surface p-4"><p className="mb-2 text-[11px] uppercase tracking-wider text-faint">{title}</p><div className="flex flex-wrap gap-1.5">{children}</div></div>; }
function Chip({ children, tone }: { children: React.ReactNode; tone: "warn" | "danger" }) { return <span className={`rounded-full px-2.5 py-1 text-[12px] ${tone === "warn" ? "bg-warn/10 text-warn" : "bg-danger/10 text-danger"}`}>{children}</span>; }
function Ring({ v }: { v: number }) { const r = 30, c = 2 * Math.PI * r, o = c - (v / 100) * c; return <svg width="76" height="76" className="-rotate-90"><circle cx="38" cy="38" r={r} fill="none" stroke="#ececef" strokeWidth="6" /><circle cx="38" cy="38" r={r} fill="none" stroke="#5b54e8" strokeWidth="6" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={o} /></svg>; }
function ListBlock({ title, items, tone = "text-muted" }: { title: string; items: string[]; tone?: string }) { return <div><p className="mb-1 text-[11px] uppercase tracking-wider text-faint">{title}</p>{items.length ? <ul className="space-y-1">{items.map((it, i) => <li key={i} className={`text-[13px] ${tone}`}>• {it}</li>)}</ul> : <p className="text-[13px] text-faint">None detected.</p>}</div>; }

export default function FundraisingPage() {
  return <RequireCompany><WarRoom /></RequireCompany>;
}
