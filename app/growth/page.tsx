"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireCompany } from "@/components/RequireCompany";
import { useStore } from "@/lib/store";
import { growthApi, GrowthResult, Recommendation, RecStatus } from "@/lib/api";

const STATUS_FLOW: RecStatus[] = ["recommended", "in_progress", "completed", "measured"];
const STATUS_STYLE: Record<RecStatus, string> = {
  recommended: "bg-line/60 text-muted",
  in_progress: "bg-warn/10 text-warn",
  completed: "bg-accent/10 text-accent",
  measured: "bg-good/10 text-good",
};
const STATUS_LABEL: Record<RecStatus, string> = {
  recommended: "Recommended",
  in_progress: "In progress",
  completed: "Completed",
  measured: "Measured",
};
const CATEGORY_DOT: Record<string, string> = {
  retention: "#be185d", sales: "#1a8f5c", marketing: "#b7791f", growth: "#5b54e8",
};
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

function Growth() {
  const companyId = useStore((s) => s.companyId)!;
  const [data, setData] = useState<GrowthResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await growthApi.recommendations(companyId));
      setError(null);
    } catch {
      setError("Couldn't reach the Growth Agent. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { load(); }, [load]);

  const lead = data?.lead_score;

  return (
    <div className="mx-auto max-w-4xl px-5 pb-24 pt-10 sm:px-8">
      <div className="animate-fade-up">
        <h1 className="h-display text-3xl text-ink sm:text-4xl">Growth Agent</h1>
        <p className="mt-2 max-w-reading text-[16px] leading-relaxed text-muted">
          Ranked campaign and sales plays, grounded strictly in your memory. Track each one from
          recommended through measured — results feed back into future strategy.
        </p>
      </div>

      {/* Lead Score */}
      <div className="mt-7 animate-fade-up rounded-2xl border border-line bg-surface p-5">
        <div className="flex items-center justify-between">
          <span className="text-[11px] uppercase tracking-wider text-faint">Lead Score</span>
          <span className="text-[11px] text-faint">
            {lead && lead.inputs_used.length ? `${lead.inputs_used.length} input(s)` : "no inputs"}
          </span>
        </div>
        <div className="mt-1.5 flex items-end gap-3">
          <span className="h-display text-4xl text-ink">
            {lead && lead.lead_score !== null ? Math.round(lead.lead_score) : "—"}
          </span>
          {lead && lead.lead_score === null && (
            <span className="pb-1.5 text-[13px] text-muted">Insufficient data — add lead facts or connect HubSpot.</span>
          )}
        </div>
        {lead && lead.inputs_used.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {lead.inputs_used.map((i) => (
              <span key={i} className="rounded-full border border-line px-2.5 py-1 text-[11px] text-muted">{i}</span>
            ))}
          </div>
        )}
      </div>

      {error && <p className="mt-6 text-sm text-danger">{error}</p>}
      {loading && (
        <div className="mt-8 flex items-center gap-3 text-sm text-muted animate-fade">
          <span className="h-2 w-2 animate-breathe rounded-full bg-accent" />
          Reasoning over your memory…
        </div>
      )}

      {data && !loading && data.recommendations.length === 0 && (
        <p className="mt-8 rounded-2xl border border-line bg-surface p-5 text-[14px] leading-relaxed text-muted">
          {data.note}
        </p>
      )}

      {data && data.recommendations.length > 0 && (
        <div className="mt-8 space-y-4">
          <p className="text-[11px] uppercase tracking-wider text-faint">
            Recommendations ({data.recommendations.length})
          </p>
          {data.recommendations.map((r, i) => (
            <RecommendationCard key={r.recommendation_id} rec={r} index={i} companyId={companyId} onChange={load} />
          ))}
        </div>
      )}
    </div>
  );
}

