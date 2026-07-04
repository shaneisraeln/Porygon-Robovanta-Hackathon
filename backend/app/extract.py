"""Extraction: plain text / records -> structured facts.

Deterministic, dependency-free heuristics (money, growth, headcount, firms,
deadlines). This is the seam an LLM extractor plugs into via ai.llm; the rest of
the pipeline is agnostic to how facts are produced.
"""
from __future__ import annotations

import re

KNOWN_FIRMS = [
    "Sequoia", "Sequoia Capital", "Accel", "a16z", "Andreessen Horowitz", "Y Combinator", "YC",
    "Peak XV", "Lightspeed", "Greylock", "Benchmark", "Khosla", "Index Ventures",
    "Founders Fund", "General Catalyst", "Bessemer", "Insight Partners", "Tiger Global",
    "Kleiner Perkins", "First Round", "Initialized", "SV Angel", "Matrix",
    "Battery Ventures", "Redpoint", "NEA", "Coatue", "Ribbit", "Craft Ventures",
    "Conviction", "Union Square Ventures", "USV", "Thrive Capital", "Felicis",
    "Spark Capital", "Amplify Partners", "8VC", "Lux Capital", "Bain Capital Ventures",
    "Menlo Ventures", "Sound Ventures",
]


def parse_money(text: str) -> float | None:
    t = text.lower().replace(",", "")
    m = re.search(r"\$?\s*(\d+(?:\.\d+)?)\s*(k|thousand|m|mn|million|b|bn|billion)?", t)
    if not m:
        return None
    n = float(m.group(1))
    unit = m.group(2)
    if unit in ("k", "thousand"):
        n *= 1_000
    elif unit in ("m", "mn", "million"):
        n *= 1_000_000
    elif unit in ("b", "bn", "billion"):
        n *= 1_000_000_000
    return n


def fmt_money(n: float) -> str:
    if n >= 1_000_000_000:
        return f"${n/1e9:.1f}B"
    if n >= 1_000_000:
        v = n / 1e6
        return f"${v:.0f}M" if v == int(v) else f"${v:.1f}M"
    if n >= 1_000:
        return f"${round(n/1e3)}K"
    return f"${round(n)}"


def parse_count(text: str) -> int | None:
    t = text.lower().replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(k|thousand|m|million)?", t)
    if not m:
        return None
    n = float(m.group(1))
    if m.group(2) in ("k", "thousand"):
        n *= 1_000
    if m.group(2) in ("m", "million"):
        n *= 1_000_000
    return round(n)


def parse_percent(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    return float(m.group(1)) if m else None


def detect_firms(text: str) -> list[str]:
    found = []
    for firm in KNOWN_FIRMS:
        if re.search(rf"\b{re.escape(firm)}\b", text, re.IGNORECASE) and firm not in found:
            found.append(firm)
    # Collapse "Sequoia Capital" -> keep specific if present, drop generic dup
    if "Sequoia Capital" in found and "Sequoia" in found:
        found.remove("Sequoia")
    return found


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.replace("\r", " "))
    return [p.strip() for p in parts if p.strip()]


def find_deadline(text: str):
    m = re.search(r"\b(by|before|due|end of)\s+(today|tomorrow|monday|tuesday|wednesday|thursday|friday|next week|this week|eod)", text, re.IGNORECASE)
    return m.group(0) if m else None


# ---------------- Onboarding extraction ----------------

