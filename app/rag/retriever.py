"""
retriever.py

FAISS similarity search for CJIS Security Policy chunks.

The module holds a shared index and chunk list initialized once at app startup
via initialize(). retrieve_chunks() is the single public function used by
query_cjis.py.
"""

import json
import logging
import os
import urllib.request
from typing import Dict, List, Optional

import faiss
import numpy as np
from google import genai

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "models/text-embedding-004"
SIMILARITY_THRESHOLD = 0.3

_index: Optional[faiss.Index] = None
_chunks: Optional[List[Dict]] = None


def initialize(index: faiss.Index, chunks: List[Dict]) -> None:
    """
    Set the shared FAISS index and chunk list.
    Must be called once at Streamlit app startup before any retrieve_chunks() calls.

    Args:
        index: A FAISS index populated with L2-normalized chunk embeddings.
        chunks: List of chunk metadata dicts produced by build_index.py.
    """
    global _index, _chunks
    _index = index
    _chunks = chunks
    logger.info(
        "[retriever] Initialized — %d vectors, %d chunks.", index.ntotal, len(chunks)
    )


def _embed_query(query: str) -> np.ndarray:
    """
    Embed a query string using text-embedding-004 v1 REST API directly.
    Returns a L2-normalized float32 row vector of shape (1, 768).
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Neither GEMINI_API_KEY nor GOOGLE_API_KEY environment variable is set.")
    url = (
        "https://generativelanguage.googleapis.com"
        f"/v1/models/text-embedding-004:embedContent?key={api_key}"
    )
    body = json.dumps({
        "model": "models/text-embedding-004",
        "content": {"parts": [{"text": query}]},
    }).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    values = data["embedding"]["values"]
    vector = np.array(values, dtype=np.float32).reshape(1, -1)
    faiss.normalize_L2(vector)
    return vector


def retrieve_chunks(query: str, k: int = 5) -> List[Dict]:
    """
    Embed the query and search the FAISS index for the top-k most similar chunks.

    Each returned dict contains:
        section_id      — e.g., "5.5.6"
        section_title   — e.g., "Encryption"
        chunk_text      — the full section text
        page_number     — source page in the CJIS PDF
        similarity_score — cosine similarity score (0.0 – 1.0)

    If the highest similarity score is below SIMILARITY_THRESHOLD (0.3),
    an empty list is returned. The caller (query_cjis.py) must handle
    this by setting cannot_answer=True — never force an answer from
    irrelevant chunks.

    Args:
        query: Natural language question about CJIS requirements.
        k: Number of chunks to retrieve (default 5).

    Returns:
        List of chunk dicts sorted by descending similarity, or [] if
        no chunk exceeds the similarity threshold.

    Raises:
        RuntimeError: If initialize() has not been called before this function.
    """
    if _index is None or _chunks is None:
        raise RuntimeError(
            "Retriever not initialized. Call retriever.initialize(index, chunks) at startup."
        )

    query_vector = _embed_query(query)
    actual_k = min(k, _index.ntotal)
    scores, indices = _index.search(query_vector, actual_k)

    top_score = float(scores[0][0]) if scores.shape[1] > 0 else 0.0

    if top_score < SIMILARITY_THRESHOLD:
        logger.info(
            "[retriever] Top score %.4f < threshold %.2f — returning empty (cannot_answer).",
            top_score,
            SIMILARITY_THRESHOLD,
        )
        return []

    results: List[Dict] = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        chunk = dict(_chunks[int(idx)])
        chunk["similarity_score"] = float(score)
        results.append(chunk)

    logger.info(
        "[retriever] Retrieved %d chunks (top score: %.4f).", len(results), top_score
    )
    return results
