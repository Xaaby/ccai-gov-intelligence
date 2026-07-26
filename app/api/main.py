"""
app/api/main.py

FastAPI backend for ccai-gov-intelligence.
Exposes three endpoints for the compliance-intelligence-platform wrapper:

  POST /classify      — 311 citizen request classification
  POST /query-cjis   — CJIS Security Policy RAG Q&A
  GET  /health       — service health + FAISS index status

FAISS index is loaded once at startup via FastAPI lifespan.
retriever.initialize() is called immediately after load so that
query_cjis_policy() can call retrieve_chunks() without error.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

import faiss
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.rag import build_index, retriever
from app.schemas import CJISCitation, ClassificationResult, CJISQueryResult
from app.modes.classify_311 import classify_311_request
from app.modes.query_cjis import query_cjis_policy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level index state — set once in lifespan, read by /health
# ---------------------------------------------------------------------------

_index: Optional[faiss.Index] = None
_chunks: Optional[List[dict]] = None


# ---------------------------------------------------------------------------
# Lifespan: load FAISS index at startup, initialize retriever module state
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _index, _chunks
    logger.info("[lifespan] Loading or building CJIS FAISS index…")
    _index, _chunks = build_index.load_or_build_index()
    retriever.initialize(_index, _chunks)
    logger.info(
        "[lifespan] FAISS index ready — %d vectors, %d chunks.",
        _index.ntotal,
        len(_chunks),
    )
    yield
    logger.info("[lifespan] Shutting down.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ccai-gov-intelligence API",
    description="Government Citizen Intelligence — 311 Classifier and CJIS RAG endpoints",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ClassifyRequest(BaseModel):
    request_id: str
    complaint_text: str


class CJISQueryRequest(BaseModel):
    query_id: str
    question: str


class CJISAPIResponse(BaseModel):
    """CJISQueryResult fields plus chunks_retrieved for the API caller."""
    query_id: Optional[str]
    question: str
    answer: str
    citations: List[CJISCitation]
    confidence: str
    cannot_answer: bool
    chunks_retrieved: int


class HealthResponse(BaseModel):
    status: str
    service: str
    index_loaded: bool
    timestamp: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health() -> HealthResponse:
    """
    Returns service health and whether the FAISS index is loaded.
    The wrapper app should verify index_loaded=true before calling /query-cjis.
    """
    return HealthResponse(
        status="ok",
        service="ccai-gov-intelligence-api",
        index_loaded=_index is not None,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/classify", response_model=ClassificationResult, tags=["Mode 1 — 311 Classifier"])
def classify(body: ClassifyRequest) -> ClassificationResult:
    """
    Classify a citizen complaint using Gemini 2.5 Flash structured output.

    Returns department routing, urgency, SLA, per-department work orders,
    and an acknowledgment letter. Result is also written to SQLite.
    """
    try:
        result = classify_311_request(
            request_id=body.request_id,
            complaint_text=body.complaint_text,
        )
    except RuntimeError as exc:
        logger.error("[/classify] RuntimeError: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        logger.error("[/classify] ValueError: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("[/classify] Unexpected error")
        raise HTTPException(status_code=500, detail=str(exc))
    return result


@app.post("/query-cjis", response_model=CJISAPIResponse, tags=["Mode 2 — CJIS RAG"])
def query_cjis(body: CJISQueryRequest) -> CJISAPIResponse:
    """
    Answer a CJIS Security Policy question via retrieval-augmented generation.

    Retrieves top-5 chunks from the pre-loaded FAISS index, generates a grounded
    answer with Gemini 2.5 Flash, strips hallucinated citations, and writes to SQLite.
    If no chunk exceeds similarity threshold 0.3, returns cannot_answer=true.
    """
    if _index is None:
        raise HTTPException(
            status_code=503,
            detail="FAISS index is not yet loaded. Retry after /health returns index_loaded=true.",
        )
    try:
        result: CJISQueryResult = query_cjis_policy(
            query_id=body.query_id,
            question=body.question,
        )
    except RuntimeError as exc:
        logger.error("[/query-cjis] RuntimeError: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        logger.error("[/query-cjis] ValueError: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("[/query-cjis] Unexpected error")
        raise HTTPException(status_code=500, detail=str(exc))

    chunks_retrieved = 0 if result.cannot_answer else 5

    return CJISAPIResponse(
        query_id=result.query_id,
        question=result.question,
        answer=result.answer,
        citations=result.citations,
        confidence=result.confidence,
        cannot_answer=result.cannot_answer,
        chunks_retrieved=chunks_retrieved,
    )
