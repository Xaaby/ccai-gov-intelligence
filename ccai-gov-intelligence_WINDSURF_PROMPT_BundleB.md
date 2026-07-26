# WINDSURF_PROMPT.md
# Government Citizen Intelligence Platform — Complete Build Instructions
# READ THIS ENTIRE FILE BEFORE WRITING A SINGLE LINE OF CODE

---

## WHO YOU ARE BUILDING FOR

- **Developer:** Abhishek (Abhi) Yadav, Dallas TX
- **Interview:** Monday 3 PM CST — Ram Agarwal (CEO/CTO), Global Technology Solutions Inc. (GTS)
- **GTS Identity:** Genesys Gold Partner + Google Cloud CCAI Reseller + Government tech (OmniDARS for courts)
- **GitHub:** https://github.com/Xaaby
- **Repo to create:** `ccai-gov-intelligence` (public)
- **Your job:** Write complete, working, production-quality code. Abhi reviews. No snippets. No TODOs. No placeholders in logic.

---

## WHAT YOU ARE BUILDING

A GCP-native dual-mode AI platform for government operations:

**Mode 1 — 311 Citizen Request Classifier**
A citizen types a messy, multi-issue complaint in plain English. The agent classifies it into the right government department(s), assigns urgency and SLA, decomposes multi-department requests into separate work orders, and drafts a personalized acknowledgment letter back to the citizen. Instant. Deterministic. No drift.

**Mode 2 — CJIS Security Policy Q&A Agent**
A law enforcement IT officer types a question in plain English ("What does CJIS require for mobile device encryption?"). The agent retrieves the answer from the official FBI CJIS Security Policy PDF using RAG, and returns a cited, accurate response with the exact policy section number. No hallucination — every answer is grounded in the document.

**Why this matters to GTS:**
- GTS builds OmniDARS for government courts and administrative law judges
- GTS sells to government agencies with CJIS, FedRAMP, NIST compliance requirements
- This demo shows GTS can build AI that works for government — reliable, cited, auditable

**This is NOT a chatbot. This is a dual-mode structured AI agent with deterministic classification and cited RAG retrieval.**

---

## ARCHITECTURE — LOCKED, DO NOT DEVIATE

```
User → Streamlit Frontend (Cloud Run, port 8080)
             ↓ Two tabs — Mode 1 and Mode 2
             ↓ in-process imports (no HTTP between processes)

MODE 1: 311 CLASSIFIER
       classify_311_request()
             ↓
       Gemini 2.5 Flash + Pydantic response_schema (enum fields)
             ↓
       SQLite: citizen_requests table
             ↓
       Returns: department(s), urgency, SLA, work orders, acknowledgment letter

MODE 2: CJIS RAG AGENT
       query_cjis_policy()
             ↓
       FAISS in-memory index (pre-built from CJIS PDF at container startup)
             ↓ retrieve top-k chunks
       Gemini 2.5 Flash + citation enforcement
             ↓
       SQLite: cjis_queries table
             ↓
       Returns: answer + cited section references (e.g., "CJIS v6.0 Section 5.5.6")
```

**CRITICAL ARCHITECTURE RULE:** Streamlit is the ONLY public process. It runs on `$PORT` (8080 on Cloud Run). No FastAPI. No separate backend. Import all logic directly into `streamlit_app.py`. This is the single most important rule — two processes on Cloud Run = demo-breaking port conflict.

---

## TECH STACK — EVERY VERSION LOCKED

| Component | Choice | Version |
|---|---|---|
| Language | Python | 3.11 |
| Frontend | Streamlit | >=1.35.0 |
| Agent SDK | google-genai (native) | >=0.8.0 |
| LLM | Gemini 2.5 Flash | `gemini-2.5-flash` |
| Data validation | Pydantic | >=2.0 |
| Data store | SQLite | Built-in Python stdlib |
| Vector index | FAISS (faiss-cpu) | >=1.7.4 |
| Embeddings | google-genai embed API | `models/text-embedding-004` |
| PDF parsing | pypdf | >=4.0.0 |
| Container base | python:3.11-slim | Docker |
| Registry | GCP Artifact Registry | us-central1 |
| Hosting | GCP Cloud Run | us-central1, port 8080 |
| CI/CD | GitHub Actions + Cloud Build | Workload Identity Federation |
| Secrets | GCP Secret Manager | secret: GEMINI_API_KEY |
| Logs | GCP Cloud Logging | structured JSON |

