# Running the CBO model on Google Colab

Use this when you'd rather run the AI on Colab's free GPU than on your own computer.

## Steps
1. Upload `CBO_Colab_LLM.ipynb` to https://colab.research.google.com (File → Upload notebook).
2. In Colab: **Runtime → Change runtime type → GPU**.
3. Run the cells top to bottom. The second cell prints a **PUBLIC MODEL URL** like
   `https://something.trycloudflare.com`.
4. Open `backend/.env` and set:
   ```
   OLLAMA_BASE_URL=https://something.trycloudflare.com
   ```
5. Tell the assistant "restart the backend" (or restart it yourself). Done — the app now uses Colab's GPU.
6. Check it worked: open `http://127.0.0.1:8000/health` — it should show `"llm":"ollama","llm_active":true`.

## When Colab disconnects (important)
Colab stops the model when you close the tab or after idle time. **This does not break the app.**
The moment the Colab URL is unreachable, the app automatically switches to its built-in grounded
advisor — every page and API still responds with the exact same shape, just with simpler (non-AI)
content. Re-run the notebook, paste the new URL into `.env`, restart, and full AI is back.

So the API is always "the same" whether Colab is up or down — no mock server required.

## Optional: keep a model endpoint alive locally
If you want `/health` to always report an active model even without Colab, you can run the tiny
stand-in server:
```
python -m app.tools.mock_ollama
```
It speaks the same model API on port 11434. Note: it intentionally returns no content, so the app's
built-in advisor produces the actual output — it just keeps the endpoint "present." For real AI
answers, use Colab (or a local Ollama).
