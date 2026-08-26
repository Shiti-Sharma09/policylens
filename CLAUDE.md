# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status: Day 1 Complete

Day 0 (prep) and Day 1 (FastAPI + Next.js + SQLite + embedded Qdrant scaffolding) are done — see `PROGRESS.md`. `backend/` and `frontend/` exist and run locally (`/health` round trip verified). All routers (`auth`, `upload`, `ask`, `compare`, `damage`, `agent`) and services (`rag`, `embeddings`, `yolo`, `comparison`, `fraud_signals`, `claim_advisor`, `agent`) are stubs only — no real logic yet. Day 2 (auth + PDF ingestion) is next. Check `PROGRESS.md`'s status table before assuming any later day's work exists.

**Local dev environment note:** this machine has no Docker installed — Qdrant runs in `qdrant-client`'s embedded local mode instead (see Vector DB decision below). Python 3.12 was installed via winget after Day 0's original assumption of "already available" turned out wrong; the backend venv lives at `backend/.venv/` (gitignored).

The planning docs, in reading order:
- **`suggestions.md`** — the **what/why**: every technology decision (LLM, embeddings, DB, vision model, auth) with reasoning. Read this first to understand *why* a choice was made before changing it.
- **`PLAN.md`** — the **how/when**: day-by-day execution plan (Day 0–10) with concrete setup steps and "done" criteria for each day. This is the primary task list to work from.
- **`PROGRESS.md`** — status tracker mirroring `PLAN.md`'s structure; update the Status column (`Pending` → `In Progress` → `Done`/`Blocked`) as work completes. Currently only Day 0 (prep) is marked Done.
- **`questions_for_shiti.txt`** — an early clarifying-questions Q&A that shaped the plan. **Superseded** by `suggestions.md`/`PLAN.md` — don't treat it as current spec (e.g. it floats Gemini/GPT-4V and multi-format OCR, both later ruled out in favor of fully local models and a fixed 6-document reference set).
- **`requirements.txt`** — despite the filename, this is *not* a pip requirements file. It's the original project-idea writeup (problem statement + feature brainstorm) that `suggestions.md` responds to. A real Python `requirements.txt` will need to be created under `backend/` once scaffolding starts.

## The Project: PolicyLens

An AI-powered vehicle insurance assistant (working name **PolicyLens**, repo/folder currently named `Vcure`) for the Indian market: users upload their insurance policy PDF and/or a photo of vehicle damage, and get policy-grounded answers about coverage, exclusions, and claim guidance — never a claim-approval verdict, only advisory reasoning ("this appears to fall under your own-damage coverage; final approval depends on the insurer").

Built as a **fully local, single-user, zero-recurring-cost** system — no cloud LLM APIs, no deployment. Runway: 1–2 weeks part-time (~10 sessions).

### Core flow

```
User (email+password login) → Upload Insurance PDF(s) → Extract & Structure Policy →
Ask Questions (RAG) OR Compare 2+ Policies OR Upload Damage Photo →
Agent orchestrates: retrieval / vision / comparison / checklist / claim-vs-pay →
Grounded answer with citations + risk flags where relevant
```

### Planned architecture (from `suggestions.md` §3)

```
Next.js + Tailwind frontend (local, email+password login)
        │ localhost API calls
FastAPI backend
  → verifies bcrypt password hash → issues JWT
  → single tool-calling agent (Qwen3-8B via Ollama) routes each request to:
       retrieve_policy_sections | classify_damage | compare_policies |
       generate_claim_checklist | estimate_claim_vs_deductible | check_fraud_signals
  → RAG (Qdrant + Qwen3-Embedding-0.6B) | YOLO (fine-tuned, CPU inference) |
    comparison engine (structured + LLM narrative) | fraud signals (pHash/EXIF/ELA — flags, not verdicts)
        │
   Qdrant (vectors) · SQLite (users, policies, claims) · local encrypted file store (PDFs, photos)
```

