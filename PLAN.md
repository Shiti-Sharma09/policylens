# PolicyLens: Execution Plan

This is the **how/when** companion to `suggestions.md` (the **what/why**). Every tech decision referenced below (model choices, DB choice, data source, feature scope) is argued for in `suggestions.md` — this file focuses purely on execution order, concrete setup steps, and what "done" looks like for each session.

**Total runway:** 1-2 weeks, part-time, ~10 working sessions (~5 hrs each, ~50 hrs). Single user, fully local, no deployment.

---

## Quick Plan

| Day | Focus | Key Deliverable |
|---|---|---|
| 0 | Prep | Ollama + models pulled, Kaggle account, 6 IRDAI reference PDFs + damage dataset downloaded |
| 1 | Scaffolding | FastAPI + Next.js + Qdrant + SQLite running locally, repo initialized |
| 2 | Auth + Ingestion | Email+password login works; PDF upload → parsed → chunked |
| 3 | Embeddings + Retrieval | Chunks embedded into Qdrant; retrieval endpoint returns relevant sections |
| 4 | RAG Answers | Chat UI: ask a question, get a cited answer from a real policy |
| 5 | Policy Comparison | Upload 2 policies → comparison table + narrative; single policy → gap analysis vs. reference library |
| 6 | Vision | YOLO fine-tuned on Kaggle GPU on damage dataset; weights running locally on CPU |
| 7 | Damage → Coverage | Photo upload → damage type → matched policy coverage + dynamic checklist |
| 8 | Agent Orchestration | Single tool-calling agent routes any request to the right tool(s) |
| 9 | Advisors | Claim-vs-pay reasoning + fraud/integrity flags (pHash, EXIF, ELA) |
| 10 | Polish + Eval | End-to-end testing, 60-case evaluation, README + docs, push to GitHub |

---

## Detailed Plan

### Day 0 — Prep (before Week 1 starts)

Nothing here should block Day 1 — it's all downloads/account setup.

