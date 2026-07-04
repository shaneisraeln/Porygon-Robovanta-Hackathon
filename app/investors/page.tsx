"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RequireCompany } from "@/components/RequireCompany";
import { useStore } from "@/lib/store";
import { networkApi, Discover, NetworkInvestor, Research } from "@/lib/api";

function fitColor(v: number) { return v >= 80 ? "text-good" : v >= 65 ? "text-accent" : v >= 50 ? "text-warn" : "text-faint"; }

function Network() {
  const companyId = useStore((s) => s.companyId)!;
  const [data, setData] = useState<Discover | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    networkApi.discover(companyId).then((d) => { setData(d); setSelected(d.investors[0]?.id ?? null); }).catch(() => setError("Couldn't reach the investor network."));
  }, [companyId]);

  if (error) return <div className="mx-auto max-w-reading px-5 pt-16 text-sm text-danger sm:px-8">{error}</div>;
  if (!data) return <div className="flex min-h-[60vh] items-center justify-center"><div className="h-2 w-2 animate-breathe rounded-full bg-accent" /></div>;

  return (
    <div className="mx-auto max-w-5xl px-5 pb-24 pt-10 sm:px-8">
      <div className="animate-fade-up">
        <h1 className="h-display text-3xl text-ink sm:text-4xl">Investor Intelligence</h1>
        <p className="mt-2 max-w-reading text-[16px] leading-relaxed text-muted">
          You never search. CBO continuously discovers, researches and ranks investors against your live
          Company Memory — then prepares every step of the outreach.
        </p>
        <p className="mt-4 text-[17px] text-ink">
          I scanned <span className="font-semibold">{data.total}</span> firms. After ranking,{" "}
          <span className="font-semibold text-accent">{data.worth_count}</span> are worth your time
          {data.excellent_count > 0 && <> · <span className="font-semibold text-good">{data.excellent_count}</span> are an excellent fit</>}.
        </p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Sig label={`Stage: ${data.signals.stage}`} />
          {data.signals.sectors.map((s) => <Sig key={s} label={s} />)}
          {data.signals.geo && <Sig label={data.signals.geo} />}
        </div>
      </div>

      <div className="mt-8 grid gap-8 lg:grid-cols-[340px_1fr]">
        <div>
          <p className="mb-2 text-[11px] uppercase tracking-wider text-faint">Ranked · top {Math.min(data.investors.length, 15)}</p>
          <div className="divide-hair rounded-2xl border border-line bg-surface">
            {data.investors.slice(0, 15).map((inv, i) => (
              <button key={inv.id} onClick={() => setSelected(inv.id)} className={`row-hover flex w-full items-center gap-3 px-4 py-3 text-left ${inv.id === selected ? "bg-canvas" : ""}`}>
                <span className="w-5 shrink-0 text-[12px] text-faint">{i + 1}</span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[15px] font-medium text-ink">{inv.firm}</p>
                  <p className="truncate text-[12px] text-muted">{inv.reasons_for[0] ?? inv.thesis}</p>
                </div>
                {inv.warm_intro.available && <span className="shrink-0 rounded-full bg-good/10 px-2 py-0.5 text-[10px] text-good">warm</span>}
                <span className={`shrink-0 text-[14px] font-semibold ${fitColor(inv.fit_score)}`}>{inv.fit_score}%</span>
              </button>
            ))}
          </div>
        </div>
        {selected && <ResearchPanel key={selected} companyId={companyId} firmId={selected} summary={data.investors.find((x) => x.id === selected)!} />}
      </div>
    </div>
  );
}