**Key technology decisions** (each argued for in `suggestions.md` §0/§2 — read there before overriding):
- **LLM:** Qwen3-8B via Ollama, CPU inference, `localhost:11434`. Chosen for native tool-calling support (confirmed working by direct test) at a CPU-runnable size — not a cloud API. **Always call with `think: false`** — Qwen3's default thinking mode was measured taking 27+ minutes for one answer versus ~20s with it disabled; this is a hard requirement for any code in `app/services/rag.py`/`embeddings.py`/`agent.py`, not optional. Real measured throughput on this machine is ~2-6 tok/s (not the ~15-30 tok/s generic figure `suggestions.md` originally assumed before Day 1 hardware validation) — expect ~20-90s per RAG/agent turn, and build a loading/progress UI state around that, not a "few seconds" assumption.
- **Embeddings:** Qwen3-Embedding-0.6B via Ollama, **1024-dim** (confirmed empirically via `/api/embed`, not just assumed) — use this exact number for the Qdrant collection's vector size in Day 3.
- **Vector DB:** Qdrant, running in `qdrant-client`'s **embedded local mode** (in-process, on-disk at `backend/qdrant_data/`, gitignored) — revised from the original "Docker Compose" plan during Day 1 execution because Docker isn't installed on this machine. Same Qdrant API either way; see `suggestions.md`'s Vector DB section for the tradeoff (single-process file lock — don't run two backend instances against the same path at once).
- **App DB:** SQLite, not Postgres — single user, single writer, zero-config, one-file portability.
- **Vision:** YOLOv8n/v11n, fine-tuned (not stock COCO weights — COCO has no dent/scratch/windshield-crack classes) on a public Roboflow car-damage dataset via free Kaggle GPU hours; inference runs locally on CPU.
- **Auth:** self-rolled email+password (bcrypt + JWT), not Firebase phone-OTP — dropped because Firebase now requires a paid Blaze plan with a card on file for phone auth.
- **Frontend:** Next.js + Tailwind, run via `next dev` — no deployment target for this build.
- **Data:** 6 real IRDAI-filed policy wordings (2 insurers × {comprehensive, third-party-only, two-wheeler}) in `data/irdai_policies/` — these double as RAG test data *and* the gap-analysis reference library. Not synthetic, not scraped insurer marketing pages — the actual regulator-filed wordings.

### Repo structure (current, as of Day 1)

```
backend/
  .venv/                     (Python 3.12 venv, gitignored)
  app/
    main.py                  (FastAPI app, CORS, lifespan init_db + get_qdrant_client)
    config.py                (pydantic-settings, loads .env)
    db.py                    (SQLite engine + init_db/get_session)
    routers/                 (auth, upload, ask, compare, damage, agent — /ping stubs only)
    services/                (rag.py, embeddings.py, yolo.py, comparison.py, fraud_signals.py,
                               claim_advisor.py, agent.py — empty modules, no logic yet)
    models/models.py         (SQLModel: User, Policy, PolicyChunkMeta, Claim)
  qdrant_data/               (embedded Qdrant on-disk storage, gitignored)
  policylens.db              (SQLite, gitignored)
  requirements.txt
  .env / .env.example
frontend/                    (Next.js 16 + TypeScript + Tailwind, App Router, src/ dir)
  src/app/page.tsx           (health-check round trip to backend)
  .env.local                 (NEXT_PUBLIC_API_URL, gitignored)
data/
  irdai_policies/            (6 source PDFs — reference library; committed)
  damage_dataset/            (Roboflow zip; gitignored, too large to version)
```

Not yet created: `models/yolo_damage.pt` (Day 6), `README.md`/`ARCHITECTURE.md`/`EVALUATION_RESULTS.md` (Day 10).

## Data already present

- `data/irdai_policies/` — 6 PDFs: HDFC ERGO (comprehensive, TP-only, two-wheeler) and ICICI Lombard (same 3 types).
- `data/damage_dataset/car_damage_dataset_yolov8.zip` — ~1.3GB Roboflow-format car-damage dataset for the Day 6 YOLO fine-tune.

## Frontend: Next.js 16, not the Next.js in training data

`frontend/` was scaffolded with **Next.js 16.3.3 / React 19.2.8** — newer than most training data. `frontend/AGENTS.md` (auto-generated by `next dev`, re-added if deleted) flags this explicitly and points to `frontend/node_modules/next/dist/docs/` for current API/convention docs. Check those docs before assuming a Next.js API/pattern from memory, especially for anything beyond basic Server/Client Components (which were verified unchanged as of Day 1: `"use client"` + `useEffect` for client-side fetching, `NEXT_PUBLIC_` env var bundling — both work as expected).

## Working conventions for this project

- **Never fabricate claim-approval language.** Every advisory feature (coverage reasoning, claim-vs-pay, fraud signals) must be framed as advice/flags, explicitly deferring final say to the insurer — this is a deliberate product/legal framing decision repeated throughout `suggestions.md`, not a style nit.
- **Claim checklist requirements must be sourced from the actual insurer/policy text**, not invented by the LLM (per `suggestions.md` §1 item 12 / `requirements.txt`'s original spec).
- **Reuse before adding a subsystem.** Several "features" (policy comparison, gap analysis, renewal diff) are explicitly designed to reuse the same structured-extraction + comparison-engine pipeline rather than becoming separate systems — check `suggestions.md` §5/§8 before building something new that looks similar.
- **Everything stays local and free.** No cloud LLM/vision/embedding API calls, no paid services — this is a hard constraint from `suggestions.md` §0, not a cost-optimization preference.
- Update `PROGRESS.md`'s status table as tasks complete — it's the day-by-day source of truth for what's actually done versus planned.
