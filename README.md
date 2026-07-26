# ccai-gov-intelligence

**GCP-native dual-mode AI platform for government operations** — built with Gemini 2.5 Flash, FAISS, and Streamlit on Cloud Run. Designed to show government AI capabilities directly relevant to GTS's OmniDARS and CCAI product verticals.

🔗 **Live URL:** https://ccai-gov-intelligence-786562162192.us-central1.run.app

---

## Architecture

```
User → Streamlit Frontend (Cloud Run, port 8080)
             ↓ Two tabs — Mode 1 and Mode 2
             ↓ in-process imports (no HTTP between processes)

MODE 1: 311 CLASSIFIER
       app/modes/classify_311.py
             ↓
       Gemini 2.5 Flash + response_schema=ClassificationResult (enum fields)
             ↓
       SQLite: citizen_requests table
             ↓
       Returns: department(s), urgency, SLA, work orders, acknowledgment letter

MODE 2: CJIS RAG AGENT
       app/modes/query_cjis.py
             ↓
       app/rag/retriever.py → FAISS IndexFlatIP (built from CJIS PDF, cached to disk)
             ↓ top-5 chunks
       Gemini 2.5 Flash + response_schema=CJISQueryResult
             ↓
       Post-validation: strip citations not in retrieved chunks
             ↓
       SQLite: cjis_queries table
             ↓
       Returns: answer + cited CJIS section references
```

**Critical rule — single process on Cloud Run.** Streamlit is the only listener on port 8080. No FastAPI. All logic imported directly into `streamlit_app.py`.

---

## GCP Services

| Service | Purpose |
|---|---|
| Cloud Run | Single Streamlit container · 1 Gi memory · port 8080 |
| Artifact Registry | Docker image registry (`ccai-gov-intelligence` repo) |
| Cloud Build | Triggered by GitHub Actions push to `main` |
| Secret Manager | `GEMINI_API_KEY` secret |
| Cloud Logging | Structured JSON logs from all modules |

---

## Repo Structure

```
ccai-gov-intelligence/
├── WINDSURF_PROMPT.md               ← build instructions
├── CLAUDE_CONTEXT.md                ← architecture context
├── .github/
│   └── workflows/
│       └── deploy.yml               ← GitHub Actions CI/CD (WIF → Cloud Run)
├── app/
│   ├── streamlit_app.py             ← main entry point, single public process
│   ├── schemas.py                   ← all Pydantic models
│   ├── modes/
│   │   ├── __init__.py
│   │   ├── classify_311.py          ← Mode 1: Gemini structured output
│   │   └── query_cjis.py           ← Mode 2: RAG retrieve + generate
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── build_index.py          ← chunks CJIS PDF, builds FAISS, caches to disk
│   │   ├── retriever.py            ← similarity search, returns top-k chunks
│   │   └── cjis_policy.pdf         ← downloaded at Docker build time
│   ├── data/
│   │   ├── seed_requests.py        ← SQLite DDL + 5 demo complaints
│   │   ├── sample_queries.py       ← 5 demo CJIS questions
│   │   └── gov_intel.db            ← SQLite (baked into image at build)
│   └── requirements.txt
├── Dockerfile
├── docker-compose.yml               ← local dev only
└── README.md
```

---

## Tech Stack

| Component | Choice | Version |
|---|---|---|
| Language | Python | 3.11 |
| Frontend | Streamlit | ≥1.35.0 |
| LLM | Gemini 2.5 Flash | `gemini-2.5-flash` |
| Embeddings | google-genai | `models/text-embedding-004` |
| Data validation | Pydantic | ≥2.0 |
| Vector index | faiss-cpu | ≥1.7.4 |
| PDF parser | pypdf | ≥4.0.0 |
| Data store | SQLite | stdlib |
| Container | Docker | python:3.11-slim |

---

## Mode 1 — 311 Classifier: Demo Queries

| ID | Complaint | What it demonstrates |
|---|---|---|
| REQ-001 | Pothole at 5th & Elm | Single department, medium urgency baseline |
| REQ-002 | Fallen tree + broken streetlight on Maple Ave | Multi-department decomposition (Public Works + Transportation) |
| REQ-003 | Water main burst at Oak & 3rd | **CRITICAL** urgency, 2-hour SLA |
| REQ-004 | Abandoned car + graffiti on Birch St | Low urgency, 7-day SLA |
| REQ-005 | Potholes + streetlights + dumping + clogged drain on Cedar Ln | Maximum decomposition — 4 work orders across 3 departments |

Paste any free-text complaint to see live classification.

---

## Mode 2 — CJIS Q&A: Demo Queries

```
Q-001: What encryption standard does CJIS require for data at rest on mobile devices?
Q-002: How often must agencies conduct security awareness training under CJIS?
Q-003: What are the CJIS requirements for multi-factor authentication?
Q-004: Can cloud service providers store Criminal Justice Information, and what must they comply with?
Q-005: What does CJIS require for incident response planning and reporting?
```

To demo **cannot-answer** behavior, ask something outside CJIS scope:
> "What is the capital of France?"

The system returns `cannot_answer=True` with a referral to the CJIS Systems Officer — demonstrating it knows its limits.

---

## Why This Matters to GTS

**GTS builds OmniDARS** for government courts and administrative law judges. GTS sells to agencies with CJIS, FedRAMP, and NIST compliance requirements.

- **Mode 1** (311 Classifier) maps directly to the citizen intake workflows government agencies automate with OmniDARS and OmniSuite — multi-issue complaint decomposition from free text is a real unsolved problem in existing 311 platforms.
- **Mode 2** (CJIS Q&A) demonstrates the same RAG architecture pattern that powers OmniAssist and OmniRAG — applied to the most compliance-sensitive document in government IT. A law enforcement IT officer asking CJIS questions and getting cited policy section answers is a capability no commercial product offers today.
- **The stack** (Gemini 2.5 Flash, GCP Cloud Run, Artifact Registry) mirrors GTS's Google Cloud CCAI reseller stack — this could be deployed as part of OmniAssist for a government client in an afternoon.

---

## Local Development

```bash
# Set your API key
export GEMINI_API_KEY=your_key_here

# Run with Docker Compose
docker compose up --build

# Or run directly (after installing requirements)
cd app
pip install -r requirements.txt
python data/seed_requests.py        # create SQLite + seed data
streamlit run streamlit_app.py      # starts on port 8501 locally
```

---

## Deployment

Push to `main` → GitHub Actions triggers automatically:
1. Authenticates via Workload Identity Federation
2. Builds Docker image (downloads CJIS PDF, seeds SQLite)
3. Pushes to Artifact Registry (`us-central1`)
4. Deploys to Cloud Run (`us-central1`, 1 Gi, 300s timeout)

**GCP prerequisites** (one-time setup):
- Artifact Registry repo: `ccai-gov-intelligence`
- Secret Manager secret: `GEMINI_API_KEY`
- Service account: `ccai-gov-intelligence-sa` with roles `run.invoker`, `logging.logWriter`, `secretmanager.secretAccessor`
- Workload Identity Federation configured; set GitHub Secrets `WIF_PROVIDER` and `WIF_SERVICE_ACCOUNT`

---

## CJIS Disclaimer

> This tool answers questions about the publicly available FBI CJIS Security Policy document. It does not process, store, or transmit actual Criminal Justice Information. All answers are grounded in the retrieved policy document chunks — citations reference the exact policy section. Consult your agency's CJIS Systems Officer for authoritative compliance guidance.
