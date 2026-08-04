# Design Doc — MedExpiry (current production)

**Status:** production (API `1.0.0`)  
**Last updated:** August 2026  

This is the source-of-truth design for the current MedExpiry build
(YOLO-first localization → dual crop readers → optional reflection → deterministic validation).

**Repos**

| Area | Location |
|------|----------|
| Backend API | `AGENTIC_MEDICINE_PROJECT/` |
| Frontend UI | `frontend/` (Vite + React, brand **MedExpiry**) |

---

## 1. Goals

1. Read manufacturing (MFG) and expiry (EXP) dates from a medicine pack photo.
2. Cross-check with two independent VLM crop readers; adjudicate only when needed.
3. Never let an LLM be the last word on validity — deterministic parse + calendar checks.
4. Return an explicit **expired / not expired / unknown** verdict and a separate **human-review** flag for the UI and TTS.
5. Support multilingual UI + browser speech (no server TTS).

---

## 2. End-to-end architecture

```mermaid
flowchart LR
  UI["MedExpiry frontend<br/>Vite / React / i18n / Web Speech"]
  API["FastAPI /api/v1<br/>port 8000"]
  Graph["LangGraph Approach B<br/>YOLO-first"]
  Assess["ExpiryAssessmentService<br/>pack_date_parser"]

  UI -->|"POST /detect multipart file"| API
  API --> Graph
  Graph -->|"final_mfg / final_exp / status"| Assess
  Assess -->|"DetectResponse.assessment"| API
  API --> UI
  UI -->|"Listen / Stop"| Speech["speechSynthesis"]
```

**Request flow (frontend):** Component → `useDetect` → `detectService` → axios (`timeout` 300000 ms) → `POST /api/v1/detect`.  
The UI **does not** parse dates or decide expiry; it displays `result.assessment.*` only.

---

## 3. LangGraph pipeline (Approach B — YOLO-first)

**Code:** `src/api/core/services/date_detection_graph.py`  
**`model_pipeline`:** `approach_b_yolo_first`

```mermaid
flowchart TD
  START([image input]) --> CZ["crop_zoom<br/>YOLO + OpenCV"]
  CZ --> FR["first_read<br/>qwen/qwen3.6-27b @ Groq"]
  FR --> SR["second_read<br/>qwen/qwen3.6-27b @ Groq"]
  SR --> CC{"consensus_check<br/>deterministic"}
  CC -->|match| VAL["validate<br/>pack_date_parser"]
  CC -->|mismatch / low_confidence| REF["reflection<br/>nemotron-3-nano-omni @ OpenRouter"]
  REF --> VAL
  VAL -->|pass| OK([status: accepted])
  VAL -->|fail| HR([status: human_review])
```

### 3.1 State (`DateDetectionState`)

Defined in `src/api/schemas/date_detection_state.py`:

| Field | Role |
|-------|------|
| `image_path`, `image_b64`, `attempt` | Inputs |
| `bbox_2d` | `[x1,y1,x2,y2]` from YOLO union rect (or full image on fallback) |
| `crop_path`, `crop_source` | Crop artifact; `yolo` \| `full_image_fallback` |
| `first_result`, `second_result` | Reader JSON (raw dates + confidence) |
| `consensus_status` | `match` \| `mismatch` \| `low_confidence` |
| `reflection_result` | Present only if reflection ran |
| `final_mfg`, `final_exp` | Chosen strings after consensus/reflection |
| `validation` | Boolean checks from `validate` |
| `status` | `accepted` \| `human_review` |

There is **no** `ground_and_read` / `ground_result` — localization is YOLO-only.

### 3.2 Node summary

