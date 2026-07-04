"use client";

import { Edge, Entity } from "@/lib/api";

const typeColor: Record<string, string> = {
  company: "#16161a", product: "#5b54e8", customer: "#1a8f5c", person: "#b7791f",
  investor: "#d1453b", metric: "#6b6b76", meeting: "#0e7490", task: "#9333ea",
  decision: "#0891b2", goal: "#db2777",
};

interface Props {
  entities: Entity[];
  edges: Edge[];
  selected: string | null;
  onSelect: (id: string | null) => void;
}

export function KnowledgeGraph({ entities, edges, selected, onSelect }: Props) {
  const company = entities.find((e) => e.type === "company");
  const companyId = company?.id ?? "";

  const degree = new Map<string, number>();
  for (const e of edges) {
    degree.set(e.from_id, (degree.get(e.from_id) ?? 0) + 1);
    degree.set(e.to_id, (degree.get(e.to_id) ?? 0) + 1);
  }
  const others = entities
    .filter((e) => e.type !== "company")
    .sort((a, b) => (degree.get(b.id) ?? 0) - (degree.get(a.id) ?? 0))
    .slice(0, 16);

  const cx = 200, cy = 180, r = 128;
  const pos = new Map<string, { x: number; y: number }>();
  pos.set(companyId, { x: cx, y: cy });
  others.forEach((e, i) => {
    const angle = (i / others.length) * Math.PI * 2 - Math.PI / 2;
    pos.set(e.id, { x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r });
  });

  const shownIds = new Set([companyId, ...others.map((e) => e.id)]);
  const interEdges = edges.filter((e) => e.from_id !== companyId && e.to_id !== companyId && shownIds.has(e.from_id) && shownIds.has(e.to_id));

  return (
    <svg viewBox="0 0 400 360" className="w-full">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#ececef" strokeDasharray="2 5" />
      {interEdges.map((e, i) => {
        const a = pos.get(e.from_id);
        const b = pos.get(e.to_id);
        if (!a || !b) return null;
        return <line key={`ie${i}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#eceaf6" strokeWidth={1} />;
      })}
      {others.map((e) => {
        const p = pos.get(e.id)!;
        const angle = Math.atan2(p.y - cy, p.x - cx);
        const color = typeColor[e.type] ?? "#6b6b76";
        const active = selected === e.id;
        return (
          <g key={e.id} className="cursor-pointer" onClick={() => onSelect(active ? null : e.id)}>
            <line x1={cx} y1={cy} x2={p.x} y2={p.y} stroke={active ? color : "#e2e2de"} strokeWidth={active ? 1.5 : 1} />
            <circle cx={p.x} cy={p.y} r={active ? 8 : 6} fill={color} opacity={active ? 1 : 0.85} />
            <text x={p.x + Math.cos(angle) * 12} y={p.y + Math.sin(angle) * 12 + 3} textAnchor={p.x < cx ? "end" : "start"} className="fill-muted" style={{ fontSize: 9.5, fontWeight: active ? 600 : 400 }}>
              {e.name.length > 16 ? e.name.slice(0, 15) + "…" : e.name}
            </text>
          </g>
        );
      })}
      <circle cx={cx} cy={cy} r={27} fill="#16161a" />
      <text x={cx} y={cy + 3} textAnchor="middle" className="fill-white" style={{ fontSize: 10, fontWeight: 600 }}>
        {(company?.name ?? "Company").slice(0, 9)}
      </text>
    </svg>
  );
}