**DO NOT USE:** LangChain, LlamaIndex, Vertex AI SDK, FastAPI, ChromaDB, Pinecone, any managed vector database, Redis, Firestore, Cloud SQL.

---

## REPO STRUCTURE — EXACT, NO FILES ADDED OR REMOVED

```
ccai-gov-intelligence/
├── CLAUDE_CONTEXT.md                  ← context for Claude
├── WINDSURF_PROMPT.md                 ← this file
├── .github/
│   └── workflows/
│       └── deploy.yml                 ← GitHub Actions CI/CD
├── app/
│   ├── streamlit_app.py               ← main entry point, single public process, 2 tabs
│   ├── schemas.py                     ← ALL Pydantic models (build this FIRST)
│   ├── modes/
│   │   ├── __init__.py
│   │   ├── classify_311.py            ← Mode 1: 311 classifier (Gemini structured output)
│   │   └── query_cjis.py             ← Mode 2: CJIS RAG agent (FAISS + Gemini)
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── build_index.py            ← chunks CJIS PDF + builds FAISS index at startup
│   │   ├── retriever.py              ← FAISS similarity search + chunk return
│   │   └── cjis_policy.pdf           ← CJIS Security Policy v6.0 PDF (downloaded at build)
│   ├── data/
│   │   ├── seed_requests.py          ← seeds SQLite with 5 sample 311 requests
│   │   ├── sample_queries.py         ← 5 sample CJIS questions for demo
│   │   └── gov_intel.db              ← SQLite (baked into Docker image at build)
│   └── requirements.txt
├── Dockerfile                         ← single image, Streamlit on 8080
├── docker-compose.yml                 ← local dev only
└── README.md                          ← architecture, live URL, demo queries
```

---

## BUILD ORDER — FOLLOW THIS EXACTLY

Build files in this sequence. Do not skip ahead.

---

### STEP 1 — schemas.py (BUILD THIS FIRST — EVERYTHING ELSE IMPORTS FROM IT)

