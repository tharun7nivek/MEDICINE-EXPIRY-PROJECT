# MEDICINE-EXPIRY-PROJECT

Monorepo for **MedExpiry** — medicine package MFG/EXP date detection.

| Folder | Role |
|--------|------|
| `AGENTIC_MEDICINE_PROJECT/` | FastAPI + LangGraph YOLO-first detection API |
| `frontend/` | React + Vite UI |

## Quick start

### Backend

```bash
cd AGENTIC_MEDICINE_PROJECT
cp .env.example .env   # then add your API keys
uv sync --group dev
uv run python -m uvicorn src.api.rest.app:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env   # optional; defaults to http://127.0.0.1:8000
npm install
npm run dev
```

## Secrets

- Real keys live only in local `.env` files (gitignored).
- Commit `.env.example` templates only — never paste live keys into source or docs.
- Required backend keys: at least one `OPENROUTER_API_KEY` and one `GROQ_API_KEY`.
  Add `_2`, `_3`, … `_N` (any N) or use `OPENROUTER_API_KEYS` / `GROQ_API_KEYS` CSV lists for rotation.

See `AGENTIC_MEDICINE_PROJECT/README.md` for API details and pipeline docs.