function ResearchPanel({ companyId, firmId, summary }: { companyId: string; firmId: string; summary: NetworkInvestor }) {
  const router = useRouter();
  const [r, setR] = useState<Research | null>(null);
  const [approached, setApproached] = useState(false);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => { networkApi.research(companyId, firmId).then(setR).catch(() => {}); }, [companyId, firmId]);
  if (!r) return <div className="rounded-2xl border border-line bg-surface p-8 text-sm text-faint">Researching…</div>;

  async function approach() { setBusy(true); try { await networkApi.approach(companyId, firmId); setApproached(true); } finally { setBusy(false); } }
  function copy() { navigator.clipboard?.writeText(r!.suggested_email); setCopied(true); setTimeout(() => setCopied(false), 1500); }

  return (
    <div className="animate-fade space-y-5">
      <div className="rounded-2xl border border-line bg-surface p-5">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-semibold text-ink">{r.firm.firm}</h2>
            <p className="text-sm text-muted">{r.firm.partners.join(", ")}</p>
            <p className="mt-1 text-[13px] text-faint">{r.firm.thesis}</p>
          </div>
          <div className="text-right">
            <p className={`text-2xl font-semibold ${fitColor(r.fit.fit_score)}`}>{r.fit.fit_score}%</p>
            <p className="text-[11px] text-faint">fit · {r.fit.probability}% prob</p>
          </div>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-[12px] text-muted sm:grid-cols-3">
          <span>Check: {r.firm.check_size}</span>
          <span>Stages: {r.firm.stages.join(", ")}</span>
          <span>Geo: {r.firm.geos.join(", ")}</span>
        </div>
        {r.firm.portfolio.length > 0 && <p className="mt-2 text-[12px] text-faint">Portfolio: {r.firm.portfolio.join(", ")}</p>}
      </div>

      {/* Strategy — executive thinking */}
      <div className="rounded-2xl border border-accent/30 bg-accent/[0.04] p-5">
        <p className="text-[11px] uppercase tracking-wider text-accent">CBO's strategy</p>
        <p className="mt-1.5 text-[15px] text-ink">{r.suggested_strategy}</p>
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px]">
          <span className="text-muted">Timing: <span className="text-ink">{r.suggested_timing}</span></span>
          {r.projected_probability != null && <span className="text-muted">If you wait: <span className="text-good">{r.fit.probability}% → {r.projected_probability}%</span></span>}
          <span className="text-muted">Warm intro: <span className={r.warm_intro.available ? "text-good" : "text-faint"}>{r.warm_intro.available ? r.warm_intro.path : "none yet"}</span></span>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card title="Why it's a fit">{r.fit.reasons_for.length ? r.fit.reasons_for.map((x, i) => <li key={i} className="text-[13px] text-good">+ {x}</li>) : <li className="text-[13px] text-faint">—</li>}</Card>
        <Card title="Reasons against / gaps">{r.fit.reasons_against.length ? r.fit.reasons_against.map((x, i) => <li key={i} className="text-[13px] text-warn">− {x}</li>) : <li className="text-[13px] text-good">No major gaps</li>}</Card>
        <Card title="Likely questions">{r.likely_questions.map((x, i) => <li key={i} className="text-[13px] text-muted">• {x}</li>)}</Card>
        <Card title="Likely objections">{r.likely_objections.map((x, i) => <li key={i} className="text-[13px] text-muted">• {x}</li>)}</Card>
      </div>

      <div className="rounded-2xl border border-line bg-surface p-5">
        <p className="text-[11px] uppercase tracking-wider text-faint">Suggested founder narrative</p>
        <p className="mt-1.5 text-[14px] text-ink">{r.suggested_narrative}</p>
        <p className="mt-2 text-[12px] text-faint">Deck: {r.suggested_deck_version}</p>
      </div>

      <div className="rounded-2xl border border-line bg-surface p-5">
        <div className="mb-2 flex items-center justify-between"><p className="text-[11px] uppercase tracking-wider text-faint">Suggested email</p><button onClick={copy} className="text-[13px] text-accent hover:underline">{copied ? "Copied ✓" : "Copy"}</button></div>
        <pre className="whitespace-pre-wrap rounded-lg border border-line bg-canvas p-3 font-sans text-[13px] leading-relaxed text-ink">{r.suggested_email}</pre>
      </div>

      <div className="flex items-center gap-3">
        {approached ? (
          <>
            <span className="text-sm text-good">✓ Added to pipeline · email drafted</span>
            <button onClick={() => router.push("/fundraising")} className="rounded-xl border border-line bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-canvas">Open in Fundraising →</button>
          </>
        ) : (
          <button onClick={approach} disabled={busy} className="rounded-xl bg-ink px-5 py-2.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">{busy ? "Preparing…" : "Approach — add to pipeline & draft email"}</button>
        )}
      </div>
    </div>
  );
}

function Sig({ label }: { label: string }) { return <span className="rounded-full bg-canvas px-2.5 py-1 text-[12px] text-muted">{label}</span>; }
function Card({ title, children }: { title: string; children: React.ReactNode }) { return <div className="rounded-2xl border border-line bg-surface p-4"><p className="mb-1.5 text-[11px] uppercase tracking-wider text-faint">{title}</p><ul className="space-y-1">{children}</ul></div>; }

export default function InvestorsPage() {
  return <RequireCompany><Network /></RequireCompany>;
}
