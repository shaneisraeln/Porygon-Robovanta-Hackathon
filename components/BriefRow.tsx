"use client";

import { useState } from "react";
import { BriefItem } from "@/lib/api";

const sectionLabel: Record<string, string> = {
  priority: "Priority", risk: "Risk", opportunity: "Opportunity", approval: "Needs you", meeting: "Meeting",
};
const dot: Record<string, string> = { high: "bg-danger", medium: "bg-warn", low: "bg-good" };

export function BriefRow({ item, index }: { item: BriefItem; index: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="animate-fade-up py-5" style={{ animationDelay: `${index * 50}ms` }}>
      <button onClick={() => setOpen((o) => !o)} className="group flex w-full items-start gap-4 text-left">
        <span className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${dot[item.severity]}`} />
        <div className="flex-1">
          <span className="text-[11px] font-medium uppercase tracking-wider text-faint">{sectionLabel[item.section] ?? item.section}</span>
          <h3 className="mt-0.5 text-[17px] font-medium leading-snug text-ink">{item.title}</h3>
          <p className="mt-1 text-[15px] leading-relaxed text-muted">{item.matters}</p>
          <p className="mt-1.5 text-[14px] text-accent"><span className="text-faint">Next ·</span> {item.next}</p>
        </div>
        <span className={`mt-1 text-faint transition-transform ${open ? "rotate-90" : ""}`}>›</span>
      </button>
      {open && (
        <div className="ml-[26px] mt-3 grid gap-2 border-l border-line pl-4 text-[14px] animate-fade">
          <Detail label="Why you're seeing this" text={item.why} />
          <Detail label="What changed" text={item.changed} />
          <Detail label="Why it matters" text={item.matters} />
          {item.source && <Detail label="Source" text={`${item.source.ref}${item.source.excerpt ? ` — "${item.source.excerpt}"` : ""}`} />}
        </div>
      )}
    </div>
  );
}

function Detail({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <span className="text-[12px] uppercase tracking-wide text-faint">{label}</span>
      <p className="text-muted">{text}</p>
    </div>
  );
}
