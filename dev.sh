#!/usr/bin/env bash
# Runs the CBO backend (FastAPI) and frontend (Next.js) together.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

# Backend
if [ ! -d "$ROOT/backend/.venv" ]; then
  python3 -m venv "$ROOT/backend/.venv"
  "$ROOT/backend/.venv/bin/pip" install -q -r "$ROOT/backend/requirements.txt"
fi
"$ROOT/backend/.venv/bin/python" -m uvicorn app.main:app --port 8000 --app-dir "$ROOT/backend" &
BACK=$!

# Frontend
(cd "$ROOT" && npm run dev) &
FRONT=$!

trap "kill $BACK $FRONT 2>/dev/null" EXIT
echo "Backend  → http://127.0.0.1:8000"
echo "Frontend → http://localhost:3000"
wait
