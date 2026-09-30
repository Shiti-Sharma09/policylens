# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## What this is

**PolicyLens** — an AI assistant for Indian vehicle insurance. Users upload a policy PDF and ask questions; answers are grounded in the policy's own text with citations. Planned: damage-photo analysis, policy comparison/gap analysis, claim checklists, claim-vs-pay estimates.

It is a **local-first, single-user** system: no cloud LLM required, no deployment target, zero recurring cost.

## Current status

| Area | State |
|---|---|
| Auth (register/login/me, bcrypt + JWT) | Done |
| PDF upload → encrypt → extract → section-aware chunk | Done |
| Embeddings + Qdrant retrieval (`/ask/retrieve`) | Done |
| RAG answers (`/ask`, `/ask/stream` SSE) + SQLite answer cache | Done |
| Frontend: login, register, upload, chat | Done |
| Policy comparison + gap analysis (`compare`) | **Stub — next** |
| Damage classification (`damage`, `yolo`, `fraud_signals`) | Stub |
| Tool-calling agent (`agent`, `claim_advisor`) | Stub |

Stub modules only expose `GET /<name>/ping` or are empty files. Don't assume they contain logic — read the file first.

## Commands

Prerequisites: Python 3.12, Node 18+, Docker, Ollama with `qwen3:8b` and `qwen3-embedding:0.6b` pulled.

```bash
# Vector DB (must be running before the backend starts)
docker compose up -d

# Backend (from backend/)
python -m venv .venv && .venv\Scripts\activate     # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                               # then fill JWT_SECRET_KEY and FILE_ENCRYPTION_KEY
uvicorn app.main:app --reload --port 8000          # Swagger UI at /docs, health at /health

# Seed the 8 IRDAI reference policies, then index anything not yet embedded (from backend/)
python -m scripts.seed_reference_policies          # idempotent
python -m scripts.backfill_embeddings              # idempotent; indexes Policy rows with indexed_at IS NULL

# Frontend (from frontend/)
npm install
npm run dev                                        # http://localhost:3000
npm run lint
```

- There is no test suite yet. Verify changes against the running app (Swagger UI for the API, the `/chat` page for RAG) and against a **real question** — see "Retrieval" below for why.
- Generate `FILE_ENCRYPTION_KEY` with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
- Full indexing of one policy takes 3–5 minutes on CPU; don't wait on it in a request handler.

## Architecture

```
Next.js (App Router) ──HTTP/SSE──▶ FastAPI ──▶ Ollama   (qwen3:8b chat, qwen3-embedding:0.6b)
                                      │   ──▶ Qdrant   (vectors + chunk text, collection `policy_chunks`)
                                      └──▶ SQLite     (users, policies, chunk metadata, answer cache, claims)
                                           + encrypted PDFs in backend/storage/policies/
```

### Request flow (implemented)

