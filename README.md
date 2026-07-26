# CCAI Gov Intelligence Platform

A GCP-native dual-mode AI platform for government operations — 311 citizen request classification and CJIS Security Policy Q&A with cited section answers. Deployed on Cloud Run with Gemini 2.5 Flash.

**Live demo (Streamlit):** [https://ccai-gov-intelligence-786562162192.us-central1.run.app](https://ccai-gov-intelligence-786562162192.us-central1.run.app)

**FastAPI backend:** [https://ccai-gov-intelligence-api-786562162192.us-central1.run.app](https://ccai-gov-intelligence-api-786562162192.us-central1.run.app)

**Stack:** Python 3.11 · Streamlit · FastAPI · Uvicorn · Gemini 2.5 Flash · FAISS · pypdf · Pydantic · SQLite · Cloud Run · GitHub Actions

---

## Two Real Unsolved Problems

**Problem 1 — 311 intake breaks on compound complaints.**
Existing 311 platforms (SeeClickFix, Salesforce Public Sector, ServiceNow) handle structured forms well. They fall apart on unstructured, multi-issue complaints. A citizen reporting a fallen tree + broken streetlight + blocked drain in one message requires a human operator to manually decompose it into 3 separate work orders for 3 departments. This agent does it automatically in seconds.

**Problem 2 — CJIS compliance Q&A has no commercial solution.**
The FBI CJIS Security Policy (v6.0, December 2024) is a 200+ page document that every law enforcement agency, government court, and government contractor must comply with. IT security officers search it manually. There is no product that lets them ask questions in plain English and get cited, auditable answers back. This agent is that product.

---

## Architecture

```
User → Streamlit Frontend (Cloud Run, port 8080)
             │  Two tabs — Mode 1 and Mode 2
             │  in-process imports (no HTTP between processes)
             ▼

MODE 1: 311 CLASSIFIER
       app/modes/classify_311.py
             │
             ▼
       Gemini 2.5 Flash
       response_schema=ClassificationResult (enum-constrained fields)
       temperature=0, thinking disabled
             │
             ▼
       Returns: department(s) · urgency · SLA hours · work orders · acknowledgment letter
       Writes to: SQLite citizen_requests table

MODE 2: CJIS RAG AGENT
       app/modes/query_cjis.py
             │
             ▼
       app/rag/retriever.py
       FAISS IndexFlatIP over chunked CJIS v6.0 PDF (~750 chunks)
       Similarity threshold: 0.3 (below → cannot_answer, no Gemini call)
             │  top-5 chunks
             ▼
       Gemini 2.5 Flash + response_schema=CJISQueryResult
             │
             ▼
       Post-validation: strip any citation whose section_id
       is not in the retrieved chunks
             │
             ▼
       Returns: answer + cited CJIS section references
       Writes to: SQLite cjis_queries table
```

**Two Cloud Run services:**
- **Streamlit** (`ccai-gov-intelligence`) — standalone demo UI, port 8080, imports mode logic directly
- **FastAPI** (`ccai-gov-intelligence-api`) — HTTP backend for the `compliance-intelligence-platform` wrapper, port 8080, exposes `POST /classify`, `POST /query-cjis`, `GET /health`

---

## Mode 1 — 311 Citizen Request Classifier

**Input:** Any free-text citizen complaint — messy, multi-issue, unstructured.

**Output:** Department routing + urgency + SLA hours + per-department work orders + acknowledgment letter.

All output fields are Pydantic enum-constrained. Gemini cannot invent a department or urgency level that isn't in the schema — this is the primary mechanism for consistent, non-drifting output.

### Demo Complaints

| ID | Complaint | What It Demonstrates |
|---|---|---|
| REQ-001 | Pothole at 5th & Elm | Single department baseline |
| REQ-002 | Fallen tree + broken streetlight on Maple Ave | Multi-department decomposition |
| REQ-003 | Water main burst at Oak & 3rd | CRITICAL urgency, 2-hour SLA |
| REQ-004 | Abandoned car + graffiti on Birch St | Low urgency, 7-day SLA |
| REQ-005 | Potholes + streetlights + dumping + clogged drain on Cedar Ln | Maximum decomposition — 4 work orders, 3 departments |

The text input also accepts any free-form complaint typed live — the classifier handles inputs it has never seen.

---

## Mode 2 — CJIS Security Policy Q&A

**Input:** Any natural language question about CJIS compliance requirements.

**Output:** Direct answer + cited CJIS section references (e.g., "CJIS v6.0 Section 5.5.6").

### RAG Design

- **Source document:** FBI CJIS Security Policy v6.0 (released December 27, 2024 — most current version; FBI audits against v6.0 beginning October 2025)
- **Chunking:** Split on section headers (`^\d+\.\d+(\.\d+)*\s` pattern) — each chunk preserves its section ID for citation
- **Embedding model:** `models/gemini-embedding-001` via google-genai SDK
- **Vector index:** `FAISS IndexFlatIP` (cosine similarity over L2-normalized vectors) — exact search, no approximation
- **Index lifecycle:** Built at first app startup, cached to disk. Never rebuilt if cache exists. Never built at Docker build time (API key not available during Cloud Build).
- **Citation validation:** After every Gemini call, any `section_id` in the response that does not appear in the retrieved chunks is stripped. Hallucinated section references are structurally impossible to surface to the user.
- **Cannot-answer:** If no retrieved chunk scores above 0.3 similarity, `cannot_answer=True` is returned immediately without calling Gemini. The system knows its limits.

### Demo Questions

| ID | Question | What It Demonstrates |
|---|---|---|
| Q-001 | What encryption standard does CJIS require for data at rest on mobile devices? | Technical control, specific section |
| Q-002 | How often must agencies conduct security awareness training under CJIS? | Training requirement |
| Q-003 | What are the CJIS requirements for multi-factor authentication? | MFA controls, multiple citations |
| Q-004 | Can cloud service providers store Criminal Justice Information, and what must they comply with? | Vendor/cloud policy |
| Q-005 | What does CJIS require for incident response planning and reporting? | IR policy |

To demonstrate cannot-answer: ask **"What is the capital of France?"** — the system returns `cannot_answer=True` with a referral to the CJIS Systems Officer. The index has no relevant chunks for that query and the agent does not fabricate an answer.

---

## GCP Services

| Service | Purpose |
|---|---|
| Cloud Run | Two services: Streamlit demo + FastAPI backend · 1 Gi memory each · port 8080 · 300s timeout |
| Artifact Registry | Docker image (`ccai-gov-intelligence` repo, us-central1) |
| Secret Manager | `GEMINI_API_KEY` — never hardcoded |
| Cloud Build | Triggered by GitHub Actions via Workload Identity Federation |
| Cloud Logging | Structured JSON logs from all modules |
| IAM | `ccai-gov-intelligence-sa` with least-privilege roles only |

**Service account roles:**
- `roles/run.invoker`
- `roles/logging.logWriter`
- `roles/secretmanager.secretAccessor`

**Cloud Run flags required:**
- `--memory=1Gi` — FAISS index requires it
- `--timeout=300` — first-run index build takes 60–90 seconds
- `--concurrency=10`

---

## Repository Structure

```
ccai-gov-intelligence/
├── .github/workflows/
│   ├── deploy.yml                   ← Streamlit Cloud Run deploy
│   └── deploy-api.yml              ← FastAPI Cloud Run deploy
├── app/
│   ├── streamlit_app.py             ← standalone demo UI, 2 tabs (unchanged)
│   ├── schemas.py                   ← all Pydantic models (built first)
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py                 ← FastAPI: /classify, /query-cjis, /health
│   ├── modes/
│   │   ├── classify_311.py          ← Mode 1: Gemini structured output
│   │   └── query_cjis.py           ← Mode 2: RAG retrieve + generate
│   ├── rag/
│   │   ├── build_index.py          ← chunks CJIS PDF, builds FAISS, caches
│   │   ├── retriever.py            ← similarity search, returns top-k chunks
│   │   └── cjis_policy.pdf         ← downloaded at Docker build time
│   ├── data/
│   │   ├── seed_requests.py        ← SQLite DDL + 5 demo complaints
│   │   ├── sample_queries.py       ← 5 demo CJIS questions
│   │   └── gov_intel.db            ← SQLite baked into image at build
│   └── requirements.txt
├── Dockerfile                       ← Streamlit image
├── Dockerfile.api                   ← FastAPI image
├── docker-compose.yml
└── README.md
```

---

## Local Development

```bash
# Set your API key
export GEMINI_API_KEY=your_key_here

# Install dependencies
pip install -r app/requirements.txt

# Seed SQLite
python app/data/seed_requests.py

# Run (FAISS index builds on first startup, ~60s, then cached)
streamlit run app/streamlit_app.py
```

Or with Docker Compose:

```bash
export GEMINI_API_KEY=your_key_here
docker compose up --build
# Streamlit at http://localhost:8080
# FastAPI at  http://localhost:8001
# API docs at http://localhost:8001/docs
```

---

## How This Connects to GTS Products

**Mode 1** maps directly to citizen intake workflows GTS automates with OmniDARS and OmniSuite. Multi-issue complaint decomposition from free text is a real operational gap in every major 311 platform — this agent closes it.

**Mode 2** demonstrates the same RAG architecture pattern powering OmniAssist and OmniRAG, applied to the most compliance-sensitive document in government IT. The pattern — chunk a source document, embed, retrieve, generate with citations, validate — is identical to how OmniAssist answers questions against a client's policy library. This could be deployed for a government client in an afternoon.

The stack (Gemini 2.5 Flash, Cloud Run, Artifact Registry) mirrors GTS's Google Cloud CCAI reseller stack.

---

## CJIS Disclaimer

This tool answers questions about the publicly available FBI CJIS Security Policy document. It does not process, store, or transmit actual Criminal Justice Information. All answers are grounded in retrieved policy document chunks — citations reference the exact policy section. Consult your agency's CJIS Systems Officer for authoritative compliance guidance.
