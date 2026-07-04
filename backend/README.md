# CBO Backend — AI Business Operating System

FastAPI service that owns **all** business logic. The Next.js frontend is a thin
client; nothing in the UI exists unless it comes from here.

## What's real

- **Company Memory** (`memory.py` + `db.py`): entities, facts, relationships,
  timeline, investors, vectors. Every fact carries source, confidence,
  timestamp, evidence, **version**, and **owner**. Knowledge is stored — never
  raw documents.
- **Universal Connector Framework** (`connectors.py`): every connector implements
  `connect → sync → extract → normalize → createEntities → createRelationships →
  updateKnowledgeGraph → indexVectors → publishEvents`. Adding an integration is
  one `sync()`.
- **Real ingestion**: manual uploads parse **real** PDF/DOCX/XLSX/CSV/TXT/MD
  (`files.py`). API connectors (GitHub, Gmail, Calendar, Drive, Notion, Slack,
  Stripe) call the real APIs with a provided token and sync incrementally via a
  cursor. **No credential → no sync → no fabricated data.**
- **Brain RAG** (`ai.py`): answers ONLY from memory (vector + fact retrieval),
  returns answer + confidence + sources + connected memories, and says **"I don't
  know"** when evidence is insufficient.
- **Executive Council** (`ai.py`): planner → 8 agents reason from memory → debate
  → consensus → governance.
- **Morning Brief** (`ai.py`): generated live from memory every request.
- **Investor intelligence**: investor objects with warmth/probability/timeline,
  next best action, meeting prep, drafted follow-ups, and meeting debriefs that
  write back to memory.

## Adapters (12-factor, swap via env)

Defaults are embedded so it runs with zero infra:
- Storage: **SQLite** (stdlib) → set `DATABASE_URL` for Postgres.
- Vectors: in-process hashing embeddings + cosine → set `QDRANT_URL`.
- Graph: SQL relationships table → set `NEO4J_URL`.
- AI: grounded local reasoner → set `LLM_PROVIDER=openai|anthropic` + key to use a
  real model over the same retrieved context (still no hallucination).

See `.env.example`.

## Run

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health: `GET http://127.0.0.1:8000/health`. Interactive docs: `/docs`.

## Key endpoints

```
POST /onboarding/start                         {name} -> company
POST /onboarding/answer                         {company_id,key,text}
GET  /companies/{id}/brief
POST /companies/{id}/brain/ask                  {query}
GET  /companies/{id}/graph | /facts | /timeline | /counts
GET  /companies/{id}/connectors
POST /companies/{id}/connectors/{cid}/connect   {token?}
POST /companies/{id}/connectors/{cid}/sync
POST /companies/{id}/ingest/upload              (multipart file)
POST /companies/{id}/ingest/text                {name,text}
POST /companies/{id}/council/ask                {question}
GET  /companies/{id}/investors | /investors/{iid}
POST /companies/{id}/investors/{iid}/debrief    {notes}
```