| Node | Type | Implementation | Notes |
|------|------|----------------|-------|
| `crop_zoom` | Deterministic | `crop_zoom_node.py` | YOLO `best.pt`; 15% pad; min crop width **500**; miss → full-image fallback |
| `first_read` | VLM | `first_read_node.py` | Crop only; does not see second reader |
| `second_read` | VLM | `second_read_node.py` | Crop only; independent of first answer |
| `consensus_check` | Deterministic | `consensus_check_node.py` | Normalize + compare; low confidence → reflection; **label-prefix guard** (see below) |
| `reflection` | VLM | `reflection_node.py` | Runs on mismatch / low confidence only |
| `validate` | Deterministic | `validate_node.py` | Shared `pack_date_parser`; sets `validation` + `status` |

### 3.3 Model pins

From `src/api/http_clients/key_pool.py`:

| Stage | Model ID | Provider |
|-------|----------|----------|
| `first_read` / `second_read` | `qwen/qwen3.6-27b` (`QWEN36_GROQ`) | Groq |
| `reflection` | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` (`OMNI30B`) | OpenRouter |

Emergency / alternate entry in `MODEL_SPECS`: `nvidia/nemotron-nano-12b-v2-vl:free` (not the primary path).

Keys: round-robin pools — `OPENROUTER_API_KEY` (+ `_2`…`_4`), `GROQ_API_KEY` (+ `_2`…`_10`). Retries on 429 with short backoff.

### 3.4 Localization (YOLO)

- Weights: `src/api/utils/yolo/best.pt` (required at API startup).
- Classes: date-region segmentation (`MFD_DATE` / `mfddatexp`); union mask → bbox + padding.
- YOLO miss → `crop_source=full_image_fallback`, crop = full image, `bbox_2d=[0,0,w,h]`.
- VLMs never propose `bbox_2d`.

### 3.5 Consensus rules

1. Normalize strings (trim, upper, collapse spaces / double dashes).
2. **Match** (high confidence) → set `final_*` from reader A → `validate`.
3. **Match but any `low` confidence** → `low_confidence` → `reflection`.
4. **Mismatch** → `reflection`.
5. **Label-prefix guard:** if reader B returns label-only text (no `\d{2}` run) while A has numeric dates, treat as match from A and skip reflection (avoids OCR “EXP.” / “MFG” litter).

### 3.6 Validate pass conditions

Uses `src/api/utils/pack_date_parser.py` (same parser as assessment):

| Check | Meaning |
|-------|---------|
| `exp_parsed` | EXP matches a known pack format |
| `exp_in_future` | Today ≤ last valid day for EXP (month-only → end of month) |
| `exp_after_mfg` | If MFG parsed: EXP valid-through ≥ MFG date |
| `reflection_unresolved` | Must be false |

**Accept** iff EXP parsed ∧ not expired ∧ (no MFG or EXP after MFG) ∧ not reflection-unresolved.  
Else `status = human_review`.

---

## 4. Date parsing & expiry assessment

### 4.1 Pack date formats

`pack_date_parser.py` accepts (non-exhaustive):

- Month precision: `YYYY-MM`, `YYYY/MM`, `MM/YYYY`, `MM-YYYY`, `MM.YYYY`, `APR.2024`, `MAR 2027`, `AUG2024`, `MARCH 2027`, `YYYYMM`
- Day precision: `YYYY-MM-DD`, `DD-MM-YYYY`, `DD/MM/YYYY`, `DD.MM.YYYY`, `15 AUG 2024`, `15-AUG-2024`, `AUG 15, 2024`, `YYYYMMDD`, `DDMMYYYY`

Month-precision dates remain valid through the **last calendar day** of that month.

### 4.2 `ExpiryAssessmentService`

**Code:** `src/api/core/services/expiry_assessment_service.py`  
**Schema:** `src/api/schemas/expiry_assessment.py`

Embedded on every detect response; also available standalone.

| Field | Meaning |
|-------|---------|
| `expiry_status` | `valid` (not expired) \| `expired` \| `unknown` |
| `is_expired` | `true` / `false` / `null` |
| `needs_human_review` | Pipeline `status == human_review` **or** EXP unparsed |
| `mfg_parsed` / `exp_parsed` | Parse success |
| `mfg_iso` / `exp_iso` | Normalized ISO dates |
| `exp_valid_through` | Last valid day (ISO) |
| `exp_precision` | `day` \| `month` |

**Important:** Expired vs not-expired is independent of human-review. The UI shows both.

---

## 5. Public API

**App:** `src/api/rest/app.py` — CORS from `CORS_ORIGINS` (default `*`), lifespan loads YOLO + key pools.  
**Router:** `src/api/rest/routes/detect_route.py` under `/api/v1`.

| Method | Path | Body | Response |
|--------|------|------|----------|
| `GET` | `/api/v1/` | — | Discovery (`health`, `detect`, `assess`) |
| `GET` | `/api/v1/health` | — | YOLO loaded, key counts, storage dir |
| `POST` | `/api/v1/detect` | multipart `file` | `DetectResponse` (+ `assessment`) |
| `POST` | `/api/v1/assess` | JSON `{ final_mfg?, final_exp?, status? }` | `AssessResponse` |

Allowed upload types: JPEG, PNG, WebP, BMP (plus `application/octet-stream`).

### 5.1 `DetectResponse` (high level)

```
status, final_mfg, final_exp, consensus_status, validation,
assessment,          ← ExpiryAssessment (always present)
bbox_2d, crop_source, crop_path, models_used,
first_result, second_result, reflection_result,
request_id, elapsed_ms, model_pipeline
```

Legacy routes `/detect` and `/detect-zero-shot` (outside `/api/v1`) are **removed**.

---

## 6. Frontend (MedExpiry)

**Stack:** Vite 8, React 19, TypeScript, Tailwind 4, axios, react-router-dom 7, i18next, lucide-react, react-hot-toast.

| Route | Page |
|-------|------|
| `/` | Landing |
| `/detect` | Upload → analyze → result + Listen / Stop |
| `*` | Redirect home |

**i18n:** `en`, `hi`, `ta`, `te`, `mr`, `bn`, `gu`, `kn`, `ml`, `pa` (persisted in `localStorage`).  
**TTS:** Web Speech API only (`useSpeech`); language tags like `en-IN`, `hi-IN`. Stop cancels `speechSynthesis`.  
**API base:** `VITE_API_URL` → default `http://127.0.0.1:8000`; axios timeout **5 minutes**.