```python
# app/schemas.py
"""
All Pydantic data models for the Government Citizen Intelligence Platform.
Mode 1 (311 Classifier) and Mode 2 (CJIS RAG) schemas defined here.
Gemini response_schema uses these models directly.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# ============================================================
# MODE 1 — 311 CLASSIFIER SCHEMAS
# ============================================================

class Department(str, Enum):
    """Fixed enum of city/county departments. Gemini must pick from these only."""
    PUBLIC_WORKS = "Public Works"
    TRANSPORTATION = "Transportation"
    PARKS_AND_RECREATION = "Parks and Recreation"
    UTILITIES = "Utilities"
    BUILDING_AND_SAFETY = "Building and Safety"
    ENVIRONMENTAL_SERVICES = "Environmental Services"
    POLICE = "Police"
    FIRE = "Fire"
    HEALTH_SERVICES = "Health Services"
    ANIMAL_CONTROL = "Animal Control"
    HOUSING = "Housing"
    OTHER = "Other"

class UrgencyLevel(str, Enum):
    """Urgency classification with SLA hours."""
    CRITICAL = "CRITICAL"       # Life/safety risk — respond in 2 hours
    HIGH = "HIGH"               # Property damage risk — respond in 24 hours
    MEDIUM = "MEDIUM"           # Quality of life issue — respond in 72 hours
    LOW = "LOW"                 # Cosmetic/informational — respond in 7 days

class ActionType(str, Enum):
    """What kind of government action is required."""
    FIELD_INSPECTION = "Field Inspection"
    MAINTENANCE_CREW = "Maintenance Crew Dispatch"
    INVESTIGATION = "Investigation"
    PERMIT_REVIEW = "Permit Review"
    REFERRAL = "Referral to Agency"
    INFORMATION_ONLY = "Information Only"

class WorkOrder(BaseModel):
    """A single department's work item decomposed from a multi-issue complaint."""
    department: Department
    urgency: UrgencyLevel
    sla_hours: int = Field(
        description="Hours within which this department must respond: CRITICAL=2, HIGH=24, MEDIUM=72, LOW=168"
    )
    action_type: ActionType
    issue_description: str = Field(
        description="One sentence describing the specific issue this department must address"
    )

class ClassificationResult(BaseModel):
    """Complete classification result for a 311 citizen request."""
    request_id: str
    primary_department: Department
    urgency: UrgencyLevel
    sla_hours: int
    work_orders: List[WorkOrder] = Field(
        description="One work order per department involved. Multi-issue complaints produce multiple work orders."
    )
    acknowledgment_letter: str = Field(
        description="Professional 3-4 sentence acknowledgment letter addressed to the citizen. Must reference the specific issue reported, the department(s) assigned, and the response timeline."
    )
    classification_confidence: str = Field(
        description="One of: HIGH, MEDIUM, LOW — based on how clearly the complaint maps to departments"
    )


# ============================================================
# MODE 2 — CJIS RAG SCHEMAS
# ============================================================

class CJISCitation(BaseModel):
    """A single policy citation returned with a CJIS answer."""
    section_id: str = Field(
        description="CJIS policy section number, e.g., '5.5.6' or '5.13.1.2'"
    )
    section_title: str = Field(
        description="Title of the section as it appears in the CJIS document"
    )
    policy_version: str = Field(
        description="CJIS version this citation comes from, e.g., 'CJIS Security Policy v6.0'"
    )
    relevance: str = Field(
        description="One sentence explaining why this section is relevant to the question"
    )

class CJISQueryResult(BaseModel):
    """Complete result for a CJIS policy question."""
    query_id: str
    question: str
    answer: str = Field(
        description="Direct, accurate answer to the question grounded entirely in retrieved CJIS policy chunks. Never speculate beyond the retrieved content."
    )
    citations: List[CJISCitation] = Field(
        description="One or more cited sections that directly support the answer. Minimum 1, maximum 5."
    )
    confidence: str = Field(
        description="HIGH if retrieved chunks directly answer the question, MEDIUM if partially, LOW if question is outside CJIS scope"
    )
    cannot_answer: bool = Field(
        default=False,
        description="Set True if retrieved chunks do not contain enough information to answer reliably. Never hallucinate — return cannot_answer=True instead."
    )


# ============================================================
# SQLITE RECORD SCHEMAS
# ============================================================

class CitizenRequestRecord(BaseModel):
    """Stored in SQLite after each 311 classification."""
    request_id: str
    raw_complaint_text: str
    classification_json: str    # JSON string of ClassificationResult
    created_at: str

class CJISQueryRecord(BaseModel):
    """Stored in SQLite after each CJIS query."""
    query_id: str
    question_text: str
    result_json: str            # JSON string of CJISQueryResult
    chunks_retrieved: int
    created_at: str
```

---

### STEP 2 — SQLite Schema and Seed Data

**SQLite DDL — exact:**

```sql
PRAGMA foreign_keys = ON;

-- 311 citizen requests
CREATE TABLE IF NOT EXISTS citizen_requests (
    request_id TEXT PRIMARY KEY,
    raw_complaint_text TEXT NOT NULL,
    primary_department TEXT NOT NULL,
    urgency TEXT NOT NULL,
    sla_hours INTEGER NOT NULL,
    work_orders_json TEXT NOT NULL,
    acknowledgment_letter TEXT NOT NULL,
    confidence TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- CJIS policy queries
CREATE TABLE IF NOT EXISTS cjis_queries (
    query_id TEXT PRIMARY KEY,
    question_text TEXT NOT NULL,
    answer TEXT NOT NULL,
    citations_json TEXT NOT NULL,
    chunks_retrieved INTEGER NOT NULL,
    confidence TEXT NOT NULL,
    cannot_answer INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_requests_dept ON citizen_requests(primary_department);
CREATE INDEX IF NOT EXISTS idx_requests_urgency ON citizen_requests(urgency);
CREATE INDEX IF NOT EXISTS idx_queries_confidence ON cjis_queries(confidence);
```

