# CLAUDE_CONTEXT.md
# Government Citizen Intelligence Platform — Architecture & Decision Context
# READ THIS FIRST BEFORE DOING ANYTHING IN THIS CHAT

---

## WHO THIS IS FOR

- **Developer:** Abhishek (Abhi) Yadav, Dallas TX
- **Interview:** Monday 3 PM CST — Ram Agarwal (CEO/CTO), Global Technology Solutions Inc. (GTS)
- **GitHub:** https://github.com/Xaaby
- **Repo:** `ccai-gov-intelligence` (public)
- **Previous projects (complete, live):**
  - `gcp-devops-compliance-agent` — Backend: `https://gcp-devops-backend-786562162192.us-central1.run.app`
  - GCP project: `earnest-sight-503519-t5`
- **Tooling:** Windsurf (AI IDE) builds code. Claude (claude.ai) designs architecture, reviews code, answers questions.
- **Abhi's coding style:** Primarily vibe-coder — Windsurf writes ~90%, Abhi reviews and can debug live.

---

## THE INTERVIEW CONTEXT

- **Company:** Global Technology Solutions Inc. (GTS)
- **GTS identity:** Genesys Gold Partner + Google Cloud CCAI Reseller + AWS Advanced Partner
- **Products:** OmniAssist (Vertex AI RAG agent assist), OmniBots, OmniRAG, OmniDARS (government courts/administrative law judges), OmniSuite
- **Clients:** Government agencies, courts, hospitals, universities — FedRAMP, NIST, CJIS, SOC 2
- **Ram Agarwal:** Founder/CEO/CTO — still reads PRs, values builders, speed-to-value, compliance-aware engineering. Asked about agents on the phone.
- **Aaron Schroeder:** Director of AI — evaluates RAG quality, evaluation frameworks, agentic AI. Second round — this project is especially relevant for Aaron.
- **Monday call purpose:** Ram opens GitHub, walks through projects live, sees how Abhi thinks.

---

## WHY THIS PROJECT — THE POSITIONING

**Two genuine unsolved problems this project addresses:**

**Problem 1 — 311 intake is slow and manual**
Existing 311 platforms (SeeClickFix, Salesforce Public Sector, ServiceNow) handle structured forms well but fail on unstructured, compound complaints. A citizen reporting a fallen tree + broken streetlight + blocked drain requires a human operator to decompose it into 3 separate work orders for 3 departments. This is fully automatable and nobody has built a Gemini-native version of it.

**Problem 2 — CJIS compliance Q&A is genuinely unsolved**
The FBI CJIS Security Policy (v6.0, released December 2024) is a 200+ page document that every law enforcement agency, government court, and government contractor must comply with. IT security officers spend hours searching it manually. There is no commercial product that lets them ask questions in plain English and get cited, accurate answers back. This is the single most differentiated capability across all three bundles we researched.

**Why Ram cares:**
GTS builds OmniDARS for government courts and administrative law judges. GTS sells to agencies with CJIS compliance requirements. This project speaks directly to the government vertical that GTS already operates in — and shows the RAG architecture pattern that Aaron Schroeder evaluates.

---

## WHAT WE ARE BUILDING

A GCP-native dual-mode AI platform:

**Mode 1 — 311 Citizen Request Classifier**
- Input: Free-text citizen complaint (messy, multi-issue, unstructured)
- Output: Department routing + urgency + SLA + per-department work orders + acknowledgment letter
- Powered by: Gemini 2.5 Flash structured output with strict Pydantic enum schema
- Consistency: Very high — enum-constrained output barely drifts at temperature=0

**Mode 2 — CJIS Security Policy Q&A Agent**
- Input: Natural language question about CJIS compliance requirements
- Output: Direct answer + cited CJIS section references (e.g., "CJIS v6.0 Section 5.5.6")
- Powered by: FAISS in-memory vector index over chunked CJIS PDF + Gemini 2.5 Flash generation
- Consistency: High — retrieval from fixed index is deterministic; answer phrasing may vary slightly but citations are grounded

---

## ARCHITECTURE — LOCKED, DO NOT CHANGE WITHOUT ASKING

```
User → Streamlit Frontend (Cloud Run, port 8080)
             ↓ Two tabs
             ↓ in-process imports (no HTTP between processes)

MODE 1: 311 CLASSIFIER
       modes/classify_311.py
             ↓
       Gemini 2.5 Flash + response_schema=ClassificationResult (enum fields)
             ↓
       SQLite: citizen_requests table

MODE 2: CJIS RAG AGENT
       modes/query_cjis.py
             ↓
       rag/retriever.py → FAISS index (built from CJIS PDF, cached to disk)
             ↓ top-5 chunks
       Gemini 2.5 Flash + response_schema=CJISQueryResult
             ↓
       Post-validation: strip citations not in retrieved chunks
             ↓
       SQLite: cjis_queries table
```

