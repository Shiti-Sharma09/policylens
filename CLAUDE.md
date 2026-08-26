# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status: Pre-Implementation

**No application code exists yet.** This repository currently contains only planning documents and raw source data — no `backend/`, `frontend/`, or any FastAPI/Next.js scaffolding has been created. Do not assume any code structure exists; check with `ls`/`Glob` before referencing a path. When the user asks to start building, follow `PLAN.md`'s day-by-day order starting at Day 1 (Day 0 prep is already done — see `PROGRESS.md`).

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
- **LLM:** Qwen3-8B via Ollama, CPU inference, `localhost:11434` (fallback Qwen3-4B if too slow). Chosen for native tool-calling support at a CPU-runnable size — not a cloud API.
- **Embeddings:** Qwen3-Embedding-0.6B via Ollama, native dimension (no Matryoshka truncation needed at this size).
- **Vector DB:** Qdrant, self-hosted via Docker Compose.
- **App DB:** SQLite, not Postgres — single user, single writer, zero-config, one-file portability.
- **Vision:** YOLOv8n/v11n, fine-tuned (not stock COCO weights — COCO has no dent/scratch/windshield-crack classes) on a public Roboflow car-damage dataset via free Kaggle GPU hours; inference runs locally on CPU.
- **Auth:** self-rolled email+password (bcrypt + JWT), not Firebase phone-OTP — dropped because Firebase now requires a paid Blaze plan with a card on file for phone auth.
- **Frontend:** Next.js + Tailwind, run via `next dev` — no deployment target for this build.
- **Data:** 6 real IRDAI-filed policy wordings (2 insurers × {comprehensive, third-party-only, two-wheeler}) in `data/irdai_policies/` — these double as RAG test data *and* the gap-analysis reference library. Not synthetic, not scraped insurer marketing pages — the actual regulator-filed wordings.

### Proposed repo structure (once scaffolding starts — see `PLAN.md`'s "Repo Structure")

```
backend/
  app/
    main.py
    routers/    (auth, upload, ask, compare, damage, agent)
    services/   (rag.py, embeddings.py, yolo.py, comparison.py, fraud_signals.py, claim_advisor.py, agent.py)
    models/     (SQLModel schemas)
    db.py
  models/yolo_damage.pt
  requirements.txt
frontend/                    (Next.js + Tailwind)
data/
  irdai_policies/            (6 source PDFs — reference library; present now)
  damage_dataset/            (Roboflow set, gitignored if large; present now as a zip)
docker-compose.yml           (Qdrant only)
```

## Data already present

- `data/irdai_policies/` — 6 PDFs: HDFC ERGO (comprehensive, TP-only, two-wheeler) and ICICI Lombard (same 3 types).
- `data/damage_dataset/car_damage_dataset_yolov8.zip` — ~1.3GB Roboflow-format car-damage dataset for the Day 6 YOLO fine-tune.

## Working conventions for this project

- **Never fabricate claim-approval language.** Every advisory feature (coverage reasoning, claim-vs-pay, fraud signals) must be framed as advice/flags, explicitly deferring final say to the insurer — this is a deliberate product/legal framing decision repeated throughout `suggestions.md`, not a style nit.
- **Claim checklist requirements must be sourced from the actual insurer/policy text**, not invented by the LLM (per `suggestions.md` §1 item 12 / `requirements.txt`'s original spec).
- **Reuse before adding a subsystem.** Several "features" (policy comparison, gap analysis, renewal diff) are explicitly designed to reuse the same structured-extraction + comparison-engine pipeline rather than becoming separate systems — check `suggestions.md` §5/§8 before building something new that looks similar.
- **Everything stays local and free.** No cloud LLM/vision/embedding API calls, no paid services — this is a hard constraint from `suggestions.md` §0, not a cost-optimization preference.
- Update `PROGRESS.md`'s status table as tasks complete — it's the day-by-day source of truth for what's actually done versus planned.
