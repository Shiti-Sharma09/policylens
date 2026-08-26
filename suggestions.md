# PolicyLens v2: Revised Technical Approach & Strategic Decisions

**Goal:** Build a fully local, single-user AI insurance assistant in 1-2 weeks (part-time) with everything that matters folded into one build — no "Phase 2" bucket to hide behind.

**What changed from v1:** Longer runway (1-2 weeks, not 1), no more feature deferral — comparison, agentic orchestration, lightweight fraud signals, and claim-vs-pay reasoning are now in scope. LLM and embeddings moved from Gemini API to fully local open-source models. Postgres replaced with SQLite. Auth added (email+password, self-rolled — phone-OTP was tried and dropped once Firebase's Blaze/card requirement surfaced). Deployment dropped entirely — local-only, GitHub for version control.

---

## 0. Direct Answers To Your Questions

| Question | Answer | Why (short) |
|---|---|---|
| Open-source LLM instead of Gemini? | **Qwen3-8B** via Ollama, Q4_K_M quant, CPU inference (fallback: Qwen3-4B) | Vellum's leaderboard-topping open models (GLM 5.2, Kimi K2.6, DeepSeek V4-Pro, Kimi K3 — all 700B-1T MoE, even Vellum's own "best for local" pick Gemma 4 31B) aren't runnable on a no-GPU machine at usable speed. Qwen3 keeps native tool-calling at a size that runs at 15-30 tok/s on CPU |
| Embedding model + dimension? | **Qwen3-Embedding-0.6B**, native dimension | Same SOTA family as the MTEB-topping 8B variant, traded down to a size cheap enough for CPU — embedding is a single forward pass (not autoregressive decoding), so it stays fast even without a GPU |
| Train YOLO on vehicles/damage? | **Fine-tune** YOLOv8n/v11n on a public damage dataset — don't use stock COCO weights, don't train from zero | COCO has no "dent"/"scratch" classes; a few thousand labeled images already exist publicly, fine-tuning takes hours not days |
| PostgreSQL vs SQLite? | **SQLite** | Single user, single writer, embedded, zero-config, fully ACID-durable — Postgres buys you nothing here and adds a server to run |
| Is the frontend SOTA? | **Keep Next.js + Tailwind**, drop the Netlify piece | Still the most-used, most job-relevant React stack; SSR/API-route value is moot with no deployment, but it's still the right learning investment |
| Free real-world policy data? | **IRDAI's public document repository** (irdai.gov.in), 6 wordings (2 insurers x 3 structural types) | These are the actual regulator-filed policy wordings insurers are legally required to use — more authoritative than "sample PDFs" off insurer marketing pages. Live insurer/API-Setu production APIs require registration, consent flows, and often payment — not viable for a free portfolio build, so document-upload stays the right model |
| Policy comparison feature? | **Added** as a first-class feature, plus **gap analysis** against a small reference library | Side-by-side structured diff + LLM narrative for 2+ user-uploaded policies; a single uploaded policy can also be auto-compared against the reference library to surface "your policy lacks X that similar plans include" without needing a second upload |
| Other features? | Renewal diff, claim-vs-pay advisor, lightweight fraud signals, voice input — see §8 | Cheap to add given the RAG+comparison infra already exists |
| Single user, scale? | Confirmed — no multi-tenancy, no load concerns | Simplifies auth, DB choice, and rate limiting |
| Phone-number auth? | **Switched to email + password** (self-rolled, bcrypt + JWT) | Since Sept 2024, Firebase Phone Auth requires the paid Blaze plan with a card on file (usage itself stays ~$0 for one user, but the card requirement isn't worth it for a portfolio build). Email+password needs no external service at all, keeping the whole stack local and free |
| Deployment? | **None for now** — local-only, GitHub repo for source control | Explicit per your instruction; deployment becomes its own future phase if you decide to do it |

---

## 1. SCOPE: One Phase, 1-2 Weeks, Single User

No more "MVP now, impressive stuff later." Everything below ships in this build. The only things explicitly cut are the ones with genuinely poor time-to-value for a solo, 1-2 week, single-user project (see §9 "Still Out of Scope").

### Core User Flow

```
User (email+password login) → Upload Insurance PDF(s) → Extract & Structure Policy →
Ask Questions (RAG) OR Compare 2+ Policies OR Upload Damage Photo →
Agent orchestrates: retrieval / vision / comparison / checklist / claim-vs-pay →
Grounded answer with citations + risk flags where relevant
```

### Full Feature Set (single phase)

✅ Policy PDF upload, parsing, chunking
✅ RAG Q&A over policy text, with citations
✅ Policy comparison (2+ user-uploaded policies, structured + narrative) + gap analysis (1 uploaded policy vs. reference library)
✅ Damage photo → fine-tuned YOLO classification → coverage match
✅ Claim checklist generation (dynamic, not hardcoded)
✅ Claim-vs-pay-out-of-pocket advisor (rough cost estimate vs deductible/NCB tradeoff)
✅ Lightweight fraud/integrity signals (duplicate-image detection, EXIF/manipulation heuristics) — flags, never verdicts
✅ Single-agent tool-calling orchestration (not a multi-agent framework — see §7)
✅ Email + password authentication (self-rolled, bcrypt + JWT)
✅ Local encryption at rest, basic rate limiting

★ Insight ─────────────────────────────────────
Folding "Phase 2" into Phase 1 isn't just more work — it changes the *shape* of the build. Instead of a hardcoded pipeline (upload → RAG → answer), you now need an orchestration layer that decides which capability to invoke per request. That's exactly what the tool-calling agent in §7 buys you: one flexible entry point instead of five hardcoded ones.
─────────────────────────────────────────────────

---

## 2. TECHNOLOGY STACK (Local-First, Zero Recurring Cost)

### LLM: Qwen3-8B (Ollama, local, CPU)

- **Checked the Vellum leaderboard before picking this** (you asked). Vellum's overall top open models are GLM 5.2 (744B total/40B active MoE, 77.8% SWE-Bench), Kimi K2.6 (1T params), DeepSeek V4-Pro (80.6% SWE-Bench), and reasoning-leader Kimi K3 (93.5% GPQA Diamond). Even Vellum's own pick for **best local-deployment model, Gemma 4 31B**, assumes a GPU — at Q4 it needs ~16-20GB RAM and runs only a few tokens/sec on CPU alone. None of Vellum's top picks are usable on a no-GPU machine.
- **Why Qwen3-8B instead:** it's the largest Qwen3 size that stays comfortably usable on CPU — public benchmarks put 7B-class models at 15-30 tok/s on a modern CPU, which is slow but workable for a non-realtime portfolio demo (a few seconds per answer, not milliseconds). It keeps native tool-calling support, which the agent in §7 depends on.
- **Fallback:** Qwen3-4B if 8B feels too slow in practice — 3-4B models run 40-70 tok/s on CPU, still tool-calling-capable, just a bit weaker on hard reasoning ("does this damage fall under this exclusion clause"-type questions).
- **Serving:** Ollama (`ollama pull qwen3:8b`), exposed at `localhost:11434`, CPU mode (no GPU flags needed). Install natively, no Docker.

### Embeddings: Qwen3-Embedding-0.6B, native dimension (Ollama, local, CPU)

- **Why Qwen3-Embedding:** the 8B variant tops the MTEB leaderboard at 70.6 — ahead of OpenAI (64.6) and Google's embedding API (68.3). It's served natively through Ollama (2M+ pulls).
- **Why 0.6B, not 4B/8B:** embedding is a single forward pass per chunk, not autoregressive token-by-token decoding like the LLM — so it's much cheaper on CPU than generation is, but at your data volume (a handful of policies) there's no reason to pay for the largest variant either. The 0.6B model stays in the same SOTA-leaderboard family/training lineage, just sized for CPU throughput during PDF ingestion.
- **Dimension:** use the 0.6B model's native output dimension directly — it's smaller than the 4B/8B variants' 4096-dim output, so the earlier Matryoshka-truncate-to-1024 advice (sized for the bigger models) isn't needed here.

```
Education Point:
Embedding models and generative LLMs don't scale the same way on CPU.
An LLM has to run its full forward pass once PER OUTPUT TOKEN (autoregressive
decoding) — that's why a 14B LLM feels dramatically slower than a 4B one.
An embedding model runs its forward pass ONCE per chunk of input text,
regardless of output length. That's why it's fine to keep a mid-size
embedding model on CPU-only hardware even when you have to shrink the LLM
a lot more aggressively for the same hardware.
```

### Vector DB: Qdrant, embedded local mode (revised from v1's Docker Compose plan)

- **What changed:** v1 planned Qdrant self-hosted via Docker Compose. At Day 1 execution time, Docker wasn't installed on the build machine, and installing Docker Desktop would have required enabling WSL2/virtualization plus a likely reboot — friction with no payoff for a single-user local app.
- **What we use instead:** `qdrant-client`'s embedded local mode — the same Qdrant API, running fully in-process against an on-disk folder (`backend/qdrant_data/`, gitignored), no server or container at all.
- **Tradeoff:** the on-disk store is exclusive-locked to one process at a time — don't run two backend instances against the same path simultaneously. Otherwise functionally equivalent to the Docker-hosted version for this project's needs.

### Database: SQLite (replacing PostgreSQL)

- **Why the switch:** you're the only user. Postgres is built for concurrent writers and multi-terabyte scale — neither applies here. SQLite is a single file, fully ACID/durable (passes the same durability tests Postgres does), runs in-process with no server, no connection pool, no auth config, and is trivially backed up (copy the file).
- **What you lose:** true multi-writer concurrency and network access to the DB. You need neither.
- **Where vectors live:** still Qdrant, not SQLite — SQLite here only holds user account, policy metadata, and claim records.

```
Education Point:
"Production-grade" doesn't mean "biggest tool available" — it means
"the tool whose guarantees match your actual requirements." Postgres's
guarantees (concurrent writers, huge scale, network access) are wasted
on a single local user; SQLite's guarantees (ACID durability, zero-ops,
one-file portability) are exactly what this project needs. Knowing when
NOT to reach for Postgres is itself a signal of engineering judgment —
this is worth saying explicitly in your README/interview talking points.
```

### Vision: YOLOv8n/v11n, **fine-tuned** on a public car-damage dataset

- **Do you need to train it?** Yes — but not from scratch. Stock YOLO (COCO-pretrained) can detect "car" as an object but has no concept of "dent," "scratch," or "windshield crack" — those aren't COCO classes. You need a model fine-tuned on damage-labeled data.
- **What to use:** several public Roboflow datasets already exist with exactly this labeling — e.g. Curacel AI's car-damage set (~6.8k images) or a ~8.8k-image set from Skillfactory, both with bumper/door/fender/windshield-level damage classes. Fine-tune YOLOv8n or YOLOv11n on one of these.
- **No local GPU — train on a free cloud GPU instead:** Kaggle gives 30 free GPU-hours/week (P100/T4) and handles long-running training jobs more reliably than Colab's session timeouts; Colab's free T4 also works for a shorter run. Either way: upload the dataset, fine-tune there (a couple hours of GPU time, not days), download the resulting `.pt` weights (a nano model is ~6MB) and run **inference locally on CPU** — inference on a nano-size model is fast even without a GPU; only training needs the cloud GPU.
- **Alternative if time-constrained:** start from an already-fine-tuned checkpoint (e.g. a public YOLOv11n car-damage model, ~6MB, 79.7% mAP@0.5 across 14 damage categories) and optionally do a short additional fine-tune pass (still on Kaggle/Colab) on a small set of your own photos for calibration.
- **Why this matters for the portfolio:** "downloaded a pretrained model" is a much weaker story than "fine-tuned YOLO on a labeled damage dataset, here's the training curve and mAP" — and it's genuinely not much more work.

### Frontend: Next.js + Tailwind (kept, deployment piece dropped)

- Still the most widely used, most job-market-relevant React framework — no reason to switch for a local-only build.
- Since there's no deployment yet, you lose nothing by not using Next's SSR/API-route features today; keep them anyway since it's the standard you'd deploy with later. Run via `next dev` locally.

### Backend: FastAPI (unchanged)

### Authentication: Email + Password (self-rolled, no external service)

- **Why the switch:** phone-number OTP was the original ask, but every real SMS-delivery option costs money past a trial (Twilio, MSG91) or now requires a card on file even for near-zero usage (Firebase, since Sept 2024's policy change). None of that is worth it for a single-user portfolio build.
- **What you build:** a standard registration/login flow — password hashed with bcrypt (via `passlib`) before storage in SQLite, a login endpoint that verifies the hash and issues a JWT, and a FastAPI dependency that validates that JWT on protected routes. No external account, no card, no network dependency at all.
- **Why this is arguably the better portfolio story anyway:** implementing the hash-verify-issue-token flow yourself demonstrates you understand what "auth" actually does under the hood, rather than "I wired up a vendor SDK." It's also one less moving part in a project whose whole design principle is "everything runs locally, for free."
- **Scope-check:** since you're the only user, this remains mostly a demonstration of understanding real auth flows (not a security requirement) — don't over-build session management around it.

### Local Development Setup (replacing the whole Deployment section)

```
Backend:    FastAPI, run via `uvicorn` locally
LLM+Embed:  Ollama, native install (not Docker — GPU passthrough is simpler)
Vector DB:  Qdrant, embedded local mode via qdrant-client (no Docker/server)
DB:         SQLite file, gitignored, sits alongside the backend
Frontend:   Next.js dev server (`npm run dev`)
Files:      Local disk, encrypted at rest
Repo:       Public or private GitHub repo, normal commits + PRs if you want
            the habit — no CI/CD deploy step needed yet
```

**Total cost:** $0, no recurring anything. Deployment (Railway/Netlify/etc.) becomes its own task later if you decide to do it — not part of this build.

---

## 3. ARCHITECTURE

```
┌───────────────────────────────────────────────────┐
│         FRONTEND (Next.js + Tailwind, local)      │
│         Email + password login form on client      │
└──────────────────┬──────────────────────────────────┘
                    │ localhost API calls
┌──────────────────▼──────────────────────────────────┐
│              BACKEND (FastAPI, local)                │
│                                                        │
│   Verifies password hash (bcrypt) → issues JWT          │
│                                                        │
│  ┌──────────────────────────────────────────────┐   │
│  │       TOOL-CALLING AGENT (Qwen3-8B, CPU)      │   │
│  │  Decides which tool(s) a request needs:       │   │
│  │  retrieve_policy_sections | classify_damage   │   │
│  │  compare_policies | generate_checklist        │   │
│  │  estimate_claim_vs_deductible | fraud_signals │   │
│  └───┬─────────┬──────────┬──────────┬───────────┘   │
│      │         │          │          │               │
│  ┌───▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼──────────┐   │
│  │ RAG    │ │ YOLO    │ │Compare │ │ Fraud signals│   │
│  │(Qdrant │ │(fine-   │ │engine  │ │(pHash, EXIF, │   │
│  │+Qwen3- │ │tuned,   │ │(struct.│ │ ELA — flags  │   │
│  │Embed-  │ │CPU      │ │+ LLM)  │ │ not verdicts)│   │
│  │0.6B)   │ │infer.)  │ │        │ │              │   │
│  └───┬────┘ └────┬────┘ └───┬────┘ └──────┬───────┘   │
└──────┼────────────┼──────────┼─────────────┼──────────┘
       │             │          │             │
   ┌───▼───┐   ┌─────▼────┐  ┌─▼────────┐
   │ Qdrant │   │  SQLite  │  │File store│
   │(vectors│   │(users,   │  │(PDFs,    │
   │)       │   │ policies,│  │ photos,  │
   │        │   │ claims)  │  │encrypted)│
   └────────┘   └──────────┘  └──────────┘
```

---

## 4. DATA STRATEGY: Real Policies, Legally Clean

### The Answer: IRDAI's Document Repository

Instead of scraping sample-policy pages off insurer marketing sites, use **irdai.gov.in**'s public document repository directly. IRDAI (India's insurance regulator) publishes the actual **regulator-filed policy wordings** insurers are legally required to use — these are the real documents, not marketing summaries, and they're public by design (that's the point of regulatory filing).