**CRITICAL RULE: Single process on Cloud Run.** Streamlit is the only public process on port 8080. No FastAPI. All logic imported directly into `streamlit_app.py`. Two processes = demo-breaking port conflict.

**FAISS index rule:** Built at first app startup, cached to disk. Never rebuilt if cache exists. Never built at Docker build time (GEMINI_API_KEY is not available during Cloud Build).

---

## TECH STACK — EVERY VERSION LOCKED

| Component | Choice | Version/Config |
|---|---|---|
| Language | Python | 3.11 |
| Frontend | Streamlit | >=1.35.0 |
| Agent SDK | google-genai (native) | >=0.8.0 |
| LLM | Gemini 2.5 Flash | `gemini-2.5-flash` |
| Embeddings | google-genai embed API | `models/text-embedding-004` |
| Data validation | Pydantic | >=2.0 |
| Data store | SQLite | Built-in Python stdlib |
| Vector index | FAISS (faiss-cpu) | >=1.7.4 |
| PDF parser | pypdf | >=4.0.0 |
| Container | Docker | python:3.11-slim base |
| Registry | GCP Artifact Registry | us-central1 |
| Hosting | GCP Cloud Run | us-central1, port 8080, 1Gi memory |
| CI/CD | GitHub Actions + Cloud Build | Workload Identity Federation |
| Secrets | GCP Secret Manager | secret: GEMINI_API_KEY |
| Logs | GCP Cloud Logging | structured JSON |

**DO NOT USE:** LangChain, LlamaIndex, Vertex AI SDK, FastAPI, ChromaDB, Pinecone, any managed vector DB, Redis, Firestore, Cloud SQL.

---

## REPO STRUCTURE

```
ccai-gov-intelligence/
├── CLAUDE_CONTEXT.md
├── WINDSURF_PROMPT.md
├── .github/
│   └── workflows/
│       └── deploy.yml
├── app/
│   ├── streamlit_app.py            ← single public process, 2 tabs
│   ├── schemas.py                  ← ALL Pydantic models (built first)
│   ├── modes/
│   │   ├── __init__.py
│   │   ├── classify_311.py         ← Mode 1: Gemini structured output
│   │   └── query_cjis.py          ← Mode 2: RAG retrieve + generate
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── build_index.py         ← chunks PDF, builds FAISS, caches to disk
│   │   ├── retriever.py           ← similarity search, returns top-k chunks
│   │   └── cjis_policy.pdf        ← CJIS v6.0 PDF (downloaded at Docker build)
│   ├── data/
│   │   ├── seed_requests.py       ← seeds SQLite with 5 sample complaints
│   │   ├── sample_queries.py      ← 5 sample CJIS questions for demo
│   │   └── gov_intel.db           ← SQLite (baked into image at build)
│   └── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## THE TWO MODES — SPECIFICATIONS

### Mode 1: classify_311_request

```python
def classify_311_request(request_id: str, complaint_text: str) -> ClassificationResult:
```

- Input: Any free-text citizen complaint
- Gemini config: `response_schema=ClassificationResult`, `temperature=0`, `thinking_budget=0`
- Output: Department enum(s), urgency enum, SLA hours, list of WorkOrders, acknowledgment letter
- Writes to: `citizen_requests` SQLite table
- Consistency: Very high — all output fields are enum-constrained

**The key demo value:** Multi-department decomposition. A single complaint with 3 issues → 3 separate WorkOrder objects, each with its own department, urgency, and action type. No existing 311 tool does this automatically from free text.

### Mode 2: query_cjis_policy

```python
def query_cjis_policy(query_id: str, question: str) -> CJISQueryResult:
```

- Input: Any natural language question about CJIS requirements
- Flow: embed question → FAISS search → retrieve top-5 chunks → Gemini generate with citations
- Output: Answer text + list of CJISCitation objects (section_id, title, version, relevance)
- Post-validation: Strip any citation whose section_id is not in the retrieved chunks
- Cannot-answer handling: If top similarity score < 0.3, return `cannot_answer=True` immediately without calling Gemini
- Writes to: `cjis_queries` SQLite table
- Consistency: High — retrieval from fixed index is deterministic; Gemini phrasing may vary slightly

**The key demo value:** Cited answers. "Per CJIS v6.0 Section 5.13.1, agencies must implement AES-256 encryption..." This is verifiable, auditable, and nothing like a regular chatbot.

---

## PYDANTIC SCHEMAS — KEY MODELS

```python
# Mode 1
class Department(str, Enum): PUBLIC_WORKS, TRANSPORTATION, UTILITIES, PARKS_AND_RECREATION, ...
class UrgencyLevel(str, Enum): CRITICAL, HIGH, MEDIUM, LOW
class ActionType(str, Enum): FIELD_INSPECTION, MAINTENANCE_CREW_DISPATCH, INVESTIGATION, ...
class WorkOrder(BaseModel): department, urgency, sla_hours, action_type, issue_description
class ClassificationResult(BaseModel): request_id, primary_department, urgency, sla_hours, work_orders, acknowledgment_letter, classification_confidence

