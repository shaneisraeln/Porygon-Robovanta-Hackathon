"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { RequireCompany } from "@/components/RequireCompany";
import { useStore } from "@/lib/store";
import { dashboardApi, Dashboard as DashboardData, DashboardTile, RecTile, RiskAlert } from "@/lib/api";

const STATUS_RING: Record<string, string> = {
  ok: "border-line",
  warn: "border-warn/40",
  insufficient: "border-line border-dashed",
};
const STATUS_TEXT: Record<string, string> = {
  ok: "text-ink",
  warn: "text-warn",
  insufficient: "text-faint",
};
const REC_PILL: Record<string, string> = {
  recommended: "bg-line/60 text-muted",
  in_progress: "bg-warn/10 text-warn",
  completed: "bg-accent/10 text-accent",
  measured: "bg-good/10 text-good",
};
const SEV_DOT: Record<string, string> = { high: "#d1453b", medium: "#b7791f", low: "#6b6b76" };

function Dashboard() {
  const companyId = useStore((s) => s.companyId)!;
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { setData(await dashboardApi.get(companyId)); setError(null); }
    catch { setError("Couldn't load the dashboard. Is the backend running?"); }
    finally { setLoading(false); }
  }, [companyId]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="mx-auto max-w-5xl px-5 pb-24 pt-10 sm:px-8">
      <div className="animate-fade-up">
        <h1 className="h-display text-3xl text-ink sm:text-4xl">Business Intelligence</h1>
        <p className="mt-2 max-w-reading text-[16px] leading-relaxed text-muted">
          The daily read a CEO checks. Every tile is computed from your Company Memory — where data is
          missing, it says so rather than guessing.
        </p>
      </div>

      {error && <p className="mt-6 text-sm text-danger">{error}</p>}
      {loading && (
        <div className="mt-8 flex items-center gap-3 text-sm text-muted animate-fade">
          <span className="h-2 w-2 animate-breathe rounded-full bg-accent" />
          Aggregating your metrics…
        </div>
      )}

      {data && (
        <>
          <div className="mt-7 animate-fade-up rounded-2xl border border-ink/15 bg-surface p-5">
            <span className="text-[11px] uppercase tracking-wider text-accent">Executive Summary</span>
            <p className="mt-2 text-[16px] leading-relaxed text-ink">{data.executive_summary}</p>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.tiles.map((t, i) => <Tile key={t.key} tile={t} index={i} />)}
          </div>
        </>
      )}
    </div>
  );
}

function Tile({ tile, index }: { tile: DashboardTile; index: number }) {
  const isList = tile.kind === "list";
  const display = tile.display ?? (tile.value !== null ? Math.round(tile.value as number).toString() : "—");

  return (
    <div
      className={`animate-fade-up rounded-2xl border bg-surface p-5 ${STATUS_RING[tile.status]} ${isList ? "sm:col-span-2 lg:col-span-1" : ""}`}
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-wider text-faint">{tile.label}</span>
        {tile.status === "warn" && <span className="h-1.5 w-1.5 rounded-full bg-warn" />}
      </div>

      {!isList && (
        <div className="mt-1.5 flex items-baseline gap-2">
          <span className={`h-display text-4xl ${STATUS_TEXT[tile.status]}`}>{display}</span>
          {tile.kind === "score" && tile.value !== null && <span className="text-sm text-faint">/100</span>}
        </div>
      )}

      {isList && tile.key === "ai_recommendations" && (
        <div className="mt-2 space-y-2">
          {(tile.items as RecTile[])?.length ? (
            (tile.items as RecTile[]).map((r) => (
              <Link key={r.recommendation_id} href="/growth" className="block rounded-xl border border-line p-2.5 transition-colors hover:border-accent">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[13px] text-ink">{r.title}</span>
                  <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${REC_PILL[r.status]}`}>{r.status.replace("_", " ")}</span>
                </div>
                <span className="mt-1 block text-[11px] text-faint">{r.outcome_badge}</span>
              </Link>
            ))
          ) : (
            <p className="text-[13px] text-faint">{tile.detail}</p>
          )}
        </div>
      )}

      {isList && tile.key === "risk_alerts" && (
        <div className="mt-2 space-y-2">
          {(tile.items as RiskAlert[]).map((a, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: SEV_DOT[a.severity] }} />
              <div>
                <p className="text-[13px] text-ink">{a.title}</p>
                <p className="text-[11px] text-muted">{a.detail}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {!isList && <p className="mt-3 text-[12px] leading-relaxed text-muted">{tile.detail}</p>}
    </div>
  );
}

export default function DashboardPage() {
  return <RequireCompany><Dashboard /></RequireCompany>;
}
