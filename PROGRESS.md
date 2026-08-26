# PolicyLens: Progress Tracker

Use this file to track progress day by day. Update the **Status** column as you go (`Pending` → `In Progress` → `Done`; use `Blocked` if something's stuck). Action items and order come directly from `PLAN.md`.

---

## Day 0 — Prep

| Action Item | Desired Outcome | Status |
|---|---|---|
| Install Ollama locally | AI model runner working on your machine | Done |
| Pull Qwen3-8B (or 4B fallback) model | Main chatbot "brain" downloaded and ready | Done |
| Pull Qwen3-Embedding-0.6B model | Text-search model downloaded and ready | Done |
| Create free Kaggle account | Access to free cloud GPU for later | Pending (needs your login) |
| ~~Create Firebase project, enable phone auth~~ (dropped) | N/A — switched to self-rolled email+password auth, no external service needed | Not needed |
| Download 6 IRDAI policy PDFs | Real insurance documents ready to feed the app | Done |
| Download Roboflow damage dataset | Labeled car-damage photos ready for training | Done |

**What each action item means:**

1. **Install Ollama locally**
   - Ollama is a free program that runs AI models on your own computer.
   - No internet is needed once it's installed — everything runs offline.
   - This is the tool that will power your chatbot's "brain."

2. **Pull Qwen3-8B (or 4B fallback) model**
   - This downloads the actual AI model file onto your computer.
   - Think of it like downloading an app before you can use it.
   - If it runs too slowly, you'll switch to a smaller, faster version (4B).

3. **Pull Qwen3-Embedding-0.6B model**
   - This downloads a second, smaller AI model.
   - Its job is turning text into numbers so the computer can compare meanings.
   - This is what powers the "search my policy" feature later on.

4. **Create free Kaggle account**
   - Kaggle is a free website that lends you a powerful computer to use.
   - You'll use it later to train your damage-detection model.
   - No payment needed — just sign up with an email.

5. **~~Create Firebase project, enable phone auth~~ (dropped)**
   - Turns out Firebase now requires a linked card to use phone-number login, even though actual usage stays free.
   - Rather than deal with that for a solo project, login switched to a classic email + password form instead.
   - Nothing to set up here anymore — this gets built directly in your own backend on Day 2.

6. **Download 6 IRDAI policy PDFs**
   - These are real insurance policy documents from the government's website.
   - They'll be the sample data your app learns to read and understand.
   - Using real documents makes your project far more convincing to show off.

7. **Download Roboflow damage dataset**
   - This is a folder of car-damage photos that are already labeled.
   - "Labeled" means someone already marked what each photo shows (dent, scratch, etc.).
   - You'll use these photos to teach your AI what damage looks like.

---

## Day 1 — Environment & Scaffolding

| Action Item | Desired Outcome | Status |
|---|---|---|
| Initialize Git repo and GitHub | Code is version-controlled and backed up online | Pending |
| Set up FastAPI backend skeleton | Empty backend project ready to build on | Pending |
| Set up Next.js frontend skeleton | Empty frontend project ready to build on | Pending |
| Run Qdrant via Docker Compose | Search database running locally | Pending |
| Create SQLite database schema | Storage ready for users, policies, claims | Pending |
| Add environment variable template file | Settings/secrets kept separate from code | Pending |
| Verify backend-frontend health check works | Confirms frontend and backend can talk | Pending |

**What each action item means:**

1. **Initialize Git repo and GitHub**
   - Git tracks every change you make to your code over time.
   - GitHub is an online backup/storage place for that code.
   - This protects your work and lets you show it off later.

2. **Set up FastAPI backend skeleton**
   - The "backend" is the part of your app that does the thinking.
   - FastAPI is the tool used to build it, written in Python.
   - Right now it's just an empty structure — features get added on later days.

3. **Set up Next.js frontend skeleton**
   - The "frontend" is the part users actually see and click on.
   - Next.js is the tool used to build that visual part.
   - This step just creates a blank starting page to build on.

4. **Run Qdrant via Docker Compose**
   - Qdrant is a special database built for storing the "meaning" of text.
   - Docker Compose is a simple way to start it with one command.
   - This is where your policy text will be stored for smart searching later.

5. **Create SQLite database schema**
   - SQLite is a simple, lightweight database — just a single file.
   - "Schema" means designing what information gets stored (users, policies, claims).
   - This is where regular account and policy details will live.

6. **Add environment variable template file**
   - This is a file listing settings your app needs to run (like keys and addresses).
   - Keeping it separate means secrets aren't hard-coded directly into your code.
   - It's a standard, professional habit worth building from day one.

7. **Verify backend-frontend health check works**
   - This is a simple test: does the frontend talk to the backend at all?
   - If this small test passes, the foundation of the whole project is solid.
   - Everything else you build afterward depends on this connection working.

---

## Day 2 — Auth + Ingestion

| Action Item | Desired Outcome | Status |
|---|---|---|
| Build register/login forms (frontend) | Users can create an account and log in | Pending |
| Build register/login endpoints (backend) | Passwords hashed and checked securely | Pending |
| Build JWT session check (backend) | Backend confirms the login is genuine | Pending |
| Build PDF upload endpoint | Users can upload a policy file | Pending |
| Extract text from PDF | Raw policy words pulled out of the file | Pending |
| Chunk policy text into sections | Long policy split into small, searchable pieces | Pending |
| Upload 6 IRDAI PDFs as test data | Real policies flowing through the pipeline | Pending |

**What each action item means:**

1. **Build register/login forms (frontend)**
   - This is the screen where users type an email and choose a password to sign up.
   - The same form (or a similar one) lets them log back in later.
   - Simple and familiar — no phone, no text message, no external service involved.

2. **Build register/login endpoints (backend)**
   - When someone registers, their password is scrambled ("hashed") before it's ever saved.
   - This means even you can't see anyone's actual password by looking at the database.
   - When they log in, the backend checks the scrambled version matches — never the raw password.

3. **Build JWT session check (backend)**
   - After a successful login, the backend hands back a signed "proof of login" token (a JWT).
   - The app then includes that token on every future request to prove who's asking.
   - This is what keeps your app's login process secure without needing any outside service.

4. **Build PDF upload endpoint**
   - This is the feature that lets a user upload a policy file.
   - "Endpoint" just means a specific web address the file gets sent to.
   - Once uploaded, the file is saved so it can be processed.

5. **Extract text from PDF**
   - PDFs look like documents, but computers can't "read" them directly by default.
   - This step pulls out the raw text that's hidden inside the file.
   - Now the actual words of the policy become usable data.

6. **Chunk policy text into sections**
   - Long documents are split into smaller, bite-sized pieces.
   - Each piece is easier for the AI to search through and understand.
   - Think of it like splitting a book into paragraphs instead of one giant page.

7. **Upload 6 IRDAI PDFs as test data**
   - This runs your real policy documents through everything built so far.
   - It proves the upload → extract → chunk pipeline actually works end to end.
   - These same 6 documents get reused throughout the rest of the project.

---

## Day 3 — Embeddings + Retrieval

| Action Item | Desired Outcome | Status |
|---|---|---|
| Connect to embedding model service | Text can be turned into searchable numbers | Pending |
| Store chunk embeddings in Qdrant | Policy chunks are now searchable by meaning | Pending |
| Build retrieval (search) endpoint | App can find the most relevant policy section | Pending |
| Test retrieval with sample question | Confirms search actually finds the right answer | Pending |

**What each action item means:**

1. **Connect to embedding model service**
   - This links your backend to the "meaning-to-numbers" AI model from Day 0.
   - Once connected, any text chunk can be converted into a list of numbers.
   - This is the setup step needed before real searching can happen.

2. **Store chunk embeddings in Qdrant**
   - Every policy chunk's "number version" gets saved into the Qdrant database.
   - This makes chunks searchable by meaning, not just exact matching words.
   - It's like building a smart index at the back of a book.

3. **Build retrieval (search) endpoint**
   - This feature finds the most relevant policy sections for a given question.
   - It compares the question's "meaning" against all the stored chunks.
   - It returns the closest matches — the sections most likely to hold the answer.

4. **Test retrieval with sample question**
   - This manually checks: does the search actually find the right section?
   - Example: asking about windshield damage should return the windshield coverage clause.
   - If this works well, the foundation of your Q&A feature is solid.

---

## Day 4 — RAG Answers + Chat UI

| Action Item | Desired Outcome | Status |
|---|---|---|
| Write prompt template for answers | AI answers only from real policy text | Pending |
| Build /ask endpoint with citations | Users get answers with a source shown | Pending |
| Build chat interface in frontend | Users can type and see answers on screen | Pending |
| Cache repeated question-answer pairs | Repeated questions answer instantly | Pending |

**What each action item means:**

1. **Write prompt template for answers**
   - A "prompt" is the exact instructions given to the AI model.
   - This template tells the AI: "answer using ONLY these policy sections."
   - This is what stops the AI from making up false information.

2. **Build /ask endpoint with citations**
   - This connects search (Day 3) and the AI model into one Q&A feature.
   - "Citations" means the answer also shows which policy section it came from.
   - Users can trust the answer because they can check the source themselves.

3. **Build chat interface in frontend**
   - This is the actual chat window users type their questions into.
   - It also displays the answer along with a clickable source citation.
   - This becomes the first real, usable feature of your app.

4. **Cache repeated question-answer pairs**
   - If the same question is asked again, reuse the saved answer instead of recomputing.
   - This makes repeated questions feel instant instead of slow.
   - Useful since the AI model runs a bit slowly on a normal computer (no GPU).

---

## Day 5 — Policy Comparison + Gap Analysis

| Action Item | Desired Outcome | Status |
|---|---|---|
| Design structured policy data schema | Clear list of facts to pull from every policy | Pending |
| Extract structured data from each policy | Messy PDF text turned into neat facts | Pending |
| Build compare-two-policies endpoint | App can line up two policies side by side | Pending |
| Build comparison table + summary UI | Users see a clear table and plain-English summary | Pending |
| Test comparison with two policies | Confirms the comparison feature is accurate | Pending |
| Build gap-analysis (single policy) mode | Users can check their one policy against typical plans | Pending |
| Test gap analysis accuracy | Confirms gap-finding logic can be trusted | Pending |

**What each action item means:**

1. **Design structured policy data schema**
   - Decide exactly what facts to pull from every policy (premium, coverage, deductible, etc.).
   - This turns messy document text into neat, comparable categories.
   - Think of it as a form that every policy gets filled into.

2. **Extract structured data from each policy**
   - Run the AI over each policy to fill in that form automatically.
   - This reuses the same search-and-answer pipeline built on Days 3-4.
   - The result is clean, structured facts about each policy, ready to compare.

3. **Build compare-two-policies endpoint**
   - This feature takes two policies and lines up their facts side by side.
   - It highlights what's different between them (price, coverage, deductible, etc.).
   - This is the core of the "compare policies" feature.

4. **Build comparison table + summary UI**
   - This displays the comparison as an easy-to-scan table.
   - It also shows a plain-English summary written by the AI.
   - Example: "Policy B costs more but covers more."

5. **Test comparison with two policies**
   - Run two real policies through the compare feature to check it works.
   - Confirm the table numbers and the written summary actually match the documents.
   - Catch mistakes here before building more features on top of this one.

6. **Build gap-analysis (single policy) mode**
   - This lets a user compare their ONE policy against typical reference policies.
   - It works even if they don't have a second document to upload.
   - It answers the question: "what's missing compared to what's normal?"

7. **Test gap analysis accuracy**
   - Check that comparing a policy to itself shows "no differences" (a sanity check).
   - Check that comparing to a genuinely different policy shows real, correct gaps.
   - This confirms the gap-finding logic is trustworthy before moving on.

---

## Day 6 — YOLO Fine-Tuning

| Action Item | Desired Outcome | Status |
|---|---|---|
| Upload damage dataset to Kaggle | Training data ready on a free cloud GPU | Pending |
| Fine-tune YOLO model on Kaggle GPU | AI model learns to spot car damage types | Pending |
| Evaluate model accuracy (mAP score) | Honest number showing how good the model is | Pending |
| Download trained model weights | Trained model saved onto your own computer | Pending |
| Test model inference on local CPU | Confirms the model works without a graphics card | Pending |

**What each action item means:**

1. **Upload damage dataset to Kaggle**
   - Move the labeled car-damage photos (from Day 0) into a free Kaggle notebook.
   - Kaggle gives free access to a powerful graphics card (GPU) for training.
   - This step just gets your data ready in the right place to train.

2. **Fine-tune YOLO model on Kaggle GPU**
   - "Fine-tuning" means teaching an existing AI model your specific new task.
   - YOLO is the AI model that detects objects — here, types of car damage.
   - After this step, your model can recognize dents, scratches, cracks, and more.

3. **Evaluate model accuracy (mAP score)**
   - This measures how good the trained model actually turned out.
   - "mAP" is a standard score — a higher number means more accurate detections.
   - Knowing this number lets you honestly report how well it performs.

4. **Download trained model weights**
   - "Weights" are the actual trained brain of your damage-detection model.
   - This is a small file you save from Kaggle onto your own computer.
   - Once downloaded, you don't need Kaggle anymore for everyday use.

5. **Test model inference on local CPU**
   - Check that the downloaded model works fine on your own computer.
   - "Inference" just means using the trained model to make a prediction.
   - This confirms the model runs fine without needing a graphics card.

---

## Day 7 — Damage → Coverage Match + Checklist

| Action Item | Desired Outcome | Status |
|---|---|---|
| Build damage classification endpoint | App can tell what type of damage a photo shows | Pending |
| Match damage type to policy coverage | App tells user if their policy covers it | Pending |
| Build dynamic claim checklist generator | App lists documents needed for that specific claim | Pending |
| Build photo upload + results UI | Users can upload a photo and see full results | Pending |

**What each action item means:**

1. **Build damage classification endpoint**
   - This feature takes a photo and returns what kind of damage it shows.
   - Example output: "dent, on the front bumper."
   - This uses the model trained back on Day 6.

2. **Match damage type to policy coverage**
   - Once the damage type is known, check if the user's policy actually covers it.
   - This reuses the search feature built back on Day 3.
   - Example: "your policy covers bumper damage under comprehensive coverage."

3. **Build dynamic claim checklist generator**
   - This creates a list of documents needed to file a claim.
   - The list changes depending on the damage type and policy — not one-size-fits-all.
   - Example: hit-and-run damage needs a police report; other cases don't.

4. **Build photo upload + results UI**
   - This is the screen where users upload a damage photo.
   - It displays the detected damage, coverage match, and checklist all together.
   - This ties together everything built so far into one visual flow.

---

## Day 8 — Agent Tool-Calling Orchestration

| Action Item | Desired Outcome | Status |
|---|---|---|
| Define all agent tool schemas | Every AI "skill" is clearly described | Pending |
| Connect LLM tool-calling to tools | AI can trigger the right skill itself | Pending |
| Route all requests through one agent | One entry point handles any kind of request | Pending |
| Test agent routing across request types | Confirms AI always picks the correct skill | Pending |

**What each action item means:**

1. **Define all agent tool schemas**
   - List out every "skill" your AI assistant can use (search, compare, detect damage, etc.).
   - Each skill is described clearly so the AI knows exactly when to use it.
   - This is like writing a short job description for each tool.

2. **Connect LLM tool-calling to tools**
   - This lets the AI model actually trigger these skills by itself.
   - Instead of you coding "if photo, then do X," the AI decides on its own.
   - This is what makes the app feel like a smart assistant, not a fixed form.

3. **Route all requests through one agent**
   - Combine all the separate features into a single, unified "ask anything" entry point.
   - Users don't need to know which button does what anymore.
   - The AI figures out which skill(s) to use based on what was asked.

4. **Test agent routing across request types**
   - Try different kinds of requests (a question, a comparison, a photo) in one place.
   - Confirm the AI picks the correct tool every time, not just sometimes.
   - This proves the "smart assistant" behavior actually works reliably.

---

## Day 9 — Claim-vs-Pay Advisor + Fraud Signals

| Action Item | Desired Outcome | Status |
|---|---|---|
| Build claim-vs-pay cost advisor | App suggests whether filing a claim is worth it | Pending |
| Build duplicate photo detection check | App flags reused/duplicate damage photos | Pending |
| Build EXIF metadata consistency check | App flags photos with suspicious hidden data | Pending |
| Build image manipulation detection check | App flags signs a photo may be edited | Pending |
| Show advisory flags clearly in UI | Warnings are visible but never look like a verdict | Pending |

**What each action item means:**

1. **Build claim-vs-pay cost advisor**
   - This feature estimates repair cost versus your deductible and bonus loss.
   - It helps answer: "should I file a claim, or just pay out of pocket?"
   - It gives a suggestion, never a final decision — the choice stays with the user.

2. **Build duplicate photo detection check**
   - This checks if the same damage photo was already used in another claim.
   - It's a simple way to catch obviously reused or copied images.
   - It's a flag meant for review, not an automatic accusation.

3. **Build EXIF metadata consistency check**
   - Photos secretly store hidden details, like the date and time they were taken.
   - This checks if those hidden details match the story of the claim.
   - Mismatches get flagged as worth a second look, nothing more.

4. **Build image manipulation detection check**
   - This runs a basic technical check for signs a photo was edited.
   - It's not perfect, but it catches obvious red flags cheaply.
   - Again, this produces a flag, not a verdict.

5. **Show advisory flags clearly in UI**
   - All these warnings are displayed separately from the main answer.
   - This keeps things honest: advice and warnings, never fake authority.
   - Clear labeling avoids confusing a "flag" with a "final decision."

---

## Day 10 — Polish, Evaluation, Docs

| Action Item | Desired Outcome | Status |
|---|---|---|
| Test every feature end-to-end | Confirms the whole app works as one flow | Pending |
| Fix bugs found during testing | App runs smoothly without breaking | Pending |
| Run 60-case evaluation and record results | Proof, with real numbers, that it works | Pending |
| Write README and architecture docs | Anyone can understand and run the project | Pending |
| Push final code to GitHub | Finished project is saved and shareable | Pending |

**What each action item means:**

1. **Test every feature end-to-end**
   - Walk through the entire app from login to final advice, like a real user would.
   - This catches problems that only show up when features are used together.
   - It's the final quality check before calling the project finished.

2. **Fix bugs found during testing**
   - Any problems found in the walkthrough get fixed here.
   - This step usually takes longer than expected — budget real time for it.
   - A working, polished demo matters more than extra unfinished features.

3. **Run 60-case evaluation and record results**
   - Test the app against 60 planned examples and record how well it does.
   - This turns "I think it works" into "here's proof it works."
   - Honest numbers, including mistakes, are more impressive than hiding failures.

4. **Write README and architecture docs**
   - These documents explain what the project does and how it's built.
   - They help anyone — including future you — understand the project quickly.
   - This is often what people read first, so make it clear and complete.

5. **Push final code to GitHub**
   - This saves and publishes your final, working code online.
   - It becomes something you can link to and show others.
   - This marks the project as complete and shareable.

---

## Status Legend

`Pending` — not started · `In Progress` — actively working on it · `Done` — finished and tested · `Blocked` — stuck, needs a decision or fix before continuing
