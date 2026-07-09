"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireCompany } from "@/components/RequireCompany";
import { useStore } from "@/lib/store";
import { competitorApi, Comparison } from "@/lib/api";

function Competitors() {
  const companyId = useStore((s) => s.companyId)!;
  const [data, setData] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { setData(await competitorApi.get(companyId)); setError(null); }
    catch { setError("Couldn't load competitor analysis. Is the backend running?"); }
    finally { setLoading(false); }
  }, [companyId]);

  useEffect(() => { load(); }, [load]);

  async function discover() {
    setDiscovering(true); setNote(null);
    try {
      const d = await competitorApi.discover(companyId);
      setData(d);
      setNote(d.note || (d.discovered ? `Found ${d.discovered} via the web.` : "No new competitors found."));
    } catch { setNote("Web discovery failed. Try again or add competitors manually."); }
    finally { setDiscovering(false); }
  }

  return (
    <div className="mx-auto max-w-4xl px-5 pb-24 pt-10 sm:px-8">
      <div className="animate-fade-up flex items-start justify-between gap-4">
        <div>
          <h1 className="h-display text-3xl text-ink sm:text-4xl">Competitor Analysis</h1>
          <p className="mt-2 max-w-reading text-[16px] leading-relaxed text-muted">
            A feature, pricing and positioning gap table — plus where you win and where you're exposed.
            Grounded only in what you record.
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          <button onClick={discover} disabled={discovering}
            className="rounded-xl border border-line px-4 py-2 text-sm font-medium text-ink transition-colors hover:border-accent disabled:opacity-50">
            {discovering ? "Searching…" : "Discover from web"}
          </button>
          <button onClick={() => setShowForm((s) => !s)}
            className="rounded-xl bg-ink px-4 py-2 text-sm font-medium text-white hover:opacity-90">
            {showForm ? "Cancel" : "Add competitor"}
          </button>
        </div>
      </div>

      {note && <div className="mt-4 animate-fade rounded-2xl border border-accent/30 bg-accent/[0.04] p-4 text-[14px] text-ink">{note}</div>}

      {showForm && <CompetitorForm companyId={companyId} onDone={(c) => { setData(c); setShowForm(false); }} />}

      {error && <p className="mt-6 text-sm text-danger">{error}</p>}
      {loading && (
        <div className="mt-8 flex items-center gap-3 text-sm text-muted animate-fade">
          <span className="h-2 w-2 animate-breathe rounded-full bg-accent" />Loading…
        </div>
      )}

      {data && data.insufficient && !loading && (
        <p className="mt-8 rounded-2xl border border-line bg-surface p-5 text-[14px] leading-relaxed text-muted">
          {data.note}
        </p>
      )}

      {data && !data.insufficient && (
        <div className="mt-8 space-y-8">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-good/30 bg-good/5 p-5">
              <span className="text-[11px] uppercase tracking-wider text-good">Where you win</span>
              <ul className="mt-2 space-y-1.5">
                {data.where_you_win.length ? data.where_you_win.map((w, i) => (
                  <li key={i} className="text-[14px] text-ink">+ {w}</li>
                )) : <li className="text-[13px] text-faint">Add more detail to surface advantages.</li>}
              </ul>
            </div>
            <div className="rounded-2xl border border-danger/30 bg-danger/5 p-5">
              <span className="text-[11px] uppercase tracking-wider text-danger">Where you're exposed</span>
              <ul className="mt-2 space-y-1.5">
                {data.where_youre_exposed.length ? data.where_youre_exposed.map((e, i) => (
                  <li key={i} className="text-[14px] text-ink">− {e}</li>
                )) : <li className="text-[13px] text-faint">No exposures flagged from current data.</li>}
              </ul>
            </div>
          </div>

          <div>
            <p className="mb-3 text-[11px] uppercase tracking-wider text-faint">Competitors</p>
            <div className="flex flex-wrap gap-2">
              {data.competitors.map((c) => (
                c.url ? (
                  <a key={c.name} href={c.url.startsWith("http") ? c.url : `https://${c.url}`} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 rounded-full border border-line px-3 py-1 text-[13px] text-ink transition-colors hover:border-accent">
                    {c.name} <span className="text-accent">↗</span>
                  </a>
                ) : (
                  <span key={c.name} className="rounded-full border border-line px-3 py-1 text-[13px] text-muted">{c.name}</span>
                )
              ))}
            </div>
          </div>

          <div>
            <p className="mb-3 text-[11px] uppercase tracking-wider text-faint">Gap table</p>
            <div className="overflow-x-auto rounded-2xl border border-line">
              <table className="w-full border-collapse text-[13px]">
                <thead>
                  <tr className="border-b border-line bg-surface">
                    <th className="px-4 py-2.5 text-left font-medium text-faint">Dimension</th>
                    <th className="px-4 py-2.5 text-left font-medium text-ink">{data.us.name}</th>
                    {data.competitors.map((c) => (
                      <th key={c.name} className="px-4 py-2.5 text-left font-medium text-muted">
                        {c.url ? (
                          <a href={c.url.startsWith("http") ? c.url : `https://${c.url}`} target="_blank" rel="noopener noreferrer" className="text-ink hover:text-accent hover:underline">{c.name} ↗</a>
                        ) : c.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.table.map((row) => (
                    <tr key={row.dimension} className="border-b border-line last:border-0">
                      <td className="px-4 py-2.5 text-faint">{row.dimension}</td>
                      <td className="px-4 py-2.5 text-ink">{row.us}</td>
                      {row.competitors.map((c, i) => (
                        <td key={i} className="px-4 py-2.5 text-muted">{c.value}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CompetitorForm({ companyId, onDone }: { companyId: string; onDone: (c: Comparison) => void }) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [features, setFeatures] = useState("");
  const [pricing, setPricing] = useState("");
  const [positioning, setPositioning] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    try {
      const c = await competitorApi.add(companyId, {
        name: name.trim(), url: url.trim(), features: features.trim(), pricing: pricing.trim(),
        positioning: positioning.trim(), notes: notes.trim(),
      });
      onDone(c);
    } finally { setBusy(false); }
  }

  const field = "rounded-xl border border-line bg-canvas px-3 py-2 text-[14px] outline-none placeholder:text-faint focus:border-accent";

  return (
    <form onSubmit={submit} className="mt-5 grid gap-2.5 rounded-2xl border border-line bg-surface p-5 sm:grid-cols-2">
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Competitor name" className={field} />
      <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="Website (e.g. competitor.com)" className={field} />
      <input value={pricing} onChange={(e) => setPricing(e.target.value)} placeholder="Pricing (e.g. $99/mo)" className={field} />
      <input value={features} onChange={(e) => setFeatures(e.target.value)} placeholder="Key features" className={`${field} sm:col-span-2`} />
      <input value={positioning} onChange={(e) => setPositioning(e.target.value)} placeholder="Positioning (how they sell)" className={`${field} sm:col-span-2`} />
      <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Notes (strengths/weaknesses you've observed)" rows={2} className={`${field} sm:col-span-2`} />
      <div className="sm:col-span-2">
        <button type="submit" disabled={busy || !name.trim()}
          className="rounded-xl bg-ink px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">
          {busy ? "Adding…" : "Save competitor"}
        </button>
      </div>
    </form>
  );
}

export default function CompetitorsPage() {
  return <RequireCompany><Competitors /></RequireCompany>;
}
