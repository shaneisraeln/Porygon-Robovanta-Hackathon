"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireCompany } from "@/components/RequireCompany";
import { BriefRow } from "@/components/BriefRow";
import { useStore } from "@/lib/store";
import { api, Brief } from "@/lib/api";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

function MorningBrief() {
  const companyId = useStore((s) => s.companyId)!;
  const [brief, setBrief] = useState<Brief | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.brief(companyId).then(setBrief).catch(() => setError("Couldn't reach the backend. Is the CBO server running on port 8000?"));
  }, [companyId]);

  const today = new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });

  if (error) return <div className="mx-auto max-w-reading px-5 pt-16 text-sm text-danger sm:px-8">{error}</div>;
  if (!brief) return <div className="flex min-h-[60vh] items-center justify-center"><div className="h-2 w-2 animate-breathe rounded-full bg-accent" /></div>;

  const counts = {
    risk: brief.items.filter((i) => i.section === "risk").length,
    opportunity: brief.items.filter((i) => i.section === "opportunity").length,
    approval: brief.items.filter((i) => i.section === "approval").length,
  };

  return (
    <div className="mx-auto max-w-reading px-5 pb-24 pt-10 sm:px-8">
      <div className="animate-fade-up">
        <p className="text-sm text-faint">{today}</p>
        <h1 className="h-display mt-1 text-4xl text-ink sm:text-5xl">Morning Brief</h1>
        <p className="mt-4 text-[17px] leading-relaxed text-muted">
          {greeting()}. Here's what matters at <span className="text-ink">{brief.company.name}</span> today.{" "}
          <span className="text-faint">{brief.summary}</span>
        </p>
        <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <Stat n={counts.approval} label="need you" tone="text-danger" />
          <Stat n={counts.risk} label="risks" tone="text-warn" />
          <Stat n={counts.opportunity} label="opportunities" tone="text-good" />
          <span className="text-faint">Health {brief.metrics.health}% · Raise-ready {brief.metrics.fundraising_readiness}%</span>
        </div>
      </div>

      <div className="mt-8 divide-hair border-t border-line">
        {brief.items.map((item, i) => (
          <BriefRow key={i} item={item} index={i} />
        ))}
      </div>

      <div className="mt-10 flex flex-wrap gap-3 border-t border-line pt-6">
        <Link href="/council" className="rounded-xl bg-ink px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90">Convene the Executive Council</Link>
        <Link href="/fundraising" className="rounded-xl border border-line bg-surface px-4 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-canvas">Open the Fundraising War Room</Link>
        <Link href="/brain" className="rounded-xl border border-line bg-surface px-4 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-canvas">Ask the Company Brain</Link>
      </div>
    </div>
  );
}

function Stat({ n, label, tone }: { n: number; label: string; tone: string }) {
  return <span className={n > 0 ? tone : "text-faint"}><span className="font-semibold">{n}</span> {label}</span>;
}

export default function HomePage() {
  return (
    <RequireCompany>
      <MorningBrief />
    </RequireCompany>
  );
}