**seed_requests.py — 5 pre-built 311 complaints to seed the DB:**

These are shown in the UI dropdown for instant demo. Each demonstrates a different classification scenario.

| ID | Complaint | Expected Classification |
|---|---|---|
| REQ-001 | Simple single issue: pothole at specific address | Public Works, Medium, 72hr |
| REQ-002 | Multi-department: fallen tree blocking road + damaged streetlight | Public Works + Transportation, High, 24hr |
| REQ-003 | Urgent safety: broken water main flooding street | Utilities, Critical, 2hr |
| REQ-004 | Quality of life: abandoned vehicle + graffiti on building | Transportation + Building and Safety, Low, 7 days |
| REQ-005 | Complex multi-issue: pothole + broken streetlight + illegal dumping + flooding drain | Public Works + Transportation + Environmental Services, High, 24hr — demonstrates multi-work-order decomposition |

Write realistic complaint text for each — 2-4 sentences, first-person citizen voice, specific but messy.

**sample_queries.py — 5 pre-built CJIS questions for demo:**

| ID | Question | Demonstrates |
|---|---|---|
| Q-001 | "What encryption standard does CJIS require for data at rest on mobile devices?" | Specific technical requirement |
| Q-002 | "How often must agencies conduct security awareness training under CJIS?" | Training/policy requirement |
| Q-003 | "What are the CJIS requirements for multi-factor authentication?" | MFA controls |
| Q-004 | "Can cloud service providers store Criminal Justice Information?" | Cloud/vendor policy |
| Q-005 | "What does CJIS require for incident response planning?" | Incident response controls |

---

### STEP 3 — rag/build_index.py

**Builds the FAISS index from the CJIS PDF. Runs ONCE at container startup.**

```python
"""
build_index.py

Chunks the CJIS Security Policy PDF by section, generates embeddings via
Gemini text-embedding-004, builds a FAISS flat index, and caches it to disk.
Called once at Streamlit app startup if index file does not already exist.

CRITICAL CHUNKING RULE: Chunk boundaries must NEVER split a section header.
Each chunk must begin with its section number (e.g., "5.5.6 Encryption...").
This ensures citations map cleanly to section numbers.
"""
```

**Chunking strategy — mandatory:**
- Parse PDF page by page using `pypdf`
- Split on section headers: lines matching pattern `^\d+\.\d+(\.\d+)*\s` (e.g., "5.5.6 Encryption")
- Each chunk = section header + all body text until the next section header
- Minimum chunk size: 100 characters (skip empty or header-only sections)
- Maximum chunk size: 1500 characters (split long sections at paragraph boundaries, preserving the section ID in each sub-chunk)
- Store alongside each chunk: `section_id` (e.g., "5.5.6"), `section_title`, `page_number`

**Embedding — use Gemini:**
```python
from google import genai
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

result = client.models.embed_content(
    model="models/text-embedding-004",
    contents=chunk_text
)
embedding = result.embeddings[0].values
```

**FAISS index:**
```python
import faiss
import numpy as np

dimension = 768  # text-embedding-004 output dimension
index = faiss.IndexFlatIP(dimension)  # Inner product = cosine similarity on normalized vectors

# Normalize before adding
vectors = np.array(embeddings, dtype=np.float32)
faiss.normalize_L2(vectors)
index.add(vectors)
```

**Cache to disk:** Save index as `app/rag/cjis_index.faiss` and chunk metadata as `app/rag/cjis_chunks.json`. On app startup, load from disk if they exist — never rebuild if cache is present. This avoids re-embedding on every container restart.

**When to download the PDF:**
In Dockerfile, download the CJIS v6.0 PDF during build:
```dockerfile
RUN python -c "
import urllib.request
urllib.request.urlretrieve(
    'https://le.fbi.gov/cjis-division/cjis-security-policy',
    'app/rag/cjis_policy.pdf'
)
"
```
If the direct URL changes, fall back to downloading from Texas DPS or another state CJIS portal. The PDF is public. If download fails at build time, include a fallback local copy in the repo (check file size — CJIS PDF is ~200 pages, ~3MB).