**On the alternative data routes (API Setu, insurer developer APIs):** both were evaluated and ruled out for this build. API Setu's data-sharing is governed by a consent-management framework requiring express per-individual consent — not something a portfolio project can obtain for real policyholders, and its sandbox only offers simulated data. Insurer developer portals (e.g. HDFC ERGO's Motor Insurance API) require registration, approval, and often a commercial agreement for production use. Neither is "free API access" in practice — the document-upload model (§0, §1) sidesteps this entirely, since it never needs access to anyone's private insurer account.

**Quality over quantity, per your instruction — 6 documents, not 30, but enough for gap analysis (see §5):**

```
2 insurers x 3 structural types = 6 wordings

Insurer A (e.g. HDFC ERGO):
  1. Private car comprehensive policy wording
  2. Standalone motor third-party-only wording
  3. Two-wheeler policy wording

Insurer B (e.g. ICICI Lombard):
  4. Private car comprehensive policy wording
  5. Standalone motor third-party-only wording
  6. Two-wheeler policy wording
```

This still covers the structural variation that matters (comprehensive vs. third-party-only vs. two-wheeler) without building parsers for 20 insurer PDF layouts — the second insurer's set is what makes gap analysis meaningful (comparing a user's policy against just one example of its type is a coin flip; against two is a real "here's what's typical" baseline).

