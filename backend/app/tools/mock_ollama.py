"""Optional stand-in model endpoint.

Speaks the same model API (`/api/tags`, `/api/chat`) as Ollama on port 11434, so
the app keeps working with the identical API when a real model (local or Colab)
isn't running. It returns no content on purpose — the app's own grounded
built-in advisor then produces the actual output. This just keeps the endpoint
"present" (e.g. so `/health` reports a model). For real AI answers, run Ollama
locally or via Colab (see colab/README.md).

Run from the backend directory:
    python -m app.tools.mock_ollama
"""
from __future__ import annotations

from fastapi import FastAPI, Request

app = FastAPI(title="CBO mock model endpoint")


@app.get("/api/tags")
def tags():
    return {"models": [{"name": "mock:latest"}]}


@app.post("/api/chat")
async def chat(req: Request):
    await req.json()
    return {"message": {"role": "assistant", "content": ""}}


def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=11434)


if __name__ == "__main__":
    main()