---

### STEP 4 — rag/retriever.py

**Similarity search — returns top-k chunks for a query.**

```python
def retrieve_chunks(query: str, k: int = 5) -> List[dict]:
    """
    Embed the query using text-embedding-004.
    Search the FAISS index for top-k most similar chunks.
    Return list of: {section_id, section_title, chunk_text, similarity_score}
    
    If similarity_score of top result < 0.3, return empty list.
    The caller (query_cjis.py) must handle empty retrieval by setting cannot_answer=True.
    """
```

**Threshold rule:** If the highest similarity score is below 0.3, the question is likely outside CJIS scope. Return empty and let the agent say so honestly. Never force an answer from irrelevant chunks.

---

### STEP 5 — modes/classify_311.py

**Mode 1: 311 Classifier — Gemini structured output with strict enum schema.**

```python
def classify_311_request(request_id: str, complaint_text: str) -> ClassificationResult:
    """
    Classifies a citizen complaint using Gemini 2.5 Flash structured output.
    Returns ClassificationResult with departments, urgency, work orders, and
    a personalized acknowledgment letter.
    
    NEVER returns free-form text — all fields are enum-constrained via response_schema.
    Writes result to citizen_requests SQLite table.
    """
```

**Gemini call pattern — exact:**
```python
from google import genai
from google.genai import types
from app.schemas import ClassificationResult

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_PROMPT = """
You are a government 311 intake classification agent.
Your job is to analyze citizen complaints and classify them for routing.

Rules:
- Identify ALL departments needed for a multi-issue complaint
- Create one WorkOrder per department
- Assign urgency based on: CRITICAL=life/safety risk, HIGH=property damage, MEDIUM=quality of life, LOW=cosmetic
- SLA hours: CRITICAL=2, HIGH=24, MEDIUM=72, LOW=168
- Write the acknowledgment letter in a warm, professional tone
- Reference the specific issue and the response timeline in the letter
- Never invent departments not in the enum
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=f"Classify this citizen complaint:\n\n{complaint_text}",
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=ClassificationResult,
        temperature=0,
        thinking_config=types.ThinkingConfig(thinking_budget=0)
    )
)

result = ClassificationResult.model_validate_json(response.text)
result.request_id = request_id
```

Write result to SQLite `citizen_requests` table after every classification.

---

### STEP 6 — modes/query_cjis.py

**Mode 2: CJIS RAG Agent — retrieve then generate with citations.**

```python
def query_cjis_policy(query_id: str, question: str) -> CJISQueryResult:
    """
    Answers a CJIS Security Policy question using RAG.
    
    Flow:
    1. Retrieve top-5 chunks from FAISS index
    2. If no chunks above threshold: return cannot_answer=True immediately
    3. Build prompt with retrieved chunks as grounded context
    4. Call Gemini with CJISQueryResult response_schema
    5. Validate that all citations reference section_ids present in retrieved chunks
    6. Write to cjis_queries SQLite table
    7. Return result
    
    CITATION RULE: Gemini must only cite section_ids that appear in the retrieved chunks.
    If the response cites a section not in the retrieved chunks, strip it before returning.
    """
```

**Prompt construction:**
```python
chunks_context = "\n\n".join([
    f"[Section {chunk['section_id']}: {chunk['section_title']}]\n{chunk['chunk_text']}"
    for chunk in retrieved_chunks
])

user_prompt = f"""
Answer the following question using ONLY the policy sections provided below.
Do not speculate or use knowledge outside these sections.
If the sections do not contain enough information, set cannot_answer to true.

QUESTION: {question}

CJIS POLICY SECTIONS:
{chunks_context}
"""
```