```
Education Point:
This is a strictly better data story than "sample PDFs from insurer
websites": IRDAI filings are the authoritative source insurers must
match, they're unambiguously public (regulatory filing, not marketing
content), and citing "IRDAI-filed policy wordings" in your README reads
as more rigorous than "sample policies" to a technical interviewer.
```

---

## 5. NEW FEATURE: Policy Comparison

Upload 2+ policies → structured side-by-side comparison across the dimensions that actually change a buying decision:

| Dimension | Example |
|---|---|
| Premium | ₹8,200/yr vs ₹9,600/yr |
| IDV (Insured Declared Value) | ₹4.2L vs ₹4.5L |
| Coverage inclusions | Own damage + TP vs Own damage + TP + engine protection |
| Exclusions | Racing, wear & tear (both) vs also excludes consequential loss |
| Deductible | ₹2,000 vs ₹1,000 |
| Add-ons available | Zero-dep, roadside assist vs Zero-dep only |
| Claim limits | Engine ₹50k vs unlimited (with add-on) |
| No-Claim Bonus structure | Standard slab vs accelerated slab |

**Implementation:** structured extraction (same pipeline as single-policy parsing) into a comparable schema, rendered as a table, plus an LLM-generated narrative ("Policy B costs 17% more but includes engine protection and a lower deductible — better value if you drive in flood-prone areas").

