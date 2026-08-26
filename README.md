# PolicyLens

**An AI assistant that reads your vehicle insurance policy so you don't have to.**

Most vehicle owners in India buy insurance to stay legally compliant, but few actually understand what their policy covers, what it excludes, or whether a specific type of damage is likely to be reimbursed. PolicyLens lets you upload your policy document and a photo of vehicle damage, then answers questions in plain language — grounded in your actual policy, not generic advice — and helps you figure out what to do next.

> ⚠️ **Status:** actively in development. The core product flow described below is the target design; see [Current Progress](#current-progress) for what's actually working today.

---

## What it does

- **Ask questions about your policy** — "Does my policy cover windshield damage?", "Do I have roadside assistance?" — and get an answer with the exact section it came from, not a guess.
- **Understand a damage claim** — upload a photo of vehicle damage, and the assistant identifies the type of damage and checks it against your policy's coverage.
- **Compare policies** — upload two policies side by side, or check your own policy against a small reference library to see what it might be missing.
- **Get a claim checklist** — a list of documents typically needed for your specific situation (accident, theft, hit-and-run), rather than a generic list.
- **Weigh claim vs. pay-yourself** — a rough estimate of whether filing a claim is worth it once the deductible and no-claim bonus are factored in.

Every answer is framed as guidance, not a decision — final claim approval always rests with the insurer. The assistant explains the *why* behind an answer instead of a plain yes/no.

## How it's built

PolicyLens runs entirely on your own machine — no data leaves your computer, and there are no subscription costs to any AI provider.

- **Backend:** Python (FastAPI)
- **Frontend:** Next.js + Tailwind CSS
- **Language understanding:** a locally-run open-source language model, used to read policy text and answer questions with citations
- **Damage detection:** a computer vision model fine-tuned specifically to recognize common types of vehicle damage (dents, scratches, cracked glass, etc.)
- **Storage:** a local database for accounts and policy records, plus a local search index for finding the right part of a policy quickly

## Getting started

**Requirements:** Python 3.12+, Node.js 18+, and [Ollama](https://ollama.com) installed locally.

### 1. Pull the required local models
```bash
ollama pull qwen3:8b
ollama pull qwen3-embedding:0.6b
```

### 2. Run the backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env      # macOS/Linux: cp .env.example .env
uvicorn app.main:app --reload --port 8000
```
Visit `http://localhost:8000/health` — you should see `{"status": "ok"}`.

### 3. Run the frontend
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:3000` — the page should show the backend status as **OK**.

## Current progress

| Area | Status |
|---|---|
| Backend + frontend scaffolding | ✅ Done |
| Account creation and login | 🚧 In progress |
| Policy upload and understanding | ⏳ Planned |
| Ask-a-question chat | ⏳ Planned |
| Policy comparison | ⏳ Planned |
| Damage photo recognition | ⏳ Planned |
| Claim checklist and cost guidance | ⏳ Planned |

## Data sources

The reference policy documents used for testing and comparison come from insurers' official regulator-filed policy wordings (via IRDAI, India's insurance regulator) — real policy language, not synthetic samples.

---

*A personal project built to explore practical, real-world applications of AI — combining document understanding, computer vision, and everyday decision support into one tool.*
