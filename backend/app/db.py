"""Persistence core.

Default adapter is embedded SQLite (stdlib, zero-install). The schema and access
patterns are written so a Postgres adapter (via DATABASE_URL) is a drop-in: the
same tables, the same `Store` API. Knowledge — not documents — is what's stored,
and every fact carries source, confidence, timestamp, evidence, version, owner.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from typing import Iterator

from .config import settings

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    what TEXT DEFAULT '',
    customers TEXT DEFAULT '',
    stage TEXT DEFAULT '',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(company_id, type, name)
);

CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    type TEXT NOT NULL,
    key TEXT NOT NULL,
    label TEXT NOT NULL,
    value TEXT NOT NULL,
    num REAL,
    entity_id TEXT,
    source_kind TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    evidence TEXT DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0.7,
    version INTEGER NOT NULL DEFAULT 1,
    owner TEXT NOT NULL DEFAULT 'system',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS relationships (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    from_id TEXT NOT NULL,
    to_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    evidence TEXT DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0.7,
    created_at REAL NOT NULL,
    UNIQUE(company_id, from_id, to_id, relation)
);

CREATE TABLE IF NOT EXISTS timeline (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    at REAL NOT NULL,
    connector_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT DEFAULT '',
    who TEXT DEFAULT '[]',
    why TEXT DEFAULT '',
    evidence TEXT DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0.7,
    what_changed TEXT DEFAULT '',
    agents TEXT DEFAULT '[]',
    entity_ids TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS investors (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    firm TEXT NOT NULL,
    partner TEXT DEFAULT '',
    sector TEXT DEFAULT '',
    stage TEXT DEFAULT '',
    geography TEXT DEFAULT '',
    state TEXT NOT NULL DEFAULT 'need-intro',
    warmth REAL NOT NULL DEFAULT 40,
    probability REAL NOT NULL DEFAULT 40,
    last_touch TEXT DEFAULT '',
    concerns TEXT DEFAULT '[]',
    history TEXT DEFAULT '[]',
    sentiment TEXT,
    created_at REAL NOT NULL,
    UNIQUE(company_id, firm)
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    connector_id TEXT NOT NULL DEFAULT 'upload',
    chars INTEGER NOT NULL DEFAULT 0,
    added_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    doc_name TEXT NOT NULL,
    text TEXT NOT NULL,
    embedding TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS connectors (
    company_id TEXT NOT NULL,
    id TEXT NOT NULL,
    connected INTEGER NOT NULL DEFAULT 0,
    last_sync REAL,
    cursor TEXT DEFAULT '',
    record_count INTEGER NOT NULL DEFAULT 0,
    has_credential INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (company_id, id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    at REAL NOT NULL,
    title TEXT NOT NULL,
    detail TEXT DEFAULT '',
    agents TEXT DEFAULT '[]',
    severity TEXT NOT NULL DEFAULT 'medium'
);

CREATE TABLE IF NOT EXISTS credentials (
    company_id TEXT NOT NULL,
    connector_id TEXT NOT NULL,
    token TEXT NOT NULL,
    meta TEXT DEFAULT '{}',
    PRIMARY KEY (company_id, connector_id)
);

CREATE TABLE IF NOT EXISTS interview_log (
    company_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    status TEXT NOT NULL,
    at REAL NOT NULL,
    PRIMARY KEY (company_id, question_id)
);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    title TEXT DEFAULT '',
    content TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    investor_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'drafted',
    subject TEXT DEFAULT '',
    body TEXT DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(company_id, investor_id)
);

CREATE TABLE IF NOT EXISTS investor_db (
    id TEXT PRIMARY KEY,
    firm TEXT NOT NULL,
    partners TEXT DEFAULT '[]',
    stages TEXT DEFAULT '[]',
    industries TEXT DEFAULT '[]',
    geos TEXT DEFAULT '[]',
    check_size TEXT DEFAULT '',
    fund TEXT DEFAULT '',
    portfolio TEXT DEFAULT '[]',
    recent TEXT DEFAULT '[]',
    thesis TEXT DEFAULT '',
    twitter TEXT DEFAULT '',
    blog TEXT DEFAULT '',
    preferred_revenue TEXT DEFAULT '',
    source TEXT DEFAULT 'public-knowledge-seed',
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_investordb_firm ON investor_db(firm);

CREATE INDEX IF NOT EXISTS idx_facts_company ON facts(company_id);
CREATE INDEX IF NOT EXISTS idx_entities_company ON entities(company_id);
CREATE INDEX IF NOT EXISTS idx_rel_company ON relationships(company_id);
CREATE INDEX IF NOT EXISTS idx_timeline_company ON timeline(company_id, at DESC);
CREATE INDEX IF NOT EXISTS idx_chunks_company ON chunks(company_id);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.sqlite_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = _connect()
        _local.conn = conn
    return conn


@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db() -> None:
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