function RecommendationCard({ rec, index, companyId, onChange }: {
  rec: Recommendation; index: number; companyId: string; onChange: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const next = STATUS_FLOW[STATUS_FLOW.indexOf(rec.status) + 1];
  const canAdvance = next && next !== "measured";

  async function advance() {
    if (!next) return;
    setBusy(true);
    try { await growthApi.setStatus(companyId, rec.recommendation_id, next); onChange(); }
    finally { setBusy(false); }
  }

  return (
    <div className="animate-fade-up rounded-2xl border border-line bg-surface p-5" style={{ animationDelay: `${index * 50}ms` }}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: CATEGORY_DOT[rec.category] ?? "#6b6b76" }} />
          <h3 className="text-[15px] font-semibold text-ink">{rec.title}</h3>
        </div>
        <span className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-medium ${STATUS_STYLE[rec.status]}`}>
          {STATUS_LABEL[rec.status]}
        </span>
      </div>

      <p className="mt-2 text-[14px] leading-relaxed text-muted">{rec.detail}</p>
      <p className="mt-2 text-[13px] leading-relaxed text-faint">
        <span className="text-muted">Why: </span>{rec.rationale}
      </p>

      {rec.evidence.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {rec.evidence.map((e, i) => (
            <span key={i} className="rounded-full border border-line px-2.5 py-1 text-[11px] text-muted">{e}</span>
          ))}
        </div>
      )}

      {(rec.expected_impact || rec.effort || rec.timeframe) && (
        <div className="mt-3 flex flex-wrap gap-4 text-[12px]">
          {rec.expected_impact && <span className="text-muted"><span className="text-faint">Impact: </span>{rec.expected_impact}</span>}
          {rec.effort && <span className="text-muted"><span className="text-faint">Effort: </span>{rec.effort}</span>}
          {rec.timeframe && <span className="text-muted"><span className="text-faint">Timeframe: </span>{rec.timeframe}</span>}
        </div>
      )}

      {rec.playbook.length > 0 && (
        <div className="mt-3">
          <p className="mb-1.5 text-[11px] uppercase tracking-wider text-faint">How to run it</p>
          <ol className="space-y-1">
            {rec.playbook.map((step, i) => (
              <li key={i} className="flex gap-2 text-[13px] text-ink">
                <span className="grid h-4 w-4 shrink-0 place-items-center rounded-full bg-accent/10 text-[10px] font-medium text-accent">{i + 1}</span>
                <span className="text-muted">{step}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {rec.outcome && (
        <div className="mt-3 rounded-xl border border-good/30 bg-good/5 p-3 text-[13px]">
          <span className="text-[11px] uppercase tracking-wider text-good">Outcome logged</span>
          <p className="mt-1 text-ink">
            {rec.outcome.outcome_metric}: {rec.outcome.baseline_value || "—"} → {rec.outcome.outcome_value}
            {rec.outcome.date_range ? ` · ${rec.outcome.date_range}` : ""}
          </p>
          {rec.outcome.result_note && <p className="mt-1 text-muted">{rec.outcome.result_note}</p>}
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-3">
        <span className="text-[11px] text-faint">{rec.confidence}% confidence · {cap(rec.category)}</span>
        <div className="ml-auto flex gap-2">
          {canAdvance && (
            <button onClick={advance} disabled={busy}
              className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-muted transition-colors hover:border-accent hover:text-ink disabled:opacity-50">
              Mark {STATUS_LABEL[next].toLowerCase()}
            </button>
          )}
          {rec.status !== "measured" && (
            <button onClick={() => setShowForm((s) => !s)}
              className="rounded-lg bg-ink px-3 py-1.5 text-[12px] font-medium text-white hover:opacity-90">
              {showForm ? "Cancel" : "Log outcome"}
            </button>
          )}
        </div>
      </div>

      {showForm && (
        <OutcomeForm companyId={companyId} rid={rec.recommendation_id}
          onDone={() => { setShowForm(false); onChange(); }} />
      )}
    </div>
  );
}

function OutcomeForm({ companyId, rid, onDone }: { companyId: string; rid: string; onDone: () => void }) {
  const [metric, setMetric] = useState("");
  const [value, setValue] = useState("");
  const [baseline, setBaseline] = useState("");
  const [range, setRange] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!metric.trim() || !value.trim()) return;
    setBusy(true);
    try {
      await growthApi.logOutcome(companyId, rid, {
        outcome_metric: metric.trim(), outcome_value: value.trim(),
        baseline_value: baseline.trim(), date_range: range.trim(), result_note: note.trim(),
      });
      onDone();
    } finally { setBusy(false); }
  }

  const field = "rounded-xl border border-line bg-canvas px-3 py-2 text-[14px] outline-none placeholder:text-faint focus:border-accent";

  return (
    <form onSubmit={submit} className="mt-3 grid gap-2.5 rounded-xl border border-line bg-canvas/50 p-4 sm:grid-cols-2">
      <input value={metric} onChange={(e) => setMetric(e.target.value)} placeholder="Metric (e.g. churn)" className={field} />
      <input value={value} onChange={(e) => setValue(e.target.value)} placeholder="Result value (e.g. 6%)" className={field} />
      <input value={baseline} onChange={(e) => setBaseline(e.target.value)} placeholder="Baseline (e.g. 8%)" className={field} />
      <input value={range} onChange={(e) => setRange(e.target.value)} placeholder="Date range (e.g. Jun–Jul)" className={field} />
      <textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Result note (optional)" rows={2} className={`${field} sm:col-span-2`} />
      <div className="sm:col-span-2">
        <button type="submit" disabled={busy || !metric.trim() || !value.trim()}
          className="rounded-xl bg-ink px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">
          {busy ? "Logging…" : "Save outcome"}
        </button>
      </div>
    </form>
  );
}

export default function GrowthPage() {
  return <RequireCompany><Growth /></RequireCompany>;
}
