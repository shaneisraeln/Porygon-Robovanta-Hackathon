"""Company Memory: the single source of truth.

Stores knowledge (entities, facts, relationships, timeline, investors, vectors)
— never raw documents. Every fact carries source/confidence/timestamp/evidence/
version/owner. Provides graph queries and vector retrieval used by the Brain,
Council, Brief and Investor intelligence.
"""
from __future__ import annotations

import json
import time
import uuid

from .db import get_conn, tx
from .embedding import cosine, embed

COMPANY_NODE = "company"


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def now() -> float:
    return time.time()


# ---------------- Company ----------------

def create_company(name: str, what: str = "", customers: str = "", stage: str = "") -> dict:
    cid = _id("co")
    with tx() as c:
        c.execute(
            "INSERT INTO companies(id,name,what,customers,stage,created_at) VALUES(?,?,?,?,?,?)",
            (cid, name, what, customers, stage, now()),
        )
        # The company is the root graph node.
        c.execute(
            "INSERT OR IGNORE INTO entities(id,company_id,type,name,created_at) VALUES(?,?,?,?,?)",
            (f"ent_company_{cid}", cid, "company", name, now()),
        )
    return get_company(cid)


def get_company(company_id: str) -> dict | None:
    row = get_conn().execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone()
    return dict(row) if row else None


def update_company(company_id: str, **fields) -> None:
    allowed = {"name", "what", "customers", "stage"}
    sets = {k: v for k, v in fields.items() if k in allowed and v}
    if not sets:
        return
    cols = ", ".join(f"{k}=?" for k in sets)
    with tx() as c:
        c.execute(f"UPDATE companies SET {cols} WHERE id=?", (*sets.values(), company_id))


def company_node_id(company_id: str) -> str:
    return f"ent_company_{company_id}"


# ---------------- Entities & graph ----------------

def upsert_entity(company_id: str, type_: str, name: str, relation: str = "related to") -> str:
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM entities WHERE company_id=? AND type=? AND lower(name)=lower(?)",
        (company_id, type_, name),
    ).fetchone()
    if row:
        return row["id"]
    eid = _id("ent")
    with tx() as c:
        c.execute(
            "INSERT INTO entities(id,company_id,type,name,created_at) VALUES(?,?,?,?,?)",
            (eid, company_id, type_, name, now()),
        )
    add_relationship(company_id, company_node_id(company_id), eid, relation)
    return eid


def add_relationship(company_id: str, from_id: str, to_id: str, relation: str, evidence: str = "", confidence: float = 0.7) -> None:
    if from_id == to_id:
        return
    with tx() as c:
        c.execute(
            "INSERT OR IGNORE INTO relationships(id,company_id,from_id,to_id,relation,evidence,confidence,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (_id("rel"), company_id, from_id, to_id, relation, evidence, confidence, now()),
        )


def graph(company_id: str) -> dict:
    conn = get_conn()
    ents = [dict(r) for r in conn.execute("SELECT * FROM entities WHERE company_id=?", (company_id,)).fetchall()]
    edges = [dict(r) for r in conn.execute("SELECT * FROM relationships WHERE company_id=?", (company_id,)).fetchall()]
    return {"entities": ents, "edges": edges}


# ---------------- Facts ----------------

