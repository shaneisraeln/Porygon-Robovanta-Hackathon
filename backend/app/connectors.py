"""Universal Connector Framework.

Every connector implements the same lifecycle:
  connect -> sync -> extract -> normalize -> createEntities -> createRelationships
  -> updateKnowledgeGraph -> indexVectors -> publishEvents

The base class implements the shared pipeline; concrete connectors only provide
`sync()` (real API calls, incremental via cursor). No connector fabricates data —
if a credential is missing it cannot sync, so nothing fake ever enters memory.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod

import httpx

from . import memory
from .config import settings
from .extract import detect_firms, extract_document, find_deadline, fmt_money, parse_money, split_sentences


# ------------- record -> knowledge mapping (per kind) -------------

def record_to_knowledge(rec: dict) -> dict:
    kind = rec.get("kind")
    fn = {
        "email": _from_email,
        "calendar_event": _from_calendar,
        "commit": _from_commit,
        "issue": _from_issue,
        "payment": _from_payment,
        "message": _from_message,
        "crm_contact": _from_crm,
        "analytics": _from_analytics,
        "document": _from_document,
    }.get(kind, _from_generic)
    return fn(rec)


def _k(entities=None, facts=None, edges=None, timeline=None, chunk=None, notifications=None, investor=None):
    return {
        "entities": entities or [],
        "facts": facts or [],
        "edges": edges or [],
        "timeline": timeline,
        "chunk": chunk,
        "notifications": notifications or [],
        "investor": investor,
    }


def _fact(type_, key, label, value, ref, num=None, conf=0.7, evidence="", entity=None):
    return {"type": type_, "key": key, "label": label, "value": value, "num": num,
            "confidence": conf, "evidence": evidence, "source_ref": ref, "entity": entity}


def _from_email(rec):
    p = rec
    sender = p.get("fromName") or p.get("from") or "Unknown sender"
    subject = p.get("subject", "")
    body = p.get("body", "")
    blob = f"{subject} {body}"
    firms = detect_firms(f"{sender} {p.get('from','')} {blob}")
    is_inv = bool(firms)
    ref = f"Gmail · {subject or 'email'}"
    facts = []
    money = parse_money(blob)
    if money and any(w in blob.lower() for w in ("arr", "mrr", "revenue", "raise", "round", "valuation", "invest")):
        facts.append(_fact("investor" if is_inv else "money", "raise_target" if is_inv else "revenue",
                            "Raise discussed" if is_inv else "Revenue mentioned", fmt_money(money), ref, money, 0.6, subject))
    dl = find_deadline(blob)
    if dl:
        facts.append(_fact("task", "deadline", "Deadline", f"{subject or 'Item'} — {dl}", ref, conf=0.6, evidence=body[:120]))
    asks = any(w in body.lower() for w in ("follow up", "circle back", "send", "share", "could you", "deck", "metrics", "runway", "update"))
    name = firms[0] if is_inv else sender
    edges = [{"from": name, "to": "__company__", "relation": "emailed about the round" if is_inv else "emailed", "evidence": subject, "confidence": 0.7}]
    if asks and is_inv:
        edges.append({"from": name, "to": "__company__", "relation": "requested follow-up", "evidence": body[:100], "confidence": 0.8})
    agents = ["fundraising", "investor"] if is_inv else ["operations"]
    notifs = []
    if is_inv and asks:
        notifs.append({"title": f"{firms[0]} needs a follow-up", "detail": f"{sender}: \"{(subject or body)[:80]}\". Draft ready in the War Room.", "agents": agents, "severity": "high"})
    return _k(
        entities=[{"type": "investor" if is_inv else "person", "name": name, "relation": "fundraising" if is_inv else "in touch with"}],
        facts=facts, edges=edges,
        timeline={"kind": "Email", "title": f"{firms[0]}: {subject or 'email'}" if is_inv else f"Email: {subject or '(no subject)'}",
                  "summary": body[:160], "who": [name], "why": ("Investor engaged, awaiting reply" if asks else "Investor activity") if is_inv else "Inbound communication",
                  "evidence": subject or body[:120], "confidence": 0.7, "what_changed": "A follow-up is due" if asks else "Touchpoint logged", "agents": agents},
        chunk=f"Email from {sender}. Subject: {subject}. {body}",
        notifications=notifs,
        investor=({"firm": firms[0], "name": sender, "tone": "positive" if asks else "neutral", "kind": "email"} if is_inv else None),
    )


def _from_calendar(rec):
    title = rec.get("title", "Meeting")
    attendees = [str(a) for a in rec.get("attendees", [])]
    firms = detect_firms(f"{title} {' '.join(attendees)}")
    is_inv = bool(firms)
    ref = f"Calendar · {title}"
    edges = [{"from": title, "to": a, "relation": "attended by", "confidence": 0.8} for a in attendees]
    if is_inv:
        edges.append({"from": firms[0], "to": "__company__", "relation": "meeting scheduled", "evidence": title, "confidence": 0.85})
    agents = ["meeting", "investor", "fundraising"] if is_inv else ["operations"]
    ents = [{"type": "meeting", "name": title, "relation": "scheduled"}]
    if is_inv:
        ents.append({"type": "investor", "name": firms[0], "relation": "fundraising"})
    notifs = [{"title": f"Prep ready for {firms[0]}", "detail": f"{title} scheduled. CBO prepared background, objections and talking points.", "agents": agents, "severity": "medium"}] if is_inv else []
    return _k(
        entities=ents,
        facts=[_fact("meeting", "meeting", "Meeting", f"{title} ({len(attendees)} attendees)", ref, conf=0.8, evidence=title)],
        edges=edges,
        timeline={"kind": "Meeting", "title": title, "summary": f"With {', '.join(attendees) or 'team'}.", "who": attendees,
                  "why": "Investor meeting — prep needed" if is_inv else "Scheduled meeting", "evidence": f"{title} — {', '.join(attendees)}",
                  "confidence": 0.85, "what_changed": "Investor meeting on calendar" if is_inv else "Meeting added", "agents": agents},
        chunk=f"Meeting \"{title}\" with {', '.join(attendees)}.",
        notifications=notifs,
        investor=({"firm": firms[0], "name": attendees[0] if attendees else firms[0], "tone": "neutral", "kind": "calendar_event"} if is_inv else None),
    )


def _from_commit(rec):
    author = rec.get("author", "Engineer")
    msg = rec.get("message", "")
    ref = f"GitHub · {rec.get('repo','repo')}"
    return _k(
        entities=[{"type": "person", "name": author, "relation": "ships code"}],
        facts=[_fact("product", "velocity", "Shipping activity", msg[:60], ref, conf=0.55, evidence=msg)],
        edges=[{"from": author, "to": "__company__", "relation": "committed", "evidence": msg, "confidence": 0.7}],
        timeline={"kind": "Commit", "title": f"{author}: {msg[:60]}", "summary": f"{rec.get('additions',0)}+ / {rec.get('deletions',0)}- in {rec.get('repo','')}",
                  "who": [author], "why": "Engineering velocity signal", "evidence": msg, "confidence": 0.6, "what_changed": "Product moved forward", "agents": ["product", "execution"]},
        chunk=f"Commit by {author}: {msg}",
    )


def _from_issue(rec):
    title = rec.get("title", "")
    ref = "GitHub · issue"
    state = rec.get("state", "open")
    return _k(
        entities=[{"type": "task", "name": title[:28], "relation": "tracking"}],
        facts=[_fact("task", "issue", "Open issue", title, ref, conf=0.6, evidence=title)],
        timeline={"kind": "Issue", "title": f"Issue {state}: {title}", "summary": f"By {rec.get('author','')}", "who": [rec.get("author", "")],
                  "why": "Potential execution blocker" if state == "open" else "Execution progress", "evidence": title, "confidence": 0.6,
                  "what_changed": "New blocker" if state == "open" else "Blocker resolved", "agents": ["execution", "product"]},
        chunk=f"Issue ({state}): {title}",
    )


def _from_payment(rec):
    customer = rec.get("customer", "Customer")
    amount = float(rec.get("amount", 0) or 0)
    ref = f"Stripe · {rec.get('plan','payment')}"
    return _k(
        entities=[{"type": "customer", "name": customer, "relation": "pays"}],
        facts=[_fact("money", "revenue", "Revenue (payment)", fmt_money(amount), ref, amount, 0.7, f"{customer} {fmt_money(amount)}")],
        edges=[{"from": customer, "to": "__company__", "relation": "pays", "evidence": f"{fmt_money(amount)} {rec.get('plan','')}", "confidence": 0.85}],
        timeline={"kind": "Payment", "title": f"{customer} paid {fmt_money(amount)}", "summary": f"{rec.get('plan','')} plan", "who": [customer],
                  "why": "Revenue event", "evidence": f"{customer} — {fmt_money(amount)}", "confidence": 0.85, "what_changed": "Revenue increased", "agents": ["finance", "customer"]},
        chunk=f"{customer} paid {fmt_money(amount)} on the {rec.get('plan','')} plan.",
    )


def _from_message(rec):
    author = rec.get("author", "Teammate")
    text = rec.get("text", "")
    ref = f"Slack · #{rec.get('channel','general')}"
    return _k(
        entities=[{"type": "person", "name": author, "relation": "teammate"}],
        timeline={"kind": "Message", "title": f"#{rec.get('channel','')}: {text[:60]}", "summary": f"{author} in #{rec.get('channel','')}", "who": [author],
                  "why": "Team communication", "evidence": text[:120], "confidence": 0.5, "what_changed": "Discussion logged", "agents": ["operations"]},
        chunk=f"Slack #{rec.get('channel','')} — {author}: {text}",
    )


def _from_crm(rec):
    name = rec.get("name") or rec.get("company") or "Lead"
    value = float(rec.get("value", 0) or 0)
    ref = f"CRM · {name}"
    facts = [_fact("money", "pipeline", "Pipeline value", fmt_money(value), ref, value, 0.6)] if value else []
    return _k(
        entities=[{"type": "customer", "name": name, "relation": "in pipeline"}],
        facts=facts,
        edges=[{"from": name, "to": "__company__", "relation": f"deal · {rec.get('stage','')}", "evidence": fmt_money(value), "confidence": 0.7}],
        timeline={"kind": "CRM", "title": f"{name} — {rec.get('stage','')}", "summary": f"Deal {fmt_money(value)}" if value else "Pipeline update", "who": [name],
                  "why": "Sales pipeline movement", "evidence": f"{name} · {rec.get('stage','')}", "confidence": 0.7, "what_changed": "Pipeline updated", "agents": ["customer", "finance"]},
        chunk=f"CRM: {name} at stage {rec.get('stage','')}, value {fmt_money(value)}.",
    )


def _from_analytics(rec):
    metric = rec.get("metric", "Metric")
    value = str(rec.get("value", ""))
    ref = f"Analytics · {metric}"
    return _k(
        entities=[{"type": "metric", "name": metric, "relation": "tracks"}],
        timeline={"kind": "Analytics", "title": f"{metric}: {value}", "summary": f"Change: {rec.get('change','')}", "who": [],
                  "why": "Product/usage signal", "evidence": f"{metric} {value} {rec.get('change','')}", "confidence": 0.6, "what_changed": f"{metric} updated", "agents": ["market", "execution"]},
        chunk=f"Analytics — {metric}: {value} ({rec.get('change','')}).",
    )


def _from_document(rec):
    name = rec.get("name", "Document")
    text = rec.get("text", "")
    facts = extract_document(text)
    for f in facts:
        f["source_ref"] = name
    # multiple chunks handled by pipeline via 'chunks' list
    sentences = split_sentences(text)
    chunks = [" ".join(sentences[i:i + 3]) for i in range(0, len(sentences), 3) if sentences[i:i + 3]] or [text]
    return _k(
        entities=[],
        facts=facts,
        timeline={"kind": "Document", "title": f"Indexed {name}", "summary": text[:160], "who": [],
                  "why": "Knowledge added to memory", "evidence": text[:120], "confidence": 0.7, "what_changed": f"{len(facts)} facts extracted", "agents": ["strategy"]},
        chunk=None,
    ) | {"chunks": chunks, "document": {"name": name, "chars": len(text)}}


def _from_generic(rec):
    return _k(timeline={"kind": rec.get("kind", "event"), "title": rec.get("title", "Event"), "summary": "", "who": [],
                        "why": "", "evidence": "", "confidence": 0.4, "what_changed": "", "agents": []})


# ------------- the shared pipeline -------------

def ingest_records(company_id: str, connector_id: str, records: list[dict]) -> dict:
    stats = {"records": len(records), "entities": 0, "facts": 0, "relationships": 0, "timeline": 0, "notifications": 0}
    agents: set[str] = set()
    for rec in records:
        k = record_to_knowledge(rec)
        name_to_id: dict[str, str] = {"__company__": memory.company_node_id(company_id)}

        # ENTITY DETECTION -> KNOWLEDGE GRAPH
        for spec in k["entities"]:
            eid = memory.upsert_entity(company_id, spec["type"], spec["name"], spec.get("relation", "related to"))
            name_to_id[spec["name"].lower()] = eid
            stats["entities"] += 1

        # MEMORY (facts)
        primary_id = name_to_id.get(k["entities"][0]["name"].lower()) if k["entities"] else None
        for f in k["facts"]:
            ent_id = name_to_id.get(f.get("entity", "").lower()) if f.get("entity") else primary_id
            memory.add_fact(company_id, f["type"], f["key"], f["label"], f["value"], f.get("source_ref", connector_id),
                            num=f.get("num"), entity_id=ent_id, source_kind="document", evidence=f.get("evidence", ""),
                            confidence=f.get("confidence", 0.7), owner=connector_id)
            stats["facts"] += 1

        # RELATIONSHIP DETECTION
        for e in k["edges"]:
            frm = _resolve(company_id, name_to_id, e["from"])
            to = _resolve(company_id, name_to_id, e["to"])
            memory.add_relationship(company_id, frm, to, e["relation"], e.get("evidence", ""), e.get("confidence", 0.7))
            stats["relationships"] += 1

        # VECTOR INDEX
        for ch in ([k["chunk"]] if k.get("chunk") else []) + k.get("chunks", []):
            if ch:
                memory.add_chunk(company_id, k["timeline"]["title"] if k.get("timeline") else connector_id, ch)
        if k.get("document"):
            memory.add_document(company_id, k["document"]["name"], connector_id, k["document"]["chars"])

        # TIMELINE
        if k.get("timeline"):
            t = k["timeline"]
            entity_ids = [name_to_id[w.lower()] for w in t.get("who", []) if w.lower() in name_to_id]
            memory.add_timeline(company_id, connector_id=connector_id, kind=t["kind"], title=t["title"], summary=t.get("summary", ""),
                                who=t.get("who", []), why=t.get("why", ""), evidence=t.get("evidence", ""), confidence=t.get("confidence", 0.7),
                                what_changed=t.get("what_changed", ""), agents=t.get("agents", []), entity_ids=entity_ids, at=rec.get("at"))
            stats["timeline"] += 1
            agents.update(t.get("agents", []))

        # INVESTOR WAR-ROOM
        inv = k.get("investor")
        if inv:
            memory.upsert_investor(company_id, inv["firm"], name=inv.get("name", inv["firm"]),
                                   state="warm" if inv.get("kind") == "calendar_event" else "due-follow-up",
                                   probability=60 if inv.get("kind") == "calendar_event" else 50, warmth=55)
            memory.add_investor_event(company_id, inv["firm"], k["timeline"]["title"], inv.get("tone", "neutral"), inv.get("kind", ""))

        # NOTIFY AGENTS
        for n in k.get("notifications", []):
            memory.add_notification(company_id, n["title"], n["detail"], n["agents"], n.get("severity", "medium"))
            stats["notifications"] += 1
            agents.update(n["agents"])

        # Investor discovery from any text (documents, messages) — real signal,
        # never fabricated: only firms actually mentioned are tracked.
        blob = " ".join(([k.get("chunk")] if k.get("chunk") else []) + k.get("chunks", []))
        for firm in detect_firms(blob):
            memory.upsert_investor(company_id, firm, name=firm, state="need-intro", probability=40, warmth=40, concerns=["Why now", "Traction"])

    stats["agents_notified"] = sorted(agents)
    return stats


def _resolve(company_id: str, name_to_id: dict, name: str) -> str:
    if name == "__company__":
        return memory.company_node_id(company_id)
    if name.lower() in name_to_id:
        return name_to_id[name.lower()]
    eid = memory.upsert_entity(company_id, "person", name, "connected to")
    name_to_id[name.lower()] = eid
    return eid


# ------------- Connector base + concrete connectors -------------

class Connector(ABC):
    id: str = "base"
    name: str = "Connector"
    category: str = "documents"
    blurb: str = ""
    requires_credential: bool = True

    def __init__(self, company_id: str, token: str | None = None, cursor: str | None = None):
        self.company_id = company_id
        self.token = token
        self.cursor = cursor or ""
        self.new_cursor = self.cursor

    # --- interface ---
    def connect(self, token: str | None, meta: dict | None = None):
        if token:
            memory.save_credential(self.company_id, self.id, token, meta)
            self.token = token

    @abstractmethod
    def sync(self) -> list[dict]:
        """Return normalized records since the last cursor (incremental)."""

    def extract(self, raw):  # already normalized in sync for these connectors
        return raw

    def normalize(self, raw):
        return raw

    def create_entities(self, k):  # handled by pipeline
        ...

    def create_relationships(self, k):
        ...

    def update_knowledge_graph(self, k):
        ...

    def index_vectors(self, k):
        ...

    def publish_events(self, k):
        ...

    def run(self) -> dict:
        records = self.sync()
        summary = ingest_records(self.company_id, self.id, records)
        summary["cursor"] = self.new_cursor
        return summary


class ManualUploadConnector(Connector):
    id, name, category = "upload", "Manual Upload", "documents"
    blurb = "PDF, DOCX, PPTX, CSV, XLSX, TXT, Markdown → knowledge."
    requires_credential = False

    def __init__(self, company_id, records=None, **kw):
        super().__init__(company_id, **kw)
        self._records = records or []

    def sync(self):
        return self._records


class GitHubConnector(Connector):
    id, name, category = "github", "GitHub", "product"
    blurb = "Commits, issues, PRs → velocity, contributors, blockers."

    def sync(self):
        if not self.token:
            return []
        headers = {"Authorization": f"token {self.token}", "Accept": "application/vnd.github+json"}
        records: list[dict] = []
        with httpx.Client(timeout=20) as cli:
            repos = cli.get("https://api.github.com/user/repos", headers=headers, params={"sort": "pushed", "per_page": 3}).json()
            if not isinstance(repos, list):
                return []
            since = self.cursor or None
            latest = self.cursor
            for repo in repos:
                full = repo.get("full_name")
                commits = cli.get(f"https://api.github.com/repos/{full}/commits", headers=headers, params={"since": since, "per_page": 10} if since else {"per_page": 10})
                for c in commits.json() if commits.status_code == 200 else []:
                    commit = c.get("commit", {})
                    date = commit.get("author", {}).get("date", "")
                    records.append({"kind": "commit", "at": time.time(), "author": (commit.get("author", {}) or {}).get("name", "dev"),
                                    "message": commit.get("message", "")[:140], "repo": full, "additions": 0, "deletions": 0})
                    latest = max(latest, date) if latest else date
                issues = cli.get(f"https://api.github.com/repos/{full}/issues", headers=headers, params={"state": "open", "per_page": 5})
                for i in issues.json() if issues.status_code == 200 else []:
                    if i.get("pull_request"):
                        continue
                    records.append({"kind": "issue", "at": time.time(), "title": i.get("title", ""), "state": "open", "author": (i.get("user") or {}).get("login", "")})
            self.new_cursor = latest or self.cursor
        return records


class NotionConnector(Connector):
    id, name, category = "notion", "Notion", "documents"
    blurb = "Pages & docs → roadmap, decisions, knowledge."

    def sync(self):
        if not self.token:
            return []
        headers = {"Authorization": f"Bearer {self.token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
        records: list[dict] = []
        with httpx.Client(timeout=20) as cli:
            res = cli.post("https://api.notion.com/v1/search", headers=headers, json={"filter": {"property": "object", "value": "page"}, "page_size": 10})
            for page in res.json().get("results", []) if res.status_code == 200 else []:
                title = _notion_title(page)
                records.append({"kind": "document", "at": time.time(), "name": f"Notion · {title}", "text": title})
        return records


class StripeConnector(Connector):
    id, name, category = "stripe", "Stripe", "finance"
    blurb = "Charges & subscriptions → revenue, customers, plans."

    def sync(self):
        if not self.token:
            return []
        records: list[dict] = []
        with httpx.Client(timeout=20) as cli:
            res = cli.get("https://api.stripe.com/v1/charges", headers={"Authorization": f"Bearer {self.token}"}, params={"limit": 20})
            for ch in res.json().get("data", []) if res.status_code == 200 else []:
                if not ch.get("paid"):
                    continue
                records.append({"kind": "payment", "at": ch.get("created", time.time()), "customer": (ch.get("billing_details") or {}).get("name") or ch.get("customer") or "Customer",
                                "amount": (ch.get("amount", 0) or 0) / 100.0, "plan": ch.get("description") or "charge"})
        return records


class GoogleConnector(Connector):
    """Base for Google APIs (Drive/Gmail/Calendar) via an OAuth access token."""
    category = "communication"

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}


class GmailConnector(GoogleConnector):
    id, name, blurb = "gmail", "Gmail", "Emails → senders, investors, asks, deadlines."

    def sync(self):
        if not self.token:
            return []
        records: list[dict] = []
        with httpx.Client(timeout=20) as cli:
            lst = cli.get("https://gmail.googleapis.com/gmail/v1/users/me/messages", headers=self._headers(), params={"maxResults": 10})
            for m in lst.json().get("messages", []) if lst.status_code == 200 else []:
                full = cli.get(f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m['id']}", headers=self._headers(), params={"format": "metadata", "metadataHeaders": ["From", "Subject"]})
                if full.status_code != 200:
                    continue
                payload = full.json()
                headers = {h["name"]: h["value"] for h in payload.get("payload", {}).get("headers", [])}
                records.append({"kind": "email", "at": time.time(), "fromName": headers.get("From", ""), "from": headers.get("From", ""),
                                "subject": headers.get("Subject", ""), "body": payload.get("snippet", "")})
        return records


class CalendarConnector(GoogleConnector):
    id, name, blurb = "gcal", "Google Calendar", "Events → meetings, attendees, investor sessions."

    def sync(self):
        if not self.token:
            return []
        records: list[dict] = []
        with httpx.Client(timeout=20) as cli:
            res = cli.get("https://www.googleapis.com/calendar/v3/calendars/primary/events", headers=self._headers(), params={"maxResults": 10, "orderBy": "startTime", "singleEvents": "true"})
            for ev in res.json().get("items", []) if res.status_code == 200 else []:
                records.append({"kind": "calendar_event", "at": time.time(), "title": ev.get("summary", "Meeting"),
                                "attendees": [a.get("email", "") for a in ev.get("attendees", [])]})
        return records


class DriveConnector(GoogleConnector):
    id, name, category, blurb = "gdrive", "Google Drive", "documents", "Files → text, tables, financials, people."

    def sync(self):
        if not self.token:
            return []
        records: list[dict] = []
        with httpx.Client(timeout=20) as cli:
            res = cli.get("https://www.googleapis.com/drive/v3/files", headers=self._headers(), params={"pageSize": 10, "q": "mimeType='application/vnd.google-apps.document'"})
            for fdoc in res.json().get("files", []) if res.status_code == 200 else []:
                exp = cli.get(f"https://www.googleapis.com/drive/v3/files/{fdoc['id']}/export", headers=self._headers(), params={"mimeType": "text/plain"})
                text = exp.text if exp.status_code == 200 else fdoc.get("name", "")
                records.append({"kind": "document", "at": time.time(), "name": f"Drive · {fdoc.get('name','')}", "text": text[:20000]})
        return records


class SlackConnector(Connector):
    id, name, category, blurb = "slack", "Slack", "communication", "Messages → topics, mentions, signals."

    def sync(self):
        if not self.token:
            return []
        records: list[dict] = []
        with httpx.Client(timeout=20) as cli:
            chans = cli.get("https://slack.com/api/conversations.list", headers={"Authorization": f"Bearer {self.token}"}, params={"limit": 5})
            for ch in chans.json().get("channels", []) if chans.status_code == 200 else []:
                hist = cli.get("https://slack.com/api/conversations.history", headers={"Authorization": f"Bearer {self.token}"}, params={"channel": ch["id"], "limit": 5})
                for msg in hist.json().get("messages", []) if hist.status_code == 200 else []:
                    records.append({"kind": "message", "at": float(msg.get("ts", time.time())), "channel": ch.get("name", ""), "author": msg.get("user", "teammate"), "text": msg.get("text", "")})
        return records


def _notion_title(page: dict) -> str:
    props = page.get("properties", {})
    for v in props.values():
        if v.get("type") == "title":
            return "".join(t.get("plain_text", "") for t in v.get("title", [])) or "Untitled"
    return "Untitled"


REGISTRY: dict[str, type[Connector]] = {
    c.id: c for c in [
        GmailConnector, CalendarConnector, DriveConnector, GitHubConnector,
        NotionConnector, SlackConnector, StripeConnector, ManualUploadConnector,
    ]
}


def connector_catalog() -> list[dict]:
    return [{"id": c.id, "name": c.name, "category": c.category, "blurb": c.blurb, "requires_credential": c.requires_credential}
            for c in REGISTRY.values()]