def extract_onboarding(key: str, text: str) -> list[dict]:
    t = text.strip()
    if not t:
        return []
    low = t.lower()
    neg = re.search(r"\b(no|not|none|don'?t|nope|nothing|haven'?t)\b", low) is not None
    out: list[dict] = []

    def f(type_, k, label, value, num=None, conf=0.8):
        out.append({"type": type_, "key": k, "label": label, "value": value, "num": num, "confidence": conf, "evidence": t})

    if key == "what":
        f("product", "what", "What we're building", t, conf=0.95)
    elif key == "problem":
        f("strategy", "problem", "Problem we solve", t, conf=0.9)
    elif key == "customers":
        f("customer", "segment", "Customer segment", t, conf=0.9)
    elif key == "stage":
        f("strategy", "stage", "Company stage", t, conf=0.95)
    elif key == "users":
        if neg:
            f("customer", "count", "Active customers", "Pre-launch / no users yet", 0, 0.85)
        else:
            n = parse_count(t)
            f("customer", "count", "Active customers", str(n) if n is not None else t, n, 0.85 if n is not None else 0.6)
    elif key == "pricing":
        if neg:
            f("money", "revenue", "Revenue", "Not charging yet", 0, 0.85)
        else:
            m = parse_money(t)
            if m is not None:
                suffix = "/mo" if re.search(r"mo|month", low) else ""
                f("money", "pricing", "Pricing", fmt_money(m) + suffix, m, 0.8)
            else:
                f("money", "pricing", "Pricing", t, conf=0.6)
    elif key == "growth_feel":
        table = [
            (r"explod|rocket|crazy|3x|triple", 40, "Exploding"),
            (r"fast|strong|great|accelerat", 20, "Growing fast"),
            (r"stead|good|ok|fine", 8, "Growing steadily"),
            (r"flat|stall|stuck|slow|plateau", 2, "Flat"),
            (r"not charg|no revenue|pre.?launch|no users", 0, "Not charging yet"),
        ]
        hit = next((row for row in table if re.search(row[0], low)), None)
        if hit:
            f("money", "growth", "Growth rate", f"{hit[1]}% ({hit[2]})", hit[1], 0.7)
        else:
            f("money", "growth_feel", "Growth (described)", t, conf=0.5)
    elif key == "spend":
        m = parse_money(t)
        f("money", "monthly_spend", "Monthly spend (burn)", (fmt_money(m) + "/mo") if m is not None else t, m, 0.85 if m is not None else 0.5)
    elif key == "funding":
        boot = re.search(r"bootstrap|self.?fund|no funding|haven'?t raised", low)
        m = parse_money(t)
        if boot and m is None:
            f("investor", "funding", "Funding", "Bootstrapped", 0, 0.85)
        elif m is not None:
            f("investor", "funding", "Raised to date", fmt_money(m), m, 0.8)
        else:
            f("investor", "funding", "Funding", t, conf=0.55)
    elif key == "team":
        n = parse_count(t)
        f("team", "headcount", "Team size", str(n) if n is not None else t, n, 0.85 if n is not None else 0.5)
    elif key == "investors":
        firms = detect_firms(t)
        if neg and not firms:
            f("investor", "status", "Investors", "No investors yet — bootstrapped", 0, 0.85)
        elif firms:
            f("investor", "backers", "Investors / conversations", ", ".join(firms), len(firms), 0.85)
        else:
            f("investor", "status", "Investors", t, conf=0.6)
    elif key == "goals":
        f("goal", "goal", "6-month goal", t, conf=0.9)
    return out


# ---------------- Free-text document extraction ----------------

def extract_document(text: str) -> list[dict]:
    facts: list[dict] = []

    def f(type_, k, label, value, num=None, conf=0.7, evidence=""):
        facts.append({"type": type_, "key": k, "label": label, "value": value, "num": num, "confidence": conf, "evidence": evidence})

    for s in split_sentences(text):
        low = s.lower()
        if re.search(r"\b(arr|mrr|revenue|recurring)\b", low):
            m = parse_money(s)
            if m is not None:
                f("money", "revenue", "Revenue", fmt_money(m), m, 0.75, s)
        if re.search(r"\b(burn|spend|expenses)\b", low):
            m = parse_money(s)
            if m is not None:
                f("money", "monthly_spend", "Monthly spend (burn)", fmt_money(m) + "/mo", m, 0.7, s)
        if re.search(r"\b(raise|raising|round|seed|series [a-c])\b", low):
            m = parse_money(s)
            if m is not None:
                f("investor", "raise_target", "Raise target", fmt_money(m), m, 0.7, s)
        if re.search(r"\b(grow|growth|growing|mom|yoy)\b", low):
            p = parse_percent(s)
            if p is not None:
                f("money", "growth", "Growth rate", f"{p}%", p, 0.7, s)
        if re.search(r"\b(retention|churn|retain)\b", low):
            p = parse_percent(s)
            if p is not None:
                f("customer", "retention", "Retention", f"{p}%", p, 0.7, s)
        if re.search(r"\b(customers|users|accounts|logos|clients)\b", low):
            n = parse_count(s)
            if n is not None and n < 10_000_000:
                f("customer", "count", "Customers / users", str(n), n, 0.6, s)
        if re.search(r"\b(team|headcount|employees|engineers|people|hires)\b", low):
            n = parse_count(s)
            if n is not None and n < 100_000:
                f("team", "headcount", "Team size", str(n), n, 0.55, s)
        if re.search(r"\b(tam|market size|addressable)\b", low):
            m = parse_money(s)
            if m is not None:
                f("market", "tam", "Addressable market", fmt_money(m), m, 0.7, s)

    # dedupe by (key,value) keeping highest confidence
    best: dict[str, dict] = {}
    for fc in facts:
        k = f"{fc['key']}:{fc['value']}"
        if k not in best or fc["confidence"] > best[k]["confidence"]:
            best[k] = fc
    return list(best.values())