def add_fact(
    company_id: str,
    type_: str,
    key: str,
    label: str,
    value: str,
    source_ref: str,
    *,
    num: float | None = None,
    entity_id: str | None = None,
    source_kind: str = "conversation",
    evidence: str = "",
    confidence: float = 0.75,
    owner: str = "system",
) -> str:
    conn = get_conn()
    prior = conn.execute(
        "SELECT COUNT(*) AS n FROM facts WHERE company_id=? AND key=?", (company_id, key)
    ).fetchone()["n"]
    fid = _id("fact")
    with tx() as c:
        c.execute(
            """INSERT INTO facts(id,company_id,type,key,label,value,num,entity_id,source_kind,source_ref,evidence,confidence,version,owner,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (fid, company_id, type_, key, label, value, num, entity_id, source_kind, source_ref, evidence, confidence, prior + 1, owner, now()),
        )
    return fid


def list_facts(company_id: str, limit: int = 500) -> list[dict]:
    rows = get_conn().execute(
        "SELECT * FROM facts WHERE company_id=? ORDER BY created_at DESC LIMIT ?", (company_id, limit)
    ).fetchall()
    return [dict(r) for r in rows]


def latest_num(company_id: str, key: str) -> float | None:
    row = get_conn().execute(
        "SELECT num FROM facts WHERE company_id=? AND key=? AND num IS NOT NULL ORDER BY confidence DESC, created_at DESC LIMIT 1",
        (company_id, key),
    ).fetchone()
    return row["num"] if row else None


def facts_for_entity(company_id: str, entity_id: str) -> list[dict]:
    rows = get_conn().execute(
        "SELECT * FROM facts WHERE company_id=? AND entity_id=? ORDER BY created_at DESC", (company_id, entity_id)
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------- Vector index ----------------

def add_chunk(company_id: str, doc_name: str, text: str) -> None:
    with tx() as c:
        c.execute(
            "INSERT INTO chunks(id,company_id,doc_name,text,embedding,created_at) VALUES(?,?,?,?,?,?)",
            (_id("chk"), company_id, doc_name, text, json.dumps(embed(text)), now()),
        )


def search_chunks(company_id: str, query: str, k: int = 4) -> list[dict]:
    qv = embed(query)
    rows = get_conn().execute("SELECT doc_name,text,embedding FROM chunks WHERE company_id=?", (company_id,)).fetchall()
    scored = []
    for r in rows:
        s = cosine(qv, json.loads(r["embedding"]))
        if s > 0.02:
            scored.append({"doc_name": r["doc_name"], "text": r["text"], "score": s})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]


# ---------------- Documents ----------------

def add_document(company_id: str, name: str, connector_id: str, chars: int) -> None:
    with tx() as c:
        c.execute(
            "INSERT INTO documents(id,company_id,name,connector_id,chars,added_at) VALUES(?,?,?,?,?,?)",
            (_id("doc"), company_id, name, connector_id, chars, now()),
        )


def list_documents(company_id: str) -> list[dict]:
    return [dict(r) for r in get_conn().execute("SELECT * FROM documents WHERE company_id=? ORDER BY added_at DESC", (company_id,)).fetchall()]


# ---------------- Timeline ----------------

def add_timeline(company_id: str, *, connector_id: str, kind: str, title: str, summary: str = "", who=None, why: str = "", evidence: str = "", confidence: float = 0.7, what_changed: str = "", agents=None, entity_ids=None, at: float | None = None) -> None:
    with tx() as c:
        c.execute(
            """INSERT INTO timeline(id,company_id,at,connector_id,kind,title,summary,who,why,evidence,confidence,what_changed,agents,entity_ids)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (_id("tl"), company_id, at or now(), connector_id, kind, title, summary,
             json.dumps(who or []), why, evidence, confidence, what_changed, json.dumps(agents or []), json.dumps(entity_ids or [])),
        )


