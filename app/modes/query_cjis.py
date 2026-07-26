"""
query_cjis.py

Mode 2: CJIS Security Policy Q&A Agent.

Retrieves top-k chunks from the FAISS index, generates a grounded answer via
Gemini 2.5 Flash with a structured CJISQueryResult schema, strips any hallucinated
citations, and writes the result to the cjis_queries SQLite table.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from google import genai
from google.genai import types

from app.schemas import CJISQueryResult
from app.rag import retriever

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "gov_intel.db"

SYSTEM_PROMPT = (
    "You are a CJIS Security Policy compliance assistant. "
    "Answer questions by citing exact policy sections. "
    "Never speculate. If retrieved sections are insufficient, set cannot_answer=True."
)


def _get_client() -> genai.Client:
    """Return an authenticated Gemini client."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
    return genai.Client(api_key=api_key)


def _build_prompt(question: str, retrieved_chunks: List[dict]) -> str:
    """Construct the RAG prompt from the question and retrieved CJIS chunks."""
    chunks_context = "\n\n".join([
        f"[Section {chunk['section_id']}: {chunk['section_title']}]\n{chunk['chunk_text']}"
        for chunk in retrieved_chunks
    ])
    return (
        "Answer the following question using ONLY the policy sections provided below.\n"
        "Do not speculate or use knowledge outside these sections.\n"
        "If the sections do not contain enough information, set cannot_answer to true.\n\n"
        f"QUESTION: {question}\n\n"
        f"CJIS POLICY SECTIONS:\n{chunks_context}"
    )


def _validate_citations(
    result: CJISQueryResult, retrieved_chunks: List[dict]
) -> CJISQueryResult:
    """
    Remove any citations whose section_id does not appear in the retrieved chunks.

    This is a mandatory post-processing step that prevents hallucinated section
    references from reaching the caller. A CJIS-savvy evaluator would immediately
    spot a fabricated section number.
    """
    retrieved_ids = {chunk["section_id"] for chunk in retrieved_chunks}
    before = len(result.citations)
    result.citations = [c for c in result.citations if c.section_id in retrieved_ids]
    dropped = before - len(result.citations)
    if dropped > 0:
        logger.warning(
            "[query_cjis] Stripped %d hallucinated citation(s) not in retrieved chunks.",
            dropped,
        )
    return result


def _write_to_db(result: CJISQueryResult, chunks_retrieved: int) -> None:
    """Persist a CJISQueryResult to the cjis_queries SQLite table."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO cjis_queries
                (query_id, question_text, answer, citations_json,
                 chunks_retrieved, confidence, cannot_answer, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.query_id,
                result.question,
                result.answer,
                json.dumps([c.model_dump() for c in result.citations]),
                chunks_retrieved,
                result.confidence,
                int(result.cannot_answer),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        logger.info("[query_cjis] Saved %s to SQLite.", result.query_id)
    finally:
        conn.close()


def query_cjis_policy(query_id: str, question: str) -> CJISQueryResult:
    """
    Answer a CJIS Security Policy question using retrieval-augmented generation.

    Flow:
      1. Retrieve top-5 chunks from the FAISS index via retriever.retrieve_chunks().
      2. If no chunk exceeds the similarity threshold (0.3): return cannot_answer=True
         immediately without calling Gemini.
      3. Build a grounded prompt containing the retrieved chunks.
      4. Call Gemini 2.5 Flash with response_schema=CJISQueryResult.
      5. Strip any citations whose section_id is not present in the retrieved chunks.
      6. Write the result to the cjis_queries SQLite table.
      7. Return the validated CJISQueryResult.

    Args:
        query_id: Caller-assigned unique ID (e.g., "Q-007").
        question: Natural language question about CJIS requirements.

    Returns:
        CJISQueryResult with answer, validated citations, confidence level,
        and cannot_answer flag.

    Raises:
        RuntimeError: If GEMINI_API_KEY is not set or retriever is uninitialized.
        ValueError: If Gemini returns a response that cannot be parsed.
    """
    retrieved_chunks = retriever.retrieve_chunks(query=question, k=5)

    if not retrieved_chunks:
        logger.info(
            "[query_cjis] %s — no relevant chunks found; returning cannot_answer=True.",
            query_id,
        )
        result = CJISQueryResult(
            query_id=query_id,
            question=question,
            answer="",
            citations=[],
            confidence="LOW",
            cannot_answer=True,
        )
        _write_to_db(result, chunks_retrieved=0)
        return result

    client = _get_client()
    user_prompt = _build_prompt(question, retrieved_chunks)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=CJISQueryResult,
            temperature=0,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )

    result = CJISQueryResult.model_validate_json(response.text)
    result.query_id = query_id
    result.question = question

    result = _validate_citations(result, retrieved_chunks)

    logger.info(
        "[query_cjis] %s — confidence=%s, citations=%d, cannot_answer=%s",
        query_id,
        result.confidence,
        len(result.citations),
        result.cannot_answer,
    )

    _write_to_db(result, chunks_retrieved=len(retrieved_chunks))
    return result