**Gemini call:**
```python
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=user_prompt,
    config=types.GenerateContentConfig(
        system_instruction="You are a CJIS Security Policy compliance assistant. Answer questions by citing exact policy sections. Never speculate. If retrieved sections are insufficient, set cannot_answer=True.",
        response_mime_type="application/json",
        response_schema=CJISQueryResult,
        temperature=0,
        thinking_config=types.ThinkingConfig(thinking_budget=0)
    )
)
```

**Post-validation — mandatory:**
After getting the result, strip any citations whose `section_id` is not in the retrieved chunks. This prevents hallucinated section references.

---

### STEP 7 — streamlit_app.py

**Two tabs. Clean government-grade UI. No sidebar complexity.**

```
Tab 1: "311 Citizen Request Classifier"
Tab 2: "CJIS Policy Q&A"
```

**Tab 1 layout:**
1. Dropdown: select from 5 pre-built complaints OR free-text input area
2. "Classify Request" button
3. Results in 3 columns:
   - Column 1: Classification summary — primary department badge, urgency badge, SLA countdown
   - Column 2: Work orders — one card per department with action type and issue description
   - Column 3: Acknowledgment letter — formatted as a letter, with a copy button
4. History expander at bottom — last 10 classified requests from SQLite

**Tab 2 layout:**
1. Dropdown: select from 5 pre-built CJIS questions OR free-text input area
2. "Search Policy" button
3. Results in 2 columns:
   - Column 1: Answer — full text, clearly labeled "Based on CJIS policy:"
   - Column 2: Citations — each citation as a card: section number (bold), title, relevance
4. "Cannot answer" state — if `cannot_answer=True`, show a clear message: "This question may be outside CJIS scope or the answer requires clarification. Consult your CJIS Systems Officer directly."
5. Query history expander — last 10 queries from SQLite

**GEMINI_API_KEY:** `os.environ.get("GEMINI_API_KEY")` — never hardcoded.

**On startup (before rendering anything):**
```python
from app.rag.build_index import load_or_build_index
index, chunks = load_or_build_index()  # Loads from cache if exists, builds if not
```

Show a spinner during index build with message: "Loading CJIS Security Policy index..."

---

### STEP 8 — Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps for FAISS and pypdf
RUN apt-get update && apt-get install -y \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Download CJIS PDF at build time (public document)
RUN wget -O app/rag/cjis_policy.pdf \
    "https://le.fbi.gov/cjis-division/cjis-security-policy/resource-center/cjis-security-policy-resource-center/2024/cjis-security-policy-v5-9-5-20241217.pdf" \
    || echo "PDF download failed — using bundled fallback"

# Seed SQLite database
RUN python app/data/seed_requests.py

# Single port — Cloud Run requirement
EXPOSE 8080