# Mode 2
class CJISCitation(BaseModel): section_id, section_title, policy_version, relevance
class CJISQueryResult(BaseModel): query_id, question, answer, citations, confidence, cannot_answer
```

Full definitions in WINDSURF_PROMPT.md and in `app/schemas.py`.

---

## RAG DESIGN — CRITICAL DETAILS

**CJIS PDF:** FBI CJIS Security Policy v6.0 (released December 27, 2024). Public document. ~200 pages. Downloaded at Docker build time.

**Chunking strategy (critical for citation accuracy):**
- Split on section headers: lines matching `^\d+\.\d+(\.\d+)*\s` pattern
- Each chunk starts with its section number — this is what gets cited
- Never split a section header across chunks
- Max chunk size 1500 chars — split at paragraph boundaries, preserve section_id in each sub-chunk

**Embedding model:** `models/text-embedding-004` via google-genai SDK. Dimension: 768.

**FAISS index:** `IndexFlatIP` (inner product on L2-normalized vectors = cosine similarity). No approximate search — flat index is exact and fast enough for ~500-800 CJIS chunks.

**Citation validation (mandatory):** After Gemini generates a `CJISQueryResult`, validate that every `citation.section_id` actually appeared in the retrieved chunks. Strip any that didn't. This prevents hallucinated section references which would be immediately obvious to a CJIS-savvy evaluator.

**Cannot-answer behavior:** If no retrieved chunk has similarity > 0.3, return `cannot_answer=True` without calling Gemini. Show a clear message in the UI. This is a feature, not a bug — it demonstrates the system knows its limits.

---

## DEMO DATA

**5 pre-built 311 complaints (Mode 1 dropdown):**

| ID | Complaint Type | Key Demo Value |
|---|---|---|
| REQ-001 | Single issue (pothole) | Clean, simple baseline |
| REQ-002 | Two departments (fallen tree + streetlight) | Multi-work-order output |
| REQ-003 | Critical urgency (water main burst) | CRITICAL badge, 2-hour SLA |
| REQ-004 | Low urgency (abandoned car + graffiti) | Low urgency, 7-day SLA |
| REQ-005 | Five-department complex complaint | Maximum work-order decomposition |

**5 pre-built CJIS questions (Mode 2 dropdown):**

| ID | Question | Key Demo Value |
|---|---|---|
| Q-001 | Mobile device encryption requirement | Technical control, specific section |
| Q-002 | Security awareness training frequency | Training requirement |
| Q-003 | Multi-factor authentication requirements | MFA controls |
| Q-004 | Cloud provider data storage rules | Vendor/cloud policy |
| Q-005 | Incident response planning requirements | IR policy |

---

## GCP SERVICES USED

| Service | Purpose |
|---|---|
| Cloud Run | Single Streamlit container, 1Gi memory |
| Artifact Registry | Docker image (repo: ccai-gov-intelligence) |
| Cloud Build | Triggered by GitHub Actions |
| Secret Manager | GEMINI_API_KEY |
| Cloud Logging | Structured JSON logs |
| IAM | Service account: ccai-gov-intelligence-sa |

**Service Account Roles:**
- roles/run.invoker
- roles/logging.logWriter
- roles/secretmanager.secretAccessor

**Cloud Run flags required:**
- `--memory=1Gi` — FAISS needs it
- `--timeout=300` — first-run index build can take 60-90 seconds
- `--concurrency=10`

---

## GCP PLACEHOLDERS — SUBSTITUTE BEFORE DEPLOYING

- `YOUR_PROJECT_ID` → `earnest-sight-503519-t5`
- `YOUR_WIF_PROVIDER` → Workload Identity Federation provider resource name
- `YOUR_WIF_SERVICE_ACCOUNT` → SA email used for WIF
- `LIVE_URL` → assigned after first Cloud Run deploy

---

## KEY DECISIONS MADE — DO NOT REVISIT

1. **Single process on Cloud Run** — Streamlit only, no FastAPI. Non-negotiable.
2. **FAISS in-container, not managed vector DB** — faiss-cpu runs in the container. No Pinecone, no Vertex AI Vector Search, no ChromaDB managed service.
3. **FAISS index built at first startup, not at Docker build time** — GEMINI_API_KEY is not available during Cloud Build. Build at runtime, cache to disk.
4. **Citation validation is mandatory** — strip hallucinated section refs after every Gemini call.
5. **Cannot-answer is a feature** — similarity threshold < 0.3 → return `cannot_answer=True` immediately. Never force an answer from irrelevant chunks.
6. **CJIS v6.0 is the source document** — released December 27, 2024. Most current version. FBI audits against v6.0 beginning October 2025.
7. **Temperature=0 + thinking disabled** — on all Gemini calls.
8. **Enum-constrained Pydantic schemas** — Mode 1 output fields are enums. This is the primary determinism mechanism for Mode 1.
9. **5 pre-built inputs per mode** — controls demo variables, eliminates unexpected input risk during live demo.
10. **CJIS disclaimer in README** — this tool answers questions about the public policy document only. It does not process actual Criminal Justice Information.

---

## DEMO ORDER — DO NOT CHANGE

**Tab 1 — 311 Classifier:**
1. REQ-005 (5-department) → Run → Show 3+ work orders, different badges, acknowledgment letter
2. REQ-003 (critical urgency) → Run → CRITICAL badge, 2-hour SLA → "Watch the urgency detection"
3. Type a new complaint live → Run → "Works on any input"
4. Show SQLite history expander → "Logged and auditable"

**Tab 2 — CJIS Q&A:**
1. Q-001 (encryption) → Search → Show answer + cited section numbers
2. Q-003 (MFA) → Search → Show multiple citations
3. Type something outside CJIS scope → Search → Show cannot_answer state → "It knows what it doesn't know"
4. Re-run Q-001 → Identical result → "Grounded in the document, not hallucinated"

**Lead with Mode 1 (classification) — it's immediately understandable. Mode 2 (CJIS) is the impressive one — save it for second.**

---

## WHAT TO SAY TO RAM

- **Why this project?** "GTS builds OmniDARS for government courts. This platform shows the two AI capabilities government clients need most — instant citizen intake classification and CJIS compliance Q&A. There is no commercial product today that lets a law enforcement IT officer ask CJIS questions and get cited section references back. I built that."
- **Why cited answers?** "Because government agencies get audited. An answer that says 'per CJIS v6.0 Section 5.13.1' is defensible. An answer with no citation is a liability."
- **Why Mode 1?** "311 platforms handle structured forms fine. They fall apart on unstructured, compound complaints. A citizen reports a pothole, a broken streetlight, and a flooded drain in one message — a human operator has to decompose that. This agent does it in 3 seconds and routes each issue to the right department automatically."
- **How would this work in production?** "Mode 1 connects to your city's CRM or 311 intake form. Mode 2 connects to any policy document — CJIS today, your OmniDARS policy library tomorrow. The RAG architecture is identical to how OmniAssist works."
- **Why Gemini?** "Same model family GTS resells via Google Cloud CCAI. Architecture consistency — this could be deployed as part of OmniAssist for a government client in an afternoon."

---

## RULES FOR CLAUDE IN THIS PROJECT

1. Write complete files, not snippets
2. Flag any GCP placeholder that needs substitution before deploying
3. Keep code clean: type hints, docstrings, consistent formatting — Ram reads PRs
4. Ask before making ANY architectural change
5. If anything exceeds GCP free tier limits, say so immediately
6. Do not suggest adding services not listed
7. The Gemini SDK pattern in this file is confirmed correct — do not change it
8. Citation validation in `query_cjis.py` is mandatory — never skip it
9. Cannot-answer handling is mandatory — never force Gemini to answer from irrelevant chunks
10. FAISS index must be built at runtime, not at Docker build time
11. Single process on Cloud Run is non-negotiable
12. Cloud Run deploy must include `--memory=1Gi` — FAISS requires it

---

## CHAT-COMPASS STATUS

Fresh chat. Message count resets here.
Previous chat accomplished: full research (Claude + Gemini), bundle evaluation A/B/C, both bundles fully architected and documented.
This chat purpose: build Bundle B — generate code files, review Windsurf output, answer architecture questions, support deployment.

🔴 **Chat-Compass:** Both WINDSURF_PROMPT.md and CLAUDE_CONTEXT.md for Bundle B are now complete — this is a hard fork point. Start a new chat, paste this CLAUDE_CONTEXT.md as your first message, and begin building with Windsurf from Step 1 (schemas.py).