- [ ] Install [Ollama](https://ollama.com) natively (not Docker — simpler on Windows)
- [ ] `ollama pull qwen3:8b` — time a sample generation; if too slow, `ollama pull qwen3:4b` as the fallback (see `suggestions.md` §2)
- [ ] `ollama pull qwen3-embedding:0.6b` (or the exact tag Ollama lists for the 0.6B variant)
- [ ] Create a free [Kaggle](https://kaggle.com) account (needed for Day 6 YOLO fine-tuning — 30 free GPU-hrs/week)
- [ ] ~~Create a free Firebase project, enable Phone Authentication~~ — dropped: Firebase now requires a Blaze plan + card on file for phone auth. Switched to self-rolled email+password (bcrypt + JWT), no external account needed for auth at all.
- [ ] Download the 6 IRDAI policy wordings identified in `suggestions.md` §4 (2 insurers x 3 structural types):
  1-3. Insurer A (e.g. HDFC ERGO): comprehensive, third-party-only, two-wheeler
  4-6. Insurer B (e.g. ICICI Lombard): comprehensive, third-party-only, two-wheeler
  (These double as the RAG test set *and* the gap-analysis reference library — see §5.)
- [ ] Pick and download one Roboflow car-damage dataset (Curacel AI ~6.8k images, or Skillfactory ~8.8k images — `suggestions.md` §2)

**Done when:** Ollama responds to a test prompt locally, Kaggle + Roboflow accounts exist, and all source PDFs/dataset are sitting in a local `data/` folder.

---

### WEEK 1 — Foundation + Core RAG

#### Day 1 — Environment & Scaffolding

- [ ] `git init`, create GitHub repo (public or private), first commit
- [ ] Backend: `fastapi`, `uvicorn`, project skeleton (`app/main.py`, `app/routers/`, `app/models/`, `app/services/`)
- [ ] Frontend: `npx create-next-app` with Tailwind, basic page skeleton
- [x] Qdrant via `qdrant-client` embedded local mode (on-disk at `backend/qdrant_data/`, gitignored) — revised from the original Docker Compose plan; Docker isn't installed on the build machine, see `suggestions.md` §2
- [ ] SQLite schema (via SQLModel/SQLAlchemy): `users`, `policies`, `policy_chunks_meta`, `claims` tables — gitignore the `.db` file
- [ ] `.env.example` documenting required vars (JWT secret key, Ollama host, Qdrant host)
- [ ] Sanity check: backend `/health` endpoint, frontend hits it and renders "OK"

**Done when:** `uvicorn` and `next dev` both run locally, embedded Qdrant initializes, SQLite tables exist, and a trivial frontend→backend round trip works.

#### Day 2 — Auth + Ingestion

- [ ] Register/login forms in Next.js (email + password fields)
- [ ] FastAPI endpoints: register (hash password with bcrypt, store user), login (verify hash, issue JWT)
- [ ] FastAPI dependency that validates the JWT on protected routes and resolves it to a `users` row
- [ ] PDF upload endpoint (`multipart/form-data`), stored to local disk (encrypted at rest — see `suggestions.md` §10)
- [ ] Text extraction (pdfplumber or PyPDF2) + cleaning
- [ ] Chunking (e.g. ~500-token sliding window, matching `suggestions.md`'s RAG pipeline description)
- [ ] Upload the 6 IRDAI PDFs through this pipeline as your first real test data (also seeds the reference library for Day 5's gap analysis)

**Done when:** registering and logging in via email+password works end-to-end, and uploading any of the 6 IRDAI PDFs produces a stored, chunked policy in the DB.

#### Day 3 — Embeddings + Retrieval

- [ ] Embedding service wrapping Ollama's `qwen3-embedding:0.6b` endpoint
- [ ] On chunk creation: embed each chunk, upsert into Qdrant (vector + payload: policy_id, chunk_text, section_hint)
- [ ] Retrieval endpoint: embed a query, top-k similarity search against Qdrant, return chunks + policy citation metadata
- [ ] Manual test: query "is windshield damage covered?" against one uploaded policy, confirm relevant chunks come back

**Done when:** a raw retrieval endpoint (no LLM yet) reliably returns the right policy section for a hand-written test question.

#### Day 4 — RAG Answers + Chat UI

- [ ] Prompt template: question + retrieved chunks → grounded answer with citation back to section/page
- [ ] `/ask` endpoint: retrieve → call Qwen3-8B via Ollama (**must pass `think: false`** — see `suggestions.md`'s "Validated on actual hardware" note, without it a single answer takes 27+ minutes) → return answer + citations
- [ ] Chat UI in Next.js: policy selector, message thread, citation display (click to see source chunk), **and a visible "thinking..." / progress state** — real answers take ~20-90s on this hardware, not milliseconds
- [ ] Cache identical (policy_id, question) pairs in SQLite — a meaningful latency win, not just a nice-to-have, given measured CPU inference speed (`suggestions.md` §2)

**Done when:** you can ask a real question about one of the 3 IRDAI policies in the UI and get a cited, grounded answer, with the UI showing a loading state for the ~20-90s it actually takes (corrected from an earlier "a few seconds" assumption that Day 1 benchmarking showed was wrong for this hardware — see `suggestions.md` §2).

#### Day 5 — Policy Comparison + Gap Analysis

- [ ] Structured extraction schema (premium, IDV, coverage, exclusions, deductible, add-ons, claim limits, NCB — see `suggestions.md` §5 table)
- [ ] Extraction prompt: run structured extraction over each policy independently (reuses the Day 3/4 retrieval + LLM pipeline)
- [ ] Comparison endpoint: given 2+ policy IDs, diff the structured fields
- [ ] Comparison UI: side-by-side table + LLM-generated narrative summary
- [ ] Test with 2 of the 6 IRDAI wordings (comprehensive vs. third-party-only is the most interesting diff)
- [ ] Gap-analysis mode: given 1 policy ID, auto-match its structural type and diff against the corresponding reference doc(s) already ingested on Day 2 (`suggestions.md` §5 "Gap Analysis" subsection)
- [ ] Test gap analysis by uploading a copy of one reference policy and confirming it reports "no gaps" (sanity check the diff logic), then a deliberately different policy and confirming it surfaces real gaps

**Done when:** uploading and comparing 2 policies produces both an accurate table and a coherent narrative recommendation, AND uploading a single policy alone produces a sensible gap-analysis summary against the reference library.

---

### WEEK 2 — Vision, Agent, Advisors, Polish

#### Day 6 — YOLO Fine-Tuning

- [ ] Upload the chosen Roboflow damage dataset to a Kaggle notebook
- [ ] Fine-tune YOLOv8n or YOLOv11n (Ultralytics) on Kaggle's free GPU
- [ ] Evaluate mAP@0.5 on the held-out split; log the training curve (for `EVALUATION_RESULTS.md` later)
- [ ] Download the resulting `.pt` weights into the repo (`models/yolo_damage.pt`)
- [ ] Confirm local CPU inference works on a sample photo (`ultralytics` package, CPU mode)

**Done when:** you have a fine-tuned weights file in the repo and a local script that classifies a test damage photo correctly.

#### Day 7 — Damage → Coverage Match + Checklist

- [ ] `/classify-damage` endpoint: image in → `{damage_type, confidence, location}` out
- [ ] Coverage-matching logic: damage type → relevant policy retrieval query (reuses Day 3 retrieval)
- [ ] Dynamic claim checklist generator (damage type + policy + claim type → required documents — see `suggestions.md` §9 in v1 logic, still valid)
- [ ] UI: photo upload, damage result display, checklist display

**Done when:** uploading a damage photo against an uploaded policy produces a correct damage classification, a coverage match explanation, and a sensible document checklist.

#### Day 8 — Agent Tool-Calling Orchestration

- [ ] Define the tool schema for all 6 tools (`suggestions.md` §7): `retrieve_policy_sections`, `classify_damage`, `compare_policies`, `generate_claim_checklist`, `estimate_claim_vs_deductible`, `check_fraud_signals`
- [ ] Wire Qwen3-8B's native tool-calling (Ollama) to route a single free-text or multimodal request to the correct tool(s)
- [ ] Replace the Day 4/5/7 hardcoded endpoints with calls through the agent where it makes sense — single entry point (`/agent/message`) becomes the primary API surface
- [ ] Test routing across mixed inputs: plain question, comparison request, photo + question in the same turn

**Done when:** a single endpoint correctly routes to RAG, comparison, or vision depending on what's in the request, without you hardcoding which path to take.

#### Day 9 — Claim-vs-Pay Advisor + Fraud Signals

- [ ] `estimate_claim_vs_deductible` tool: rough repair-cost estimate (rule-based band by damage type/severity, or LLM-estimated) vs. deductible + NCB-loss tradeoff, output as advisory reasoning (not a verdict — `suggestions.md` §6)
- [ ] `check_fraud_signals` tool:
  - Perceptual hash (imagehash) each uploaded photo, flag near-duplicates across claims
  - EXIF consistency check (timestamp/GPS vs. claim date, stripped-metadata flag)
  - Basic Error Level Analysis (PIL/OpenCV) as a manipulation heuristic
- [ ] Surface both as advisory flags in the UI, styled distinctly from the core answer (never phrased as a decision)

**Done when:** a damage-claim flow produces a claim-vs-pay recommendation with visible reasoning, and at least the pHash duplicate check flags a deliberately-reused test photo correctly.

#### Day 10 — Polish, Evaluation, Docs

- [ ] End-to-end pass through every flow: login → upload → ask → compare → photo claim → checklist → advisor
- [ ] Bug fixes from the full pass
- [ ] Run the 60-case evaluation set (`suggestions.md` §12 tiers), document results in `EVALUATION_RESULTS.md`
- [ ] Write `README.md` (overview, tech stack, how to run locally) and `ARCHITECTURE.md` (the diagram + pipeline detail from `suggestions.md` §3, §6, §7)
- [ ] Final commit + push to GitHub

**Done when:** the full flow works without crashing end-to-end, evaluation results are documented with honest numbers (including failure cases), and the repo is pushed with a README someone else could follow to run it.

---

## Repo Structure (proposed)

```
policylens/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/        (auth, upload, ask, compare, damage, agent)
│   │   ├── services/       (rag.py, embeddings.py, yolo.py, comparison.py,
│   │   │                    fraud_signals.py, claim_advisor.py, agent.py)
│   │   ├── models/         (SQLModel schemas)
│   │   └── db.py
│   ├── models/
│   │   └── yolo_damage.pt
│   └── requirements.txt
├── frontend/               (Next.js + Tailwind app)
├── data/
│   ├── irdai_policies/     (6 source PDFs — reference library)
│   └── damage_dataset/     (Roboflow set, gitignored if large)
├── README.md
├── ARCHITECTURE.md
├── EVALUATION_RESULTS.md
├── suggestions.md          (tech decisions + reasoning)
└── PLAN.md                 (this file)
```

---

## Risk & Buffer Plan

Same drop-order as `suggestions.md` §11 if a day runs long: **voice input → renewal diff → fraud-signal depth (keep at least pHash) → YOLO fine-tune depth (fall back to an already-fine-tuned public checkpoint)**. None of these cuts touch the core flow (login → RAG → comparison → vision → checklist → agent), so the demo stays coherent even if a stretch feature slips.

---

## Definition of "Done" for the Whole Build

- [ ] All 10 checklist items above are checked
- [ ] Every feature in `suggestions.md` §1's "Full Feature Set" table is demonstrable locally
- [ ] `EVALUATION_RESULTS.md` has real, honest numbers — not just "it seems to work"
- [ ] Repo is on GitHub with a README that lets a stranger run it locally from scratch
