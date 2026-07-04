"use client";

import { useState } from "react";
import { RequireCompany } from "@/components/RequireCompany";
import { useStore } from "@/lib/store";
import { api, CouncilResult, Verdict } from "@/lib/api";

const SAMPLES = ["Should we raise now?", "Should we hire a senior engineer?", "Should we pivot to enterprise?"];
const agentDot: Record<string, string> = {
  strategy: "#5b54e8", finance: "#1a8f5c", fundraising: "#d1453b", market: "#b7791f",
  execution: "#0e7490", operations: "#7c3aed", customer: "#be185d", risk: "#16161a",
  growth: "#0891b2",
};
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

function Council() {
  const companyId = useStore((s) => s.companyId)!;
  const [question, setQuestion] = useState(SAMPLES[0]);
  const [result, setResult] = useState<CouncilResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function convene(q: string) {
    const query = q.trim();
    if (!query) return;
    setLoading(true); setError(null); setResult(null);
    try {
      await new Promise((r) => setTimeout(r, 400));
      setResult(await api.council(companyId, query));
    } catch { setError("The council could not convene. Is the backend running?"); }
    finally { setLoading(false); }
  }

  return (
    <div className="mx-auto max-w-4xl px-5 pb-24 pt-10 sm:px-8">
      <div className="animate-fade-up">
        <h1 className="h-display text-3xl text-ink sm:text-4xl">Executive Council</h1>
        <p className="mt-2 max-w-reading text-[16px] leading-relaxed text-muted">
          The Council executes: a planner selects agents, each reasons from memory, they debate, then CBO
          synthesizes one recommendation under governance.
        </p>
      </div>

      <div className="mt-7 animate-fade-up">
        <form onSubmit={(e) => { e.preventDefault(); convene(question); }} className="flex items-center gap-2 rounded-2xl border border-line bg-surface px-2 py-1.5 shadow-sm focus-within:border-accent">
          <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask a strategic question…" className="flex-1 bg-transparent px-3 py-2 text-[15px] outline-none placeholder:text-faint" />
          <button type="submit" disabled={loading} className="rounded-xl bg-ink px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">{loading ? "Convening…" : "Convene"}</button>
        </form>
        <div className="mt-2.5 flex flex-wrap gap-2">
          {SAMPLES.map((s) => <button key={s} onClick={() => { setQuestion(s); convene(s); }} className="rounded-full border border-line px-3 py-1 text-[12px] text-muted transition-colors hover:border-accent hover:text-ink">{s}</button>)}
        </div>
      </div>

      {error && <p className="mt-6 text-sm text-danger">{error}</p>}
      {loading && <div className="mt-8 flex items-center gap-3 text-sm text-muted animate-fade"><span className="h-2 w-2 animate-breathe rounded-full bg-accent" />Planner is selecting agents and gathering evidence…</div>}

      {result && (
        <div className="mt-8 space-y-8">
          {/* plan */}
          <div className="animate-fade text-[13px] text-muted">
            <span className="text-faint">Plan · </span>{result.plan.rationale}
          </div>

          {/* synthesis */}
          <div className="animate-fade-up rounded-2xl border border-ink/15 bg-surface p-6">
            <div className="flex items-center justify-between">
              <span className="text-[11px] uppercase tracking-wider text-accent">CBO's recommendation</span>
              <span className="text-[11px] text-faint">{result.synthesis.confidence}% council confidence</span>
            </div>
            <h2 className="h-display mt-2 text-2xl text-ink">{result.synthesis.headline}</h2>
            <p className="mt-3 text-[16px] leading-relaxed text-muted">{result.synthesis.rationale}</p>
            <div className="mt-5 grid gap-5 sm:grid-cols-2">
              <div>
                <p className="mb-1.5 text-[11px] uppercase tracking-wider text-faint">Next actions</p>
                <ul className="space-y-1.5">{result.synthesis.next_actions.map((a, i) => <li key={i} className="text-[14px] text-ink">→ {a}</li>)}</ul>
              </div>
              {result.synthesis.dissent.length > 0 && (
                <div>
                  <p className="mb-1.5 text-[11px] uppercase tracking-wider text-faint">Where the council is cautious</p>
                  <ul className="space-y-1.5">{result.synthesis.dissent.map((d, i) => <li key={i} className="text-[14px] text-warn">• {cap(d)}</li>)}</ul>
                </div>
              )}
            </div>
            <div className="mt-5 flex flex-wrap gap-2 border-t border-line pt-4">
              {result.governance.checks.map((c, i) => (
                <span key={i} className={`rounded-full px-2.5 py-1 text-[11px] ${c.status === "pass" ? "bg-good/10 text-good" : "bg-warn/10 text-warn"}`}>{c.check}: {c.status}</span>
              ))}
            </div>
          </div>

          {/* debate */}
          <div>
            <p className="mb-2 text-[11px] uppercase tracking-wider text-faint">Debate</p>
            <div className="space-y-2">
              {result.debate.map((d, i) => (
                <div key={i} className="flex items-start gap-2 text-[14px]">
                  <span className="rounded-full px-2 py-0.5 text-[11px] font-medium text-white" style={{ background: agentDot[d.agent] ?? "#6b6b76" }}>{cap(d.agent)}</span>
                  <span className="text-muted">{d.point}</span>
                </div>
              ))}
            </div>
          </div>

          {/* verdicts */}
          <div>
            <p className="mb-3 text-[11px] uppercase tracking-wider text-faint">The council ({result.verdicts.length} agents)</p>
            <div className="grid gap-3 sm:grid-cols-2">
              {result.verdicts.map((v, i) => <AgentCard key={v.agent} v={v} index={i} />)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AgentCard({ v, index }: { v: Verdict; index: number }) {
  return (
    <div className="animate-fade-up rounded-2xl border border-line bg-surface p-4" style={{ animationDelay: `${index * 50}ms` }}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: agentDot[v.agent] }} />
          <h3 className="text-sm font-semibold text-ink">{cap(v.agent)}</h3>
        </div>
        <span className="text-[11px] text-faint">{v.confidence}%</span>
      </div>
      <p className="mt-1.5 text-[14px] font-medium text-ink">{v.stance}</p>
      {v.framework && <p className="mt-0.5 text-[11px] text-faint">Framework: {v.framework}</p>}
      <p className="mt-2 text-[13px] leading-relaxed text-muted"><span className="text-faint">Evidence: </span>{v.evidence.join(" · ")}</p>
      <div className="mt-2.5 grid grid-cols-2 gap-3 text-[12px]">
        <div><p className="text-good">Pros</p>{v.pros.map((p, i) => <p key={i} className="text-muted">+ {p}</p>)}</div>
        <div><p className="text-danger">Cons</p>{v.cons.map((c, i) => <p key={i} className="text-muted">− {c}</p>)}</div>
      </div>
      <p className="mt-2.5 border-t border-line pt-2.5 text-[13px] text-ink"><span className="text-faint">Rec: </span>{v.recommendation}</p>
    </div>
  );
}

export default function CouncilPage() {
  return <RequireCompany><Council /></RequireCompany>;
}