Result card uses:

- `assessment.expiry_status` → Not expired / Expired / Unable to determine  
- `assessment.needs_human_review` → review chip  
- `consensus_status` → secondary “Models agree / …” copy  

---

## 7. Runbook

```bash
# Backend
cd AGENTIC_MEDICINE_PROJECT
uv sync --group dev
# On Windows paths with spaces, prefer:
uv run python -m uvicorn src.api.rest.app:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm run dev   # http://localhost:5173
```

**Env (backend):** at least one `OPENROUTER_API_KEY` and one `GROQ_API_KEY`; add `_2…N` (any count) or CSV `*_API_KEYS` for rotation. Optional `STORAGE_DIR`, `CORS_ORIGINS`, `RETAIN_DETECT_TEMPS`.  
**Env (frontend):** `VITE_API_URL=http://127.0.0.1:8000`.

**Tests:** `uv run python -m pytest` (unit always; e2e detect needs keys).

---

## 8. Pipeline summary

| Stage | Implementation |
|-------|----------------|
| Localization | **YOLO-first** (`best.pt` segmentation) |
| Dual readers | Dual **`qwen/qwen3.6-27b`** (Groq) |
| Reflection | **`nemotron-3-nano-omni`** (OpenRouter), on disagreement / low confidence |
| Validate | **`pack_date_parser`** + month-end calendar checks |
| Client verdict | **`assessment`** on detect + **`POST /assess`** |
| Frontend | MedExpiry UI, 10 languages, Web Speech |

Intentional design: independent dual crop reads, low-confidence → reflection, unresolved reflection → human review, deterministic validate as last gate, round-robin key pools.