This reuses your RAG extraction pipeline almost entirely — the new work is the comparison schema + table UI + a comparison-specific prompt, which is a day or two, not a new subsystem.

### Gap Analysis: Comparing a Single Policy Against the Reference Library

Manual comparison (above) needs the user to upload 2+ policies. Most of the time they'll only have one — their own. Since the 6 IRDAI wordings from §4 are already ingested and structurally extracted for RAG, they double as a **reference library**: run the same comparison engine between the user's uploaded policy and the same-type reference document(s) (e.g. their comprehensive private-car policy vs. both insurers' comprehensive wordings) to surface gaps automatically.

```
User uploads their policy
       ↓
Structured extraction (same pipeline as §4/§5)
       ↓
Identify structural type (comprehensive / TP-only / two-wheeler)
       ↓
Compare against matching reference doc(s) from the library
       ↓
"Your policy covers zero-depreciation but not engine protection —
 both reference comprehensive policies include the latter as a
 standard add-on option. Your deductible (₹2,000) is standard;
 IDV of ₹4.2L is in the typical range for this vehicle class."
```

**Why this is worth the extra 3 documents:** it turns policy comparison from "only useful if the user happens to have two policies" into "useful for anyone who uploads just their own policy" — a much more common real-world case, and a stronger single-policy-upload demo. Implementation cost is small: the reference library only needs one-time ingestion (already happening for RAG testing anyway) and reuses the exact comparison engine built for manual 2-policy comparison — no new subsystem.

---

## 6. VISION + REASONING FLOW (unchanged shape, new models)

```
User uploads damage image
       ↓
Fine-tuned YOLO detects: {damage_type: "bumper_dent", confidence: 0.87, location: "front_bumper"}
       ↓
Agent calls retrieve_policy_sections("bumper damage coverage")
       ↓
Agent calls estimate_claim_vs_deductible(damage_type, policy)
       ↓
LLM reasons over retrieved sections + estimate:
"Comprehensive coverage includes bumper damage. Estimated repair: ₹6,000.
 Your deductible is ₹2,000, so filing nets ~₹4,000 — but you'd lose one
 year's No-Claim Bonus (~₹1,800 next renewal). Marginal call; your choice."
       ↓
Display recommendation + claim checklist + fraud-signal flags (if any)
```

**Unchanged principle from v1:** the system never says "your claim is approved" — only the insurer approves claims. It reasons and advises; it doesn't adjudicate.

---

## 7. AGENTIC ORCHESTRATION (single agent, tool-calling — not a framework)

You asked to fold this in from "Phase 2." The lightweight version that fits 1-2 weeks: **one LLM with tool-calling**, not a multi-agent framework (CrewAI/AutoGen-style orchestration would be over-engineering here — you have one user making one request at a time, not agents coordinating with each other).

```python
tools = [
    retrieve_policy_sections,      # RAG lookup
    classify_damage,                # YOLO inference
    compare_policies,               # structured comparison (2+ user policies, or 1 vs. reference library)
    generate_claim_checklist,       # dynamic checklist
    estimate_claim_vs_deductible,   # claim-vs-pay reasoning
    check_fraud_signals,            # pHash/EXIF/ELA flags
]
# Qwen3-8B decides which tool(s) a given user message needs,
# calls them, and synthesizes a grounded answer.
```

```
Education Point:
"Agentic" doesn't require multiple agents — it means the model decides
WHICH capability to invoke based on the request, instead of you hardcoding
"if image uploaded, call YOLO." A single tool-calling loop is the honest,
right-sized version of "agentic orchestration" for a single-user app —
and it's exactly the pattern production systems use before they need
true multi-agent coordination (which is itself usually a sign of
poor task decomposition, not a feature to reach for by default).
```

---

## 8. ADDITIONAL SUGGESTED FEATURES (small, high-leverage)

Kept deliberately short — these ride on infrastructure you're already building, so each is roughly a day or less:

✅ **Renewal diff** — upload last year's + this year's policy from the same insurer, get a plain-language "what changed" summary (reuses the comparison engine from §5).
✅ **Claim-vs-pay advisor** (already folded into §1/§6) — the single most useful real-world feature for an actual policyholder.
✅ **Lightweight fraud/integrity signals** (already folded into §1) — perceptual-hash duplicate detection + EXIF consistency check + basic Error Level Analysis. Cheap, real, and shown as flags for manual review, never a verdict — keeps the "responsible AI" framing from v1 intact.
✅ **Voice input for the chat/claim flow** — Web Speech API, zero backend cost, nice demo moment, ~half a day.

**Not recommended to add:** multi-insurer live-quote fetching, payment integration, or a mobile app — none of these teach you anything new relative to what's already in scope, and all three meaningfully extend the timeline.

---

## 9. STILL OUT OF SCOPE (and why, explicitly — not just deferred)

Since there's no "Phase 2" to wave at anymore, here's the honest reasoning for what's cut, so it reads as a decision rather than an omission:

❌ **Multi-format OCR (20+ insurer layouts)** — quality over quantity, per your own instruction. Three structurally-distinct IRDAI wordings (§4) cover the real variation. If a new format fails to parse, the system should fail gracefully (clear error, not garbage extraction), not attempt to special-case every layout.
❌ **Full multi-agent framework** (CrewAI/AutoGen/etc.) — a single tool-calling agent (§7) already delivers the "agentic" behavior; adding agent-to-agent coordination for a single-user, single-request-at-a-time app would be complexity with no corresponding benefit.
❌ **Heavy ML fraud detection** (trained anomaly-detection model on claim patterns) — no labeled fraud dataset exists for you to train on, and the lightweight heuristic version (§8) already demonstrates the concept credibly.
❌ **Deployment** — explicitly deferred per your instruction; local-only for this build, GitHub repo maintained for version control, deployment is a distinct future task if you choose to do it.

---

## 10. SECURITY (still pragmatic, phone-auth adjusted)

```
1. Authentication: email + password, bcrypt-hashed, JWT session — no external service
2. Authorization: single user, but still scope all queries to authenticated session
3. Encryption at rest: policies/photos encrypted on local disk
4. No HTTPS needed (local-only, not exposed to network)
5. Basic rate limiting: still worth adding — protects against runaway
   local agent loops (a buggy tool-calling cycle) more than external abuse
6. No logging PII: log "user queried policy," not query contents
```

---

## 11. TIMELINE (1-2 Weeks, Part-Time)

Roughly 10 working sessions (~5 hrs each, ~50 hrs total — scales to 2 full weeks part-time).

```
WEEK 1 — Foundation + Core RAG
Day 1  Setup: FastAPI, Next.js, Qdrant (embedded local mode), Ollama (Qwen3-8B + Qwen3-Embedding-0.6B,
       CPU mode), SQLite schema, GitHub repo. Pull the 3 IRDAI policy wordings (§4).
       Note: local inference runs a few seconds per response on CPU, not milliseconds —
       fine for a solo demo, just budget for it when testing interactively.
Day 2  Email+password auth (register/login forms, bcrypt hashing, JWT session).
       PDF upload + parsing + chunking pipeline.
Day 3  Embedding pipeline (Qwen3-Embedding-0.6B, native dim) → Qdrant. Retrieval endpoint.
Day 4  LLM answer generation with citations. Basic chat UI in Next.js.
Day 5  Policy comparison: structured extraction schema + comparison table + narrative prompt.

WEEK 2 — Vision, Agent, Advisors, Polish
Day 6  YOLO fine-tuning: pull a public damage dataset (Curacel AI or Skillfactory set),
       fine-tune YOLOv8n/v11n on Kaggle (free GPU), evaluate mAP, download weights
       for local CPU inference.
Day 7  Damage → coverage matching. Claim checklist generation (dynamic).
Day 8  Tool-calling agent wiring (§7): register all tools, test routing across
       Q&A / comparison / vision / checklist requests.
Day 9  Claim-vs-pay advisor + lightweight fraud signals (pHash, EXIF, ELA).
Day 10 Frontend polish, end-to-end testing, evaluation pass (§12), README + docs.
```

**Buffer, in priority-drop order if time runs short:** voice input → renewal diff → fraud signals depth (keep at least pHash duplicate check) → YOLO fine-tune depth (fall back to an already-fine-tuned checkpoint, §2).

---

## 12. EVALUATION (scaled for solo build — quality over the original's 100-case target)

Since this is single-user and time-boxed, aim for a smaller but well-documented eval set rather than volume for its own sake:

```
TIER 1 (15 cases): Retrieval accuracy — does RAG return the right section?
TIER 2 (15 cases): Citation accuracy — does the answer cite the right section?
TIER 3 (10 cases): Vision — damage classification correctness (mAP from YOLO eval)
TIER 4 (10 cases): Comparison correctness — does the structured diff match manual read?
TIER 5 (10 cases): End-to-end — full flows (upload→ask, upload→compare, photo→advise)
```

60 well-chosen, manually-verified cases with documented results reads as more credible than 100 rushed ones. Document methodology and failure modes in `EVALUATION_RESULTS.md` — that file was your strongest asset in v1 and nothing here changes that.

---

## FINAL THOUGHT

v1's philosophy was "ship a bulletproof MVP, defer the rest." That was the right call for 1 week. At 1-2 weeks with everything folded in, the philosophy shifts to: **one flexible orchestration layer (the tool-calling agent) that makes RAG, vision, comparison, and advisory reasoning all first-class, backed by models and data sources that are honestly the best available for a single-GPU, single-user, zero-budget build.**

Nothing here is fake-scoped or hand-waved — every recommendation above is something that runs on the hardware you actually have, using data you can legitimately use, in the time you actually have.

**Next steps:**
1. Confirm Qwen3-8B Q4 gives acceptable latency on your CPU (`ollama pull qwen3:8b`, time a sample generation) before committing Day 1 to it — drop to Qwen3-4B if it's too slow.
2. Set up a free Kaggle account (for the Day 6 YOLO fine-tuning step) and pull the 3 IRDAI policy wordings + the chosen Roboflow damage dataset now, so Day 1 isn't blocked on downloads.
3. Then start Day 1.
