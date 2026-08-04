# Agentic Medicine — Date Detection API

YOLO-first LangGraph pipeline that reads MFG/EXP dates from medicine package photos,
then returns a deterministic **expired / not expired** assessment for the MedExpiry UI.

**Pipeline:** YOLO crop → dual `qwen/qwen3.6-27b` (Groq) crop readers → optional
`nemotron-3-nano-omni` reflection (OpenRouter) → `pack_date_parser` validate →
`ExpiryAssessment` embedded on the response.

## Quick start

```bash
# Install (uv)
uv sync --group dev

# Required env — copy .env.example → .env (never commit .env)
# OPENROUTER_API_KEY[+ _2…N] and GROQ_API_KEY[+ _2…N] — any count works
# Optional: STORAGE_DIR, CORS_ORIGINS, RETAIN_DETECT_TEMPS

# Windows tip: if `uv run uvicorn` fails with a trampoline path error (spaces in
# the folder name), use the module form below.
uv run python -m uvicorn src.api.rest.app:app --host 0.0.0.0 --port 8000
```

Frontend (sibling repo folder `../frontend`):

```bash
cd ../frontend
npm install
npm run dev   # http://localhost:5173 — VITE_API_URL defaults to http://127.0.0.1:8000
```

## API (v1)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/` | Discovery |
| `GET` | `/api/v1/health` | YOLO + key pool readiness |
| `POST` | `/api/v1/detect` | Multipart `file` → dates + `assessment` + pipeline metadata |
| `POST` | `/api/v1/assess` | JSON MFG/EXP → deterministic expiry assessment only |

Example:

```bash
curl -s http://127.0.0.1:8000/api/v1/health
curl -s -F "file=@tests/fixtures/images/output_0.png" \
  http://127.0.0.1:8000/api/v1/detect
curl -s -X POST http://127.0.0.1:8000/api/v1/assess \
  -H "Content-Type: application/json" \
  -d "{\"final_mfg\":\"APR.2024\",\"final_exp\":\"MAR.2027\",\"status\":\"accepted\"}"
```

`DetectResponse.assessment` includes `expiry_status` (`valid` \| `expired` \| `unknown`),
`is_expired`, and `needs_human_review`. The frontend displays these fields directly
(no client-side date math).

## Layout

```
src/api/                 FastAPI app + LangGraph nodes
  rest/app.py            lifespan, CORS, /api/v1 router
  control/agents/approach_b/   crop_zoom, readers, consensus, reflection, validate
  core/services/         detect + expiry assessment + graph
  utils/pack_date_parser.py    shared date formats / month-end validity
  utils/yolo/best.pt     required YOLO weights
docs/                    production design + system guide
tests/                   unit + optional e2e
tests/fixtures/images/   sample package photos
storage/                 temp uploads/crops (gitignored)
```

## Tests

```bash
uv run python -m pytest          # unit tests always
# e2e detect skips unless OPENROUTER + GROQ keys are set
```

## Docs

- [Current production design](docs/yolo_first_v2.md) — YOLO-first graph, assessment API, frontend
- [System guide](docs/MedExpiry_System_Guide.docx) — end-user / architecture walkthrough
