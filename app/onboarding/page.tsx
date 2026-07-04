"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import { api, interviewApi, InterviewQuestion, Profile } from "@/lib/api";

type Turn = { role: "cbo" | "founder"; text: string; captured?: string[]; context?: string };

export default function Onboarding() {
  const router = useRouter();
  const { companyId, hydrated, setCompany } = useStore();
  const [cid, setCid] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [phase, setPhase] = useState<"name" | "interview" | "done">("name");
  const [turns, setTurns] = useState<Turn[]>([
    { role: "cbo", text: "I'm CBO — I'll run the business with you. Let's start simple. What's your company called?" },
  ]);
  const [question, setQuestion] = useState<InterviewQuestion | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { if (hydrated && companyId) router.replace("/"); }, [hydrated, companyId, router]);
  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }); }, [turns, question]);
  useEffect(() => { inputRef.current?.focus(); }, [phase, question]);

  const say = (t: Turn) => setTurns((p) => [...p, t]);

  function showQuestion(q: InterviewQuestion | null, done: boolean) {
    if (done || !q) {
      setQuestion(null);
      setTimeout(() => say({ role: "cbo", text: "That's enough to get going — I've built a real picture of the company. Connect your tools to deepen it, or jump in." }), 250);
      setPhase("done");
      return;
    }
    setQuestion(q);
    setTimeout(() => say({ role: "cbo", text: q.prompt, context: q.context }), 250);
  }

  async function startCompany() {
    const n = name.trim();
    if (!n || busy) return;
    setBusy(true);
    say({ role: "founder", text: n });
    try {
      const co = await api.startOnboarding(n);
      setCid(co.id);
      setPhase("interview");
      const step = await interviewApi.next(co.id);
      setProfile(step.profile);
      showQuestion(step.question, step.done);
    } catch {
      say({ role: "cbo", text: "I couldn't reach the backend. Make sure the CBO server is running on port 8000." });
    } finally { setBusy(false); }
  }

  async function answer(text: string) {
    if (!cid || !question || busy) return;
    setBusy(true);
    setInput("");
    say({ role: "founder", text });
    try {
      const step = await interviewApi.answer(cid, question.id, text);
      if (step.captured?.length) {
        setTurns((p) => { const c = [...p]; c[c.length - 1] = { ...c[c.length - 1], captured: step.captured!.map((x) => `${x.label}: ${x.value}`) }; return c; });
      }
      setProfile(step.profile);
      showQuestion(step.question, step.done);
    } finally { setBusy(false); }
  }

  async function skip() {
    if (!cid || !question || busy) return;
    setBusy(true);
    try { const step = await interviewApi.skip(cid, question.id); setProfile(step.profile); showQuestion(step.question, step.done); }
    finally { setBusy(false); }
  }

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !cid || !question) return;
    setBusy(true);
    say({ role: "founder", text: `↑ ${file.name}` });
    try {
      const res = await api.ingestUpload(cid, file);
      setTurns((p) => { const c = [...p]; c[c.length - 1] = { ...c[c.length - 1], captured: [`Indexed ${res.summary.facts} facts`] }; return c; });
      const step = await interviewApi.answer(cid, question.id, file.name);
      setProfile(step.profile);
      showQuestion(step.question, step.done);
    } catch (err) { say({ role: "cbo", text: err instanceof Error ? err.message : "Upload failed." }); }
    finally { setBusy(false); e.target.value = ""; }
  }

  function enter(go?: string) {
    if (!cid) return;
    setCompany(cid, name.trim() || "Company");
    router.replace(go || "/");
  }

  return (
    <div className="mx-auto grid min-h-[calc(100vh-64px)] max-w-5xl gap-8 px-5 pb-6 sm:px-8 lg:grid-cols-[1fr_260px]">
      <div className="flex flex-col">
        <div ref={scrollRef} className="flex-1 space-y-6 overflow-y-auto py-6">
          {turns.map((t, i) => (
            <div key={i} className="animate-fade-up">
              {t.role === "cbo" ? (
                <div className="flex gap-3">
                  <span className="mt-1 grid h-6 w-6 shrink-0 place-items-center rounded-md bg-ink"><span className="h-1.5 w-1.5 animate-breathe rounded-full bg-accent" /></span>
                  <div className="max-w-[44ch]">
                    {t.context && <p className="mb-1 text-[12px] text-accent">✦ {t.context}</p>}
                    <p className="text-[17px] leading-relaxed text-ink">{t.text}</p>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-end gap-1.5">
                  <p className="max-w-[44ch] rounded-2xl rounded-br-md bg-ink px-4 py-2.5 text-[15px] leading-relaxed text-white">{t.text}</p>
                  {t.captured?.map((c, j) => <span key={j} className="rounded-full bg-accent/10 px-2.5 py-1 text-[11px] font-medium text-accent">✦ {c}</span>)}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="sticky bottom-0 bg-canvas pt-3 pb-4">
          {phase === "name" && (
            <form onSubmit={(e) => { e.preventDefault(); startCompany(); }} className="flex items-center gap-2 rounded-2xl border border-line bg-surface px-2 py-1.5 shadow-sm focus-within:border-accent">
              <input ref={inputRef} value={name} onChange={(e) => setName(e.target.value)} placeholder="Your company name…" className="flex-1 bg-transparent px-3 py-2 text-[15px] outline-none placeholder:text-faint" />
              <button type="submit" disabled={busy} className="rounded-xl bg-ink px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">Start</button>
            </form>
          )}

          {phase === "interview" && question && (
            <div className="space-y-2">
              {question.kind === "choice" ? (
                <div className="flex flex-wrap gap-2">
                  {question.options!.map((opt) => <button key={opt} onClick={() => answer(opt)} disabled={busy} className="rounded-xl border border-line bg-surface px-4 py-2.5 text-sm text-ink transition-colors hover:border-accent hover:text-accent disabled:opacity-50">{opt}</button>)}
                </div>
              ) : question.kind === "upload" ? (
                <div className="flex items-center gap-2">
                  <label className="flex-1 cursor-pointer rounded-2xl border border-dashed border-line bg-surface px-4 py-3 text-center text-sm text-muted hover:border-accent hover:text-ink">
                    <input type="file" accept=".txt,.md,.csv,.pdf,.docx,.xlsx" onChange={onFile} className="hidden" />
                    {busy ? "Reading…" : "↑ Upload a file"}
                  </label>
                  <button onClick={skip} className="rounded-xl px-3 py-2 text-sm text-faint hover:text-ink">Skip</button>
                </div>
              ) : (
                <form onSubmit={(e) => { e.preventDefault(); if (input.trim()) answer(input.trim()); }} className="flex items-center gap-2 rounded-2xl border border-line bg-surface px-2 py-1.5 shadow-sm focus-within:border-accent">
                  <input ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type your answer…" className="flex-1 bg-transparent px-3 py-2 text-[15px] outline-none placeholder:text-faint" />
                  <button type="button" onClick={skip} className="rounded-lg px-2 py-2 text-sm text-faint hover:text-ink">Skip</button>
                  <button type="submit" disabled={busy} className="rounded-xl bg-ink px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">Send</button>
                </form>
              )}
            </div>
          )}

          {phase === "done" && (
            <div className="flex gap-2">
              <button onClick={() => enter("/sources")} className="flex-1 rounded-2xl border border-line bg-surface py-3 text-sm font-medium text-ink hover:bg-canvas">Connect your tools</button>
              <button onClick={() => enter("/")} className="flex-1 rounded-2xl bg-accent py-3 text-sm font-semibold text-white hover:opacity-90">Enter CBO →</button>
            </div>
          )}
        </div>
      </div>

      {/* Live confidence panel */}
      <aside className="hidden py-6 lg:block">
        <div className="sticky top-20">
          <p className="text-[11px] uppercase tracking-wider text-faint">What CBO knows</p>
          {profile ? (
            <div className="mt-3 space-y-3">
              <div>
                <div className="flex items-baseline justify-between"><span className="text-sm text-muted">Overall</span><span className="text-sm font-semibold text-ink">{profile.knowledge_confidence}%</span></div>
                <Bar v={profile.knowledge_confidence} />
              </div>
              {profile.stage && <p className="text-[12px] text-faint">Stage: <span className="text-ink">{profile.stage}</span></p>}
              <div className="space-y-2 border-t border-line pt-3">
                {profile.dimensions.map((d) => (
                  <div key={d.key}>
                    <div className="flex items-baseline justify-between"><span className="text-[12px] text-muted">{d.label}</span><span className="text-[12px] text-faint">{d.confidence}%</span></div>
                    <Bar v={d.confidence} />
                  </div>
                ))}
              </div>
            </div>
          ) : <p className="mt-3 text-[13px] text-faint">CBO updates this as you answer.</p>}
        </div>
      </aside>
    </div>
  );
}

function Bar({ v }: { v: number }) {
  const color = v >= 70 ? "bg-good" : v >= 40 ? "bg-warn" : v > 0 ? "bg-danger" : "bg-line";
  return <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-line"><div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${Math.max(3, v)}%` }} /></div>;
}