1. **Upload** (`routers/upload.py`): validate PDF → Fernet-encrypt to `storage/policies/*.pdf.enc` → extract text in memory (`pdf_extraction.py`) → section-aware chunking (`chunking.py`) → stage chunk text as JSON (`chunk_store.py`) → kick off a `BackgroundTasks` job that embeds + upserts to Qdrant (`indexing.py`) and sets `Policy.indexed_at`.
2. **Ask** (`routers/ask.py` → `services/rag.py`): check `AnswerCache` → `retrieve_chunks()` (Qdrant top-k, filtered by `policy_id`) → grounded prompt → `llm.py` (Ollama `/api/chat`) → append fixed disclaimer → cache → return with citations. `/ask/stream` does the same as Server-Sent Events.
3. **Frontend** (`src/lib/api.ts`): fetch wrapper with JWT in `localStorage`; `askQuestionStream()` reads the SSE stream via `fetch` + `ReadableStream` (`EventSource` can't send `Authorization` headers or a POST body).

### Backend layout (`backend/app/`)

- `main.py` — app, CORS, lifespan (`init_db()`, Qdrant client, `ensure_collection()`); mounts all routers.
- `config.py` — `pydantic-settings`, loads `.env`. `db.py` — SQLite engine, `init_db`, `get_session`.
- `security.py` — bcrypt hashing + JWT. `dependencies.py` — `get_current_user` (`HTTPBearer`).
- `models/models.py` — `User`, `Policy`, `PolicyChunkMeta`, `AnswerCache`, `Claim`.
- `services/` — one module per concern: `file_storage`, `pdf_extraction`, `chunking`, `chunk_store`, `embeddings`, `vectorstore`, `indexing`, `llm`, `rag`, `policy_metadata` (tenure detection), `uin_validation` (IRDAI UIN format check). Stubs: `comparison`, `yolo`, `fraud_signals`, `claim_advisor`, `agent`.
- `scripts/` — `seed_reference_policies.py`, `backfill_embeddings.py`.

### Data

- `data/irdai_policies/` — 8 real IRDAI-filed policy wordings (HDFC ERGO and ICICI Lombard × comprehensive, third-party-only, two-wheeler, two-wheeler standalone-own-damage). They seed as `is_reference_doc=True` and serve both as RAG test data and as the reference library for gap analysis.
- `data/damage_dataset/` — large Roboflow car-damage dataset for the planned vision work; gitignored.
- Runtime state (`backend/policylens.db`, `backend/storage/`) is gitignored. Never commit it or `.env`.

## Hard rules and non-obvious constraints

These each came from a measured failure or an explicit product decision. Don't undo them without re-measuring.

### LLM

- **Always call Qwen3 with `think: false`.** Default thinking mode took 27+ minutes for one answer versus ~20s with it off. This applies to every call in `llm.py`, `rag.py`, `embeddings.py`, and any future agent code.
- **CPU-only latency is real.** Generation runs at ~2–3 tok/s; a real RAG answer (5 chunks, ~1900 prompt tokens) takes ~130–230s. `llm.py`'s timeout is 300s so answers aren't cut mid-generation. UI must show progress (the chat page streams tokens and shows an elapsed counter), never assume "a few seconds".
- **The answer cache is the main latency lever** (repeat question: minutes → ~50ms). Keyed by `(policy_id, sha256(normalized question))`.
- **Qwen3-4B and a llama.cpp/GGUF swap were evaluated and rejected.** 4B rambles without reaching an answer even with `think:false`; Ollama already runs llama.cpp internally (`qwen3:8b` is `Q4_K_M`), so swapping the wrapper doesn't change the CPU bottleneck.

### Retrieval

- **Embed chunks with their section heading prepended** (`f"{section_hint}\n\n{chunk_text}"`), but store heading-free `chunk_text` in the payload. Without the heading, the correct chunk for "what is covered under third party liability" ranked *below* an irrelevant one (0.478 vs 0.485); with it, it moved from rank 10 to rank 2.
- **Always validate retrieval against a real question** before trusting a pipeline change — a plausible-looking pipeline can still rank the right answer under noise.
- **Embedding is ~3s/chunk.** A single `/api/embed` call for all chunks of a policy timed out; `embeddings.py` batches 16 per call. Indexing must stay in a background task.
- Qdrant collection: `policy_chunks`, **1024-dim**, Cosine. Payload: `policy_id`, `chunk_index`, `chunk_text`, `section_hint`, `insurer`, `structural_type`. Point IDs are UUIDs pre-assigned at chunk time (`PolicyChunkMeta.qdrant_point_id`).
- `POST /ask/retrieve` and `/ask` return **409** if the policy isn't indexed yet, rather than silently returning nothing.

### Ingestion

- **Chunking rules are code, not LLM-invented.** `chunking.py` detects ALL-CAPS heading lines, groups lines under the latest heading, then packs each section to ~2000 chars with 200-char overlap (overlap never crosses a section). It's a heuristic: it occasionally splits on a table header, which adds an extra correctly-labeled chunk rather than a wrong one.
- **`pdf_extraction.py` strips repeated headers/footers** — any line appearing verbatim on ≥30% of pages. Detected by frequency, not a hardcoded string, so it generalizes across insurers.
- **Uploaded PDFs are encrypted at rest** (Fernet, key in `.env`). Text is decrypted only in memory.
- `Policy.file_path` records each encrypted PDF so cleanup can find it; policies created before it existed aren't backfilled.
- `Policy.tenure_years` is only set when the wording states a duration (3 of the 8 reference PDFs do). `policy_metadata.detect_tenure_years()` is a tightly-scoped regex over the title area — don't broaden it (HDFC's "Exceeding 3 years…" is vehicle age, not tenure). Comparisons must not treat policies of different tenure as directly comparable on premium.
- New reference PDFs: run `extract_uin()` / `validate_uin_format()` (structural check only — no public IRDAI API exists) and still cross-check the UIN against IRDAI's published product list. Source PDFs from `irdai.gov.in`; some insurer sites block non-browser downloads.

### Auth

- **`bcrypt` directly, not `passlib`** — `passlib` 1.7.4 is unmaintained and crashes against `bcrypt>=4.1`.
- **`HTTPBearer`, not `OAuth2PasswordBearer`** — login takes a JSON body, so Swagger gets a plain "paste your token" box.

### Product framing (non-negotiable)

- **Never produce claim-approval language.** Every advisory feature (coverage reasoning, claim-vs-pay, fraud signals) is framed as guidance and defers final say to the insurer.
- **The advisory disclaimer is appended in code** by `rag.generate_answer()`, not left to the model — the model omitted it on an ordinary question even when prompted. Apply the same principle to any future safety framing.
- **Claim checklists must be sourced from the actual policy/insurer text**, not invented by the LLM.
- **Reuse before adding a subsystem.** Comparison, gap analysis, and renewal diff are meant to share one structured-extraction + comparison pipeline.
- **Local-first, not local-only.** A hosted API with a workable free tier may replace a model case by case (planned: try Groq's vision API for damage classification, fall back to a fine-tuned YOLOv8n on CPU). Never make a paid tier required, and keep a local fallback path so the demo can't be throttled away.

## Frontend notes

- **Next.js 16.3 / React 19** — newer than most training data. `frontend/AGENTS.md` points to `frontend/node_modules/next/dist/docs/`; check those docs before relying on remembered APIs beyond basic Server/Client Components.
- Pages use `"use client"` + `useEffect` for data fetching; env vars need the `NEXT_PUBLIC_` prefix (`NEXT_PUBLIC_API_URL` in `frontend/.env.local`).
- **`GET /upload/policies` must be fetched with `cache: "no-store"`.** Otherwise the browser serves a stale response and a policy appears stuck on "indexing…" forever. The chat page also polls every 15s while any policy is indexing.
- Un-indexed policies are disabled in the chat dropdown rather than failing on ask.

## Git workflow

- `main` is branch-protected (PR required, admins included). **Never commit or push directly to `main`** — `git push origin main` fails with `GH006`, by design.
- One feature branch per task (e.g. `day5-policy-comparison`) → push → `gh pr create` → merge once verified locally.
- Commit and PR descriptions explain *why*, not just what; existing history is a good style reference.
- Don't leave dev servers running in the background; give the user the commands to run instead.

## Environment gotchas (Windows)

- A plain `<tool> --version` on PATH is **not** reliable for deciding a tool is missing — a fresh install doesn't reach already-running shells. This project has been wrong about `python`, `gh`, and `docker` this way. Also check Program Files and the uninstall registry before concluding something isn't installed.
- The backend venv lives at `backend/.venv/` (gitignored).
