"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireCompany } from "@/components/RequireCompany";
import { KnowledgeGraph } from "@/components/KnowledgeGraph";
import { Timeline } from "@/components/Timeline";
import { useStore } from "@/lib/store";
import { api, AskResult, Edge, Entity, Fact, TimelineEvent } from "@/lib/api";

const SAMPLES = ["What's our runway?", "How are we growing?", "Who are our investors?", "What do we charge?"];

function Brain() {
  const companyId = useStore((s) => s.companyId)!;
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<AskResult | null>(null);
  const [asking, setAsking] = useState(false);
  const [graph, setGraph] = useState<{ entities: Entity[]; edges: Edge[] }>({ entities: [], edges: [] });
  const [facts, setFacts] = useState<Fact[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [entityFacts, setEntityFacts] = useState<Fact[] | null>(null);
  const [docText, setDocText] = useState("");
  const [note, setNote] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api.graph(companyId).then(setGraph).catch(() => {});
    api.facts(companyId).then((d) => setFacts(d.facts)).catch(() => {});
    api.timeline(companyId).then((d) => setTimeline(d.timeline)).catch(() => {});
  }, [companyId]);

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    if (selected) api.entityFacts(companyId, selected).then((d) => setEntityFacts(d.facts)).catch(() => setEntityFacts([]));
    else setEntityFacts(null);
  }, [selected, companyId]);

  async function run(q: string) {
    const query = q.trim();
    if (!query) return;
    setAsking(true);
    try { setResult(await api.ask(companyId, query)); } finally { setAsking(false); }
  }

  async function addDoc() {
    if (!docText.trim()) return;
    const res = await api.ingestText(companyId, "note.txt", docText);
    setDocText("");
    setNote(`Indexed ${res.summary.facts} facts.`);
    setTimeout(() => setNote(null), 4000);
    refresh();
  }

  const selectedEntity = graph.entities.find((e) => e.id === selected);
  const visibleFacts = selectedEntity ? entityFacts ?? [] : facts;

  return (
    <div className="mx-auto max-w-5xl px-5 pb-24 pt-10 sm:px-8">
      <div className="animate-fade-up">
        <h1 className="h-display text-3xl text-ink sm:text-4xl">Company Brain</h1>
        <p className="mt-2 max-w-reading text-[16px] leading-relaxed text-muted">
          Everything you've told me and every source I've read becomes connected memory. Ask anything —
          answers come only from memory, with sources. If I don't know, I'll say so.
        </p>
      </div>

      <div className="mt-7 animate-fade-up">
        <form onSubmit={(e) => { e.preventDefault(); run(query); }} className="flex items-center gap-2 rounded-2xl border border-line bg-surface px-2 py-1.5 shadow-sm focus-within:border-accent">
          <span className="pl-3 text-faint">⌕</span>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ask your company anything…" className="flex-1 bg-transparent px-2 py-2 text-[15px] outline-none placeholder:text-faint" />
          <button type="submit" disabled={asking} className="rounded-xl bg-ink px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">{asking ? "…" : "Ask"}</button>
        </form>
        <div className="mt-2.5 flex flex-wrap gap-2">
          {SAMPLES.map((s) => (
            <button key={s} onClick={() => { setQuery(s); run(s); }} className="rounded-full border border-line px-3 py-1 text-[12px] text-muted transition-colors hover:border-accent hover:text-ink">{s}</button>
          ))}
        </div>

        {result && (
          <div className="mt-5 animate-fade rounded-2xl border border-line bg-surface p-5">
            <div className="flex items-start justify-between gap-3">
              <p className="text-[16px] leading-relaxed text-ink">{result.answer}</p>
              <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] ${result.confidence >= 0.6 ? "bg-good/10 text-good" : result.confidence > 0 ? "bg-warn/10 text-warn" : "bg-line text-faint"}`}>
                {Math.round(result.confidence * 100)}% conf
              </span>
            </div>
            {result.sources.length > 0 && (
              <div className="mt-4 border-t border-line pt-3">
                <p className="mb-2 text-[11px] uppercase tracking-wider text-faint">Sources</p>
                <div className="space-y-1.5">
                  {result.sources.map((c, i) => (
                    <p key={i} className="text-[13px] text-muted"><span className="font-medium text-ink">{c.source}</span><span className="text-faint"> — {c.excerpt.slice(0, 120)}{c.excerpt.length > 120 ? "…" : ""}</span></p>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="mt-10 grid gap-8 lg:grid-cols-[400px_1fr]">
        <div>
          <p className="mb-2 text-[11px] uppercase tracking-wider text-faint">Knowledge graph</p>
          <div className="rounded-2xl border border-line bg-surface p-2">
            <KnowledgeGraph entities={graph.entities} edges={graph.edges} selected={selected} onSelect={setSelected} />
          </div>
          <p className="mt-2 text-center text-xs text-faint">{selectedEntity ? `Showing facts for ${selectedEntity.name}` : "Tap a node to trace its facts"}</p>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-[11px] uppercase tracking-wider text-faint">Memory {selectedEntity ? `· ${selectedEntity.name}` : `· ${facts.length} facts`}</p>
            {selectedEntity && <button onClick={() => setSelected(null)} className="text-xs text-accent hover:underline">Show all</button>}
          </div>
          <div className="divide-hair rounded-2xl border border-line bg-surface">
            {visibleFacts.length === 0 && <p className="p-5 text-sm text-faint">No facts here yet.</p>}
            {visibleFacts.map((f) => (
              <div key={f.id} className="row-hover px-4 py-3">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-[15px] text-ink"><span className="text-muted">{f.label}:</span> {f.value}</span>
                  <span className="shrink-0 text-[11px] text-faint">v{f.version} · {Math.round(f.confidence * 100)}%</span>
                </div>
                <p className="mt-0.5 text-[12px] text-faint">↳ {f.source_ref} · owner {f.owner}{f.evidence ? ` — "${f.evidence.slice(0, 70)}${f.evidence.length > 70 ? "…" : ""}"` : ""}</p>
              </div>
            ))}
          </div>

          <div className="mt-4 rounded-2xl border border-line bg-surface p-3">
            <textarea value={docText} onChange={(e) => setDocText(e.target.value)} placeholder="Feed the brain — paste notes, metrics, an update…" rows={3} className="w-full resize-none bg-transparent px-2 py-1 text-[14px] outline-none placeholder:text-faint" />
            <div className="flex items-center justify-end border-t border-line pt-2.5">
              <button onClick={addDoc} disabled={!docText.trim()} className="rounded-lg bg-ink px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-40">Extract & index</button>
            </div>
            {note && <p className="mt-2 text-xs text-good">{note}</p>}
          </div>
        </div>
      </div>

      {timeline.length > 0 && (
        <div className="mt-10">
          <p className="mb-3 text-[11px] uppercase tracking-wider text-faint">Company memory · live</p>
          <div className="rounded-2xl border border-line bg-surface p-5"><Timeline events={timeline} limit={30} /></div>
        </div>
      )}
    </div>
  );
}

export default function BrainPage() {
  return <RequireCompany><Brain /></RequireCompany>;
}
