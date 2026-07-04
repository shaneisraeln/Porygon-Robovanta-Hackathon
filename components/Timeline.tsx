"use client";

import { TimelineEvent } from "@/lib/api";

const kindColor: Record<string, string> = {
  Email: "#5b54e8", Meeting: "#0e7490", "Meeting debrief": "#0e7490", Commit: "#1a8f5c",
  Issue: "#d1453b", Payment: "#1a8f5c", Message: "#b7791f", CRM: "#be185d", Analytics: "#7c3aed", Document: "#6b6b76",
};

function ago(atSeconds: number): string {
  const at = atSeconds < 1e12 ? atSeconds * 1000 : atSeconds;
  const ms = Math.max(0, Date.now() - at);
  const m = Math.floor(ms / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export function Timeline({ events, limit = 40 }: { events: TimelineEvent[]; limit?: number }) {
  const shown = events.slice(0, limit);
  if (shown.length === 0) {
    return <p className="text-sm text-faint">No memory yet. Connect a source to start the feed.</p>;
  }
  return (
    <ol className="relative">
      {shown.map((e) => (
        <li key={e.id} className="relative flex gap-3 pb-5 last:pb-0">
          <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: kindColor[e.kind] ?? "#9aa1ad" }} />
          <div className="-mt-0.5 flex-1">
            <div className="flex items-baseline justify-between gap-3">
              <p className="text-[15px] font-medium text-ink">{e.title}</p>
              <span className="shrink-0 text-[11px] text-faint">{ago(e.at)}</span>
            </div>
            <p className="text-[13px] text-muted">{e.why}</p>
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              <span className="rounded-full bg-canvas px-2 py-0.5 text-[10px] uppercase tracking-wide text-faint">{e.kind}</span>
              {e.who.slice(0, 3).map((w) => (
                <span key={w} className="rounded-full bg-canvas px-2 py-0.5 text-[11px] text-muted">{w}</span>
              ))}
              {e.agents.map((a) => (
                <span key={a} className="rounded-full bg-accent/10 px-2 py-0.5 text-[11px] text-accent">→ {a}</span>
              ))}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