# Single process — Streamlit only
CMD ["streamlit", "run", "app/streamlit_app.py", \
     "--server.port=8080", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
```

**NOTE:** The FAISS index is NOT built at Docker build time — it is built at first app startup. This keeps build time fast and avoids needing GEMINI_API_KEY at build time (which Secret Manager does not provide during Cloud Build). The index is cached to disk after first build and reloaded on subsequent starts.

---

### STEP 9 — requirements.txt

```
google-genai>=0.8.0
streamlit>=1.35.0
pydantic>=2.0
faiss-cpu>=1.7.4
pypdf>=4.0.0
numpy>=1.24.0
python-dotenv>=1.0.0
```

No LangChain. No FastAPI. No ChromaDB. Minimal dependencies = faster Cloud Run cold start.

---

### STEP 10 — deploy.yml (GitHub Actions)

Same pattern as `gcp-devops-compliance-agent` deploy.yml. Replace:
- Service name: `ccai-gov-intelligence`
- Image name: `ccai-gov-intelligence`
- Same Workload Identity Federation auth
- Same Artifact Registry push
- Same Cloud Run deploy command
- Add `--memory=1Gi` to Cloud Run deploy (FAISS needs more memory than the compliance agent)

**Cloud Run deploy flags to add:**
```
--memory=1Gi
--cpu=1
--timeout=300
--concurrency=10
```

Timeout is 300s because first-run index build + embedding can take 60-90 seconds.

---

### STEP 11 — README.md (write last)

Must include:
1. Two-line pitch: what it is, who it's for
2. Architecture diagram (ASCII)
3. Live URL (fill after deploy)
4. Demo queries — 5 for each mode, copy-pasteable
5. "Why this matters to GTS" section — OmniDARS → CJIS angle, government client base
6. GCP services used and why
7. CJIS disclaimer: "This tool answers questions about the publicly available CJIS Security Policy document. It does not process, store, or transmit actual Criminal Justice Information."

---

## GEMINI SDK PATTERNS — CONFIRMED CORRECT

**Structured output (Mode 1):**
```python
# Use response_schema= with a Pydantic model
# Use response_mime_type="application/json"
# Always temperature=0
# Always thinking_budget=0
# Never duplicate schema in system_instruction — put it only in response_schema
```

**Embedding (for FAISS index build):**
```python
result = client.models.embed_content(
    model="models/text-embedding-004",
    contents=text
)
vector = result.embeddings[0].values
```

**Breaking change warnings:**
- DO NOT use `import google.generativeai as genai` — use `from google import genai`
- DO NOT use `parameters=` in FunctionDeclaration — use `parameters_json_schema=`
- ALWAYS set `thinking_budget=0`
- ALWAYS set `temperature=0`

---

## RULES FOR WINDSURF

1. Build in the exact file order above — schemas.py always first
2. Write complete files — no `pass`, no `# TODO`, no placeholder logic
3. Every function has type hints and a docstring
4. The FAISS index build NEVER runs at Docker build time — only at first app startup
5. The PDF download happens at Docker build time — not at runtime
6. GEMINI_API_KEY always from `os.environ.get("GEMINI_API_KEY")` — never hardcoded
7. Both Gemini calls use `temperature=0` and `thinking_budget=0`
8. The citation validator in `query_cjis.py` is mandatory — strip hallucinated section refs
9. Cloud Run gets ONE port (8080) — Streamlit is the only listener, no FastAPI
10. SQLite path must work locally and in container — use `pathlib.Path(__file__).parent`
11. Do not add services not listed — no Redis, no Firestore, no Cloud SQL, no managed vector DB
12. Memory for Cloud Run deploy must be set to 1Gi — FAISS needs it
13. If CJIS PDF download fails at build, log a clear error — do not silently fail
14. Flag immediately if any requirement will break on GCP free tier

---

## GCP PLACEHOLDERS — SUBSTITUTE BEFORE DEPLOYING

- `YOUR_PROJECT_ID` → `earnest-sight-503519-t5` (same GCP project as Agent 1)
- `YOUR_WIF_PROVIDER` → Workload Identity Federation provider resource name
- `YOUR_WIF_SERVICE_ACCOUNT` → SA email used for WIF
- `LIVE_URL` → assigned after first Cloud Run deploy

---

## DEMO SCRIPT — WHAT ABHI WILL SHOW RAM

**Tab 1 — 311 Classifier (lead with this):**
1. Select REQ-005 (5-department complex complaint) → Classify → Show 3 work orders with different departments, urgency badges, SLA timers, acknowledgment letter
2. Select REQ-003 (critical water main) → Classify → CRITICAL badge, 2-hour SLA → "Watch the urgency detection"
3. Type a brand new complaint live → Classify → "It works on any input"
4. Show history expander → SQLite rows → "Everything is logged and auditable"

**Tab 2 — CJIS Q&A:**
1. Select Q-001 (mobile encryption) → Search → Show answer + cited section numbers
2. Select Q-003 (MFA requirements) → Search → Show multiple citations
3. Type a question that's outside CJIS scope → Search → Show "cannot answer" state → "It knows what it doesn't know — no hallucination"
4. Re-run Q-001 → Identical result → "Answers are consistent and grounded in the document"

**What to say when Ram asks "how would this work in production?"**
- Mode 1: "Connect to your city's existing 311 intake form or CRM. Classification and work order routing happens automatically on submission. Acknowledgment letter goes out via email API."
- Mode 2: "Same RAG pattern you'd use for any internal policy document — CJIS today, your own OmniDARS policy library tomorrow. The architecture is identical to how OmniAssist works."
