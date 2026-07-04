"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireCompany } from "@/components/RequireCompany";
import { Timeline } from "@/components/Timeline";
import { useStore } from "@/lib/store";
import { api, ConnectorInfo, Counts, TimelineEvent } from "@/lib/api";

const CATEGORY_LABEL: Record<string, string> = {
  communication: "Communication", documents: "Documents", product: "Product & Engineering",
  crm: "CRM", finance: "Finance", analytics: "Analytics", investors: "Investors",
  marketing: "Marketing & Social",
};
const PIPELINE = ["Connect", "Sync", "Extract", "Entities", "Relationships", "Graph", "Vectors", "Timeline", "Agents"];

function Sources() {
  const companyId = useStore((s) => s.companyId)!;
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [counts, setCounts] = useState<Counts | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [tokenFor, setTokenFor] = useState<string | null>(null);
  const [tokenVal, setTokenVal] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api.connectors(companyId).then((d) => { setConnectors(d.connectors); setCounts(d.counts); }).catch(() => {});
    api.timeline(companyId).then((d) => setTimeline(d.timeline)).catch(() => {});
  }, [companyId]);

  useEffect(() => { refresh(); }, [refresh]);

  // Surface the result of an OAuth round-trip (?connect=success&source=...).
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const c = p.get("connect");
    if (!c) return;
    if (c === "success") setMsg(`Connected ${p.get("source") || "source"} — synced into memory.`);
    else if (c === "failed") setMsg("Sign-in completed but the token exchange failed. Try again or paste a token.");
    else if (c === "error") setMsg("Sign-in was cancelled or returned an error.");
    window.history.replaceState({}, "", "/sources");
    refresh();
  }, [refresh]);

  async function doConnect(id: string, token?: string) {
    const info = connectors.find((c) => c.id === id);
    // One-click OAuth when the provider is configured; else fall back to token.
    if (info?.oauth && !token) {
      setBusy(id); setMsg(null);
      try {
        const start = await api.oauthStart(companyId, id);
        if (start.configured && start.authorize_url) {
          window.location.href = start.authorize_url;
          return;
        }
        setTokenFor(id);
        setMsg(start.message || "One-click sign-in isn't configured — paste a token instead.");
      } catch { setMsg("Couldn't start sign-in."); }
      finally { setBusy(null); }
      return;
    }

    setBusy(id); setMsg(null);
    try {
      const res = await api.connect(companyId, id, token);
      if (res.status === "needs_auth") {
        setTokenFor(id);
        setMsg(res.message || "This source needs an access token.");
      } else {
        setTokenFor(null); setTokenVal("");
        const s = res.summary as Record<string, number> | undefined;
        setMsg(s ? `Synced ${s.records} records · +${s.entities} entities · +${s.relationships} relationships` : "Connected.");
        refresh();
      }
    } catch { setMsg("Connect failed."); }
    finally { setBusy(null); }
  }

  async function doSync(id: string) {
    setBusy(id);
    try { await api.sync(companyId, id); refresh(); } finally { setBusy(null); }
  }
  async function doDisconnect(id: string) { await api.disconnect(companyId, id); refresh(); }

  const byCat: Record<string, ConnectorInfo[]> = {};
  connectors.forEach((c) => (byCat[c.category] ??= []).push(c));

  return (
    <div className="mx-auto max-w-5xl px-5 pb-24 pt-10 sm:px-8">
      <div className="animate-fade-up">
        <h1 className="h-display text-3xl text-ink sm:text-4xl">Knowledge Sources</h1>
        <p className="mt-2 max-w-reading text-[16px] leading-relaxed text-muted">
          Connect a source and it flows through one pipeline into Company Memory. Nothing is fabricated —
          API sources need a real access token; uploads parse your real files.
        </p>
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-faint">
        {PIPELINE.map((p, i) => (
          <span key={p} className="flex items-center gap-2"><span className="uppercase tracking-wider">{p}</span>{i < PIPELINE.length - 1 && <span className="text-line">→</span>}</span>
        ))}
      </div>

      {counts && (
        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
          <Stat n={counts.entities} label="Entities" />
          <Stat n={counts.facts} label="Facts" />
          <Stat n={counts.relationships} label="Relationships" />
          <Stat n={counts.timeline} label="Memory events" />
          <Stat n={counts.chunks} label="Indexed passages" />
        </div>
      )}
      {msg && <div className="mt-4 animate-fade rounded-2xl border border-accent/30 bg-accent/[0.04] p-4 text-[14px] text-ink">{msg}</div>}

      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_360px]">
        <div className="space-y-7">
          {Object.entries(byCat).map(([cat, list]) => (
            <div key={cat}>
              <p className="mb-2 text-[11px] uppercase tracking-wider text-faint">{CATEGORY_LABEL[cat] ?? cat}</p>
              <div className="divide-hair rounded-2xl border border-line bg-surface">
                {list.map((c) => (
                  <div key={c.id}>
                    <div className="flex items-center gap-4 px-4 py-3.5">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="text-[15px] font-medium text-ink">{c.name}</p>
                          {c.connected && <span className="h-1.5 w-1.5 rounded-full bg-good" />}
                          {c.requires_credential && (
                            <span className="rounded-full bg-canvas px-1.5 py-0.5 text-[10px] text-faint">{c.oauth ? "sign-in" : "token"}</span>
                          )}
                        </div>
                        <p className="text-[13px] text-muted">{c.blurb}</p>
                        {c.connected && c.record_count ? <p className="text-[11px] text-faint">{c.record_count} records in memory</p> : null}
                      </div>
                      {c.connected ? (
                        <div className="flex items-center gap-2">
                          <button onClick={() => doSync(c.id)} disabled={busy === c.id} className="rounded-lg border border-line px-3 py-1.5 text-[13px] text-muted hover:text-ink disabled:opacity-50">{busy === c.id ? "Syncing…" : "Re-sync"}</button>
                          <button onClick={() => doDisconnect(c.id)} className="rounded-lg px-2 py-1.5 text-[13px] text-faint hover:text-danger">Disconnect</button>
                        </div>
                      ) : (
                        <button onClick={() => doConnect(c.id)} disabled={busy === c.id} className="rounded-lg bg-ink px-3.5 py-1.5 text-[13px] font-medium text-white hover:opacity-90 disabled:opacity-50">{busy === c.id ? "…" : c.oauth ? `Connect ${c.name}` : "Connect"}</button>
                      )}
                    </div>
                    {tokenFor === c.id && (
                      <div className="flex items-center gap-2 border-t border-line bg-canvas px-4 py-3">
                        <input value={tokenVal} onChange={(e) => setTokenVal(e.target.value)} placeholder={`Paste your ${c.name} access token`} className="flex-1 rounded-lg border border-line bg-surface px-3 py-1.5 text-[13px] outline-none focus:border-accent" />
                        <button onClick={() => doConnect(c.id, tokenVal)} disabled={!tokenVal.trim()} className="rounded-lg bg-ink px-3 py-1.5 text-[13px] font-medium text-white disabled:opacity-40">Authorize & sync</button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div>
          <p className="mb-3 text-[11px] uppercase tracking-wider text-faint">Company memory · live</p>
          <div className="rounded-2xl border border-line bg-surface p-4"><Timeline events={timeline} limit={30} /></div>
        </div>
      </div>
    </div>
  );
}

function Stat({ n, label }: { n: number; label: string }) {
  return <div className="rounded-xl border border-line bg-surface px-4 py-3"><p className="text-2xl font-semibold tracking-tight text-ink">{n}</p><p className="text-[12px] text-faint">{label}</p></div>;
}

export default function SourcesPage() {
  return <RequireCompany><Sources /></RequireCompany>;
}