def list_timeline(company_id: str, limit: int = 60) -> list[dict]:
    rows = get_conn().execute("SELECT * FROM timeline WHERE company_id=? ORDER BY at DESC LIMIT ?", (company_id, limit)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["who"] = json.loads(d["who"])
        d["agents"] = json.loads(d["agents"])
        d["entity_ids"] = json.loads(d["entity_ids"])
        out.append(d)
    return out


# ---------------- Investors ----------------

def upsert_investor(company_id: str, firm: str, **fields) -> str:
    conn = get_conn()
    row = conn.execute("SELECT * FROM investors WHERE company_id=? AND lower(firm)=lower(?)", (company_id, firm)).fetchone()
    if row:
        return row["id"]
    iid = _id("inv")
    with tx() as c:
        c.execute(
            """INSERT INTO investors(id,company_id,name,firm,partner,sector,stage,geography,state,warmth,probability,last_touch,concerns,history,sentiment,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (iid, company_id, fields.get("name", firm), firm, fields.get("partner", ""), fields.get("sector", ""),
             fields.get("stage", ""), fields.get("geography", ""), fields.get("state", "need-intro"),
             fields.get("warmth", 40), fields.get("probability", 40), fields.get("last_touch", ""),
             json.dumps(fields.get("concerns", [])), json.dumps(fields.get("history", [])), fields.get("sentiment"), now()),
        )
    upsert_entity(company_id, "investor", firm, "fundraising")
    return iid


def get_investor(company_id: str, investor_id: str) -> dict | None:
    row = get_conn().execute("SELECT * FROM investors WHERE company_id=? AND id=?", (company_id, investor_id)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["concerns"] = json.loads(d["concerns"])
    d["history"] = json.loads(d["history"])
    return d


def list_investors(company_id: str) -> list[dict]:
    rows = get_conn().execute("SELECT * FROM investors WHERE company_id=?", (company_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["concerns"] = json.loads(d["concerns"])
        d["history"] = json.loads(d["history"])
        out.append(d)
    return out


def update_investor(company_id: str, investor_id: str, **fields) -> None:
    inv = get_investor(company_id, investor_id)
    if not inv:
        return
    json_fields = {"concerns", "history"}
    sets = {}
    for k, v in fields.items():
        if k in json_fields:
            sets[k] = json.dumps(v)
        else:
            sets[k] = v
    cols = ", ".join(f"{k}=?" for k in sets)
    with tx() as c:
        c.execute(f"UPDATE investors SET {cols} WHERE company_id=? AND id=?", (*sets.values(), company_id, investor_id))


def add_investor_event(company_id: str, firm: str, note: str, tone: str, record_kind: str = "") -> None:
    inv = get_conn().execute("SELECT * FROM investors WHERE company_id=? AND lower(firm)=lower(?)", (company_id, firm)).fetchone()
    if not inv:
        return
    history = json.loads(inv["history"])
    if any(h.get("note") == note for h in history):
        return
    history.insert(0, {"at": "just now", "note": note, "tone": tone})
    state = inv["state"]
    prob = inv["probability"]
    warmth = inv["warmth"]
    if record_kind == "calendar_event":
        state, prob, warmth = "warm", min(90, prob + 8), min(95, warmth + 10)
    elif tone == "positive":
        prob, warmth = min(95, prob + 6), min(95, warmth + 8)
    elif tone == "negative":
        state, prob = "cooling", max(5, prob - 12)
    update_investor(company_id, inv["id"], history=history, state=state, probability=prob, warmth=warmth, last_touch="just now")


# ---------------- Notifications ----------------

def add_notification(company_id: str, title: str, detail: str, agents: list[str], severity: str = "medium") -> None:
    with tx() as c:
        c.execute(
            "INSERT INTO notifications(id,company_id,at,title,detail,agents,severity) VALUES(?,?,?,?,?,?,?)",
            (_id("ntf"), company_id, now(), title, detail, json.dumps(agents), severity),
        )


def list_notifications(company_id: str, limit: int = 30) -> list[dict]:
    rows = get_conn().execute("SELECT * FROM notifications WHERE company_id=? ORDER BY at DESC LIMIT ?", (company_id, limit)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["agents"] = json.loads(d["agents"])
        out.append(d)
    return out


# ---------------- Connectors & credentials ----------------

def get_connector_state(company_id: str, connector_id: str) -> dict | None:
    row = get_conn().execute("SELECT * FROM connectors WHERE company_id=? AND id=?", (company_id, connector_id)).fetchone()
    return dict(row) if row else None


def list_connector_states(company_id: str) -> dict[str, dict]:
    rows = get_conn().execute("SELECT * FROM connectors WHERE company_id=?", (company_id,)).fetchall()
    return {r["id"]: dict(r) for r in rows}


def set_connector_state(company_id: str, connector_id: str, **fields) -> None:
    existing = get_connector_state(company_id, connector_id)
    with tx() as c:
        if existing:
            cols = ", ".join(f"{k}=?" for k in fields)
            c.execute(f"UPDATE connectors SET {cols} WHERE company_id=? AND id=?", (*fields.values(), company_id, connector_id))
        else:
            base = {"connected": 0, "last_sync": None, "cursor": "", "record_count": 0, "has_credential": 0}
            base.update(fields)
            c.execute(
                "INSERT INTO connectors(company_id,id,connected,last_sync,cursor,record_count,has_credential) VALUES(?,?,?,?,?,?,?)",
                (company_id, connector_id, base["connected"], base["last_sync"], base["cursor"], base["record_count"], base["has_credential"]),
            )


def save_credential(company_id: str, connector_id: str, token: str, meta: dict | None = None) -> None:
    with tx() as c:
        c.execute(
            "INSERT OR REPLACE INTO credentials(company_id,connector_id,token,meta) VALUES(?,?,?,?)",
            (company_id, connector_id, token, json.dumps(meta or {})),
        )


def get_credential(company_id: str, connector_id: str) -> str | None:
    row = get_conn().execute("SELECT token FROM credentials WHERE company_id=? AND connector_id=?", (company_id, connector_id)).fetchone()
    return row["token"] if row else None


# ---------------- Interview log ----------------

def log_question(company_id: str, question_id: str, status: str) -> None:
    with tx() as c:
        c.execute("INSERT OR REPLACE INTO interview_log(company_id,question_id,status,at) VALUES(?,?,?,?)",
                  (company_id, question_id, status, now()))


def interview_log(company_id: str) -> dict[str, str]:
    rows = get_conn().execute("SELECT question_id,status FROM interview_log WHERE company_id=?", (company_id,)).fetchall()
    return {r["question_id"]: r["status"] for r in rows}


# ---------------- Artifacts (versioned) ----------------

def save_artifact(company_id: str, kind: str, title: str, content: dict) -> dict:
    prior = get_conn().execute("SELECT MAX(version) AS v FROM artifacts WHERE company_id=? AND kind=?", (company_id, kind)).fetchone()["v"] or 0
    aid = _id("art")
    with tx() as c:
        c.execute("INSERT INTO artifacts(id,company_id,kind,version,title,content,created_at) VALUES(?,?,?,?,?,?,?)",
                  (aid, company_id, kind, prior + 1, title, json.dumps(content), now()))
    return {"id": aid, "kind": kind, "version": prior + 1, "title": title, "content": content}


def latest_artifact(company_id: str, kind: str) -> dict | None:
    row = get_conn().execute("SELECT * FROM artifacts WHERE company_id=? AND kind=? ORDER BY version DESC LIMIT 1", (company_id, kind)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["content"] = json.loads(d["content"])
    return d


def list_artifacts(company_id: str) -> list[dict]:
    rows = get_conn().execute("SELECT id,kind,version,title,created_at FROM artifacts WHERE company_id=? GROUP BY kind HAVING MAX(version) ORDER BY created_at DESC", (company_id,)).fetchall()
    return [dict(r) for r in rows]


# ---------------- Outreach ----------------

def upsert_outreach(company_id: str, investor_id: str, subject: str, body: str, status: str = "drafted") -> dict:
    existing = get_conn().execute("SELECT id FROM outreach WHERE company_id=? AND investor_id=?", (company_id, investor_id)).fetchone()
    with tx() as c:
        if existing:
            c.execute("UPDATE outreach SET subject=?,body=?,status=?,updated_at=? WHERE company_id=? AND investor_id=?",
                      (subject, body, status, now(), company_id, investor_id))
            oid = existing["id"]
        else:
            oid = _id("out")
            c.execute("INSERT INTO outreach(id,company_id,investor_id,status,subject,body,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                      (oid, company_id, investor_id, status, subject, body, now(), now()))
    return {"id": oid, "status": status}


def set_outreach_status(company_id: str, investor_id: str, status: str) -> None:
    with tx() as c:
        c.execute("UPDATE outreach SET status=?,updated_at=? WHERE company_id=? AND investor_id=?", (status, now(), company_id, investor_id))


def list_outreach(company_id: str) -> list[dict]:
    return [dict(r) for r in get_conn().execute("SELECT * FROM outreach WHERE company_id=?", (company_id,)).fetchall()]


def get_outreach(company_id: str, investor_id: str) -> dict | None:
    row = get_conn().execute("SELECT * FROM outreach WHERE company_id=? AND investor_id=?", (company_id, investor_id)).fetchone()
    return dict(row) if row else None


# ---------------- Investor Intelligence Database (global) ----------------

_INVDB_LIST = ("partners", "stages", "industries", "geos", "portfolio", "recent")


def investordb_count() -> int:
    return get_conn().execute("SELECT COUNT(*) AS n FROM investor_db").fetchone()["n"]


def _invdb_row(r) -> dict:
    d = dict(r)
    for k in _INVDB_LIST:
        d[k] = json.loads(d.get(k) or "[]")
    return d


def investordb_all() -> list[dict]:
    return [_invdb_row(r) for r in get_conn().execute("SELECT * FROM investor_db").fetchall()]


def investordb_get(firm_id: str) -> dict | None:
    r = get_conn().execute("SELECT * FROM investor_db WHERE id=?", (firm_id,)).fetchone()
    return _invdb_row(r) if r else None


def investordb_upsert(rec: dict) -> str:
    fid = rec.get("id") or _id("vc")
    existing = get_conn().execute("SELECT id FROM investor_db WHERE lower(firm)=lower(?)", (rec["firm"],)).fetchone()
    if existing:
        fid = existing["id"]
    payload = {
        "id": fid, "firm": rec["firm"],
        "partners": json.dumps(rec.get("partners", [])), "stages": json.dumps(rec.get("stages", [])),
        "industries": json.dumps(rec.get("industries", [])), "geos": json.dumps(rec.get("geos", [])),
        "check_size": rec.get("check_size", ""), "fund": rec.get("fund", ""),
        "portfolio": json.dumps(rec.get("portfolio", [])), "recent": json.dumps(rec.get("recent", [])),
        "thesis": rec.get("thesis", ""), "twitter": rec.get("twitter", ""), "blog": rec.get("blog", ""),
        "preferred_revenue": rec.get("preferred_revenue", ""), "source": rec.get("source", "public-knowledge-seed"),
        "updated_at": now(),
    }
    cols = ",".join(payload.keys())
    qs = ",".join("?" for _ in payload)
    with tx() as c:
        c.execute(f"INSERT OR REPLACE INTO investor_db({cols}) VALUES({qs})", tuple(payload.values()))
    return fid


def counts(company_id: str) -> dict:
    conn = get_conn()
    q = lambda t: conn.execute(f"SELECT COUNT(*) AS n FROM {t} WHERE company_id=?", (company_id,)).fetchone()["n"]
    return {
        "entities": q("entities"),
        "facts": q("facts"),
        "relationships": q("relationships"),
        "timeline": q("timeline"),
        "chunks": q("chunks"),
        "documents": q("documents"),
        "investors": q("investors"),
    }
