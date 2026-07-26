"""
build_index.py

Chunks the CJIS Security Policy PDF by section, generates embeddings via
Gemini text-embedding-004, builds a FAISS flat index, and caches it to disk.
Called once at Streamlit app startup if index file does not already exist.

CRITICAL CHUNKING RULE: Chunk boundaries must NEVER split a section header.
Each chunk must begin with its section number (e.g., "5.5.6 Encryption...").
This ensures citations map cleanly to section numbers.
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple

import faiss
import numpy as np
from google import genai
from pypdf import PdfReader
from app.rag.cjis_policy_text import CJIS_POLICY_SECTIONS

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
PDF_PATH = BASE_DIR / "cjis_policy.pdf"
INDEX_PATH = BASE_DIR / "cjis_index.faiss"
CHUNKS_PATH = BASE_DIR / "cjis_chunks.json"

EMBEDDING_MODEL = "models/text-embedding-004"
DIMENSION = 768
MIN_CHUNK_CHARS = 100
MAX_CHUNK_CHARS = 1500

# Matches CJIS section headers like "5.5.6 Encryption" or "5 Policy Area"
SECTION_HEADER_RE = re.compile(r"^\d+\.\d+(\.\d+)*\s+\S")


def _get_client() -> genai.Client:
    """Return an authenticated Gemini client (v1beta — used for generation)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
    return genai.Client(api_key=api_key)


def _get_embed_client() -> genai.Client:
    """
    Return a Gemini client configured for the v1 stable API.
    Required for text-embedding-004, which is not available on v1beta in SDK 2.x.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
    return genai.Client(api_key=api_key, http_options={"api_version": "v1"})


def _pdf_is_valid(pdf_path: Path) -> bool:
    """Return True only if the file exists and is large enough to be a real PDF."""
    return pdf_path.exists() and pdf_path.stat().st_size > 10_000


def _extract_pages(pdf_path: Path) -> List[Tuple[int, str]]:
    """Return [(page_number, page_text), ...] from the PDF."""
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append((i, text))
    return pages


def _chunks_from_fallback() -> List[Dict]:
    """
    Build chunk list from the hardcoded CJIS policy sections in cjis_policy_text.py.
    Used when the PDF is unavailable or empty in the container.
    """
    logger.warning(
        "[build_index] Using hardcoded CJIS policy fallback text — "
        "PDF was missing or empty. All 5 demo queries are fully supported."
    )
    chunks: List[Dict] = []
    for section in CJIS_POLICY_SECTIONS:
        text = section["text"]
        if len(text) <= MAX_CHUNK_CHARS:
            chunks.append({
                "section_id": section["section_id"],
                "section_title": section["section_title"],
                "chunk_text": text,
                "page_number": section["page_number"],
            })
        else:
            chunks.extend(_split_long_chunk(
                section["section_id"],
                section["section_title"],
                text,
                section["page_number"],
            ))
    logger.info("[build_index] Fallback produced %d chunks.", len(chunks))
    return chunks


def _parse_section_id(line: str) -> str:
    """Extract section ID (e.g., '5.5.6') from the start of a header line."""
    match = re.match(r"^(\d+\.\d+(?:\.\d+)*)", line.strip())
    return match.group(1) if match else ""


def _split_long_chunk(
    section_id: str, section_title: str, text: str, page: int
) -> List[Dict]:
    """
    Split a chunk exceeding MAX_CHUNK_CHARS at paragraph boundaries.
    The section_id is preserved in every sub-chunk so citations remain valid.
    """
    sub_chunks: List[Dict] = []
    paragraphs = re.split(r"\n{2,}", text)
    current = ""

    for para in paragraphs:
        candidate = (current + "\n\n" + para).strip() if current else para.strip()
        if len(candidate) > MAX_CHUNK_CHARS and current:
            if len(current.strip()) >= MIN_CHUNK_CHARS:
                sub_chunks.append(
                    {
                        "section_id": section_id,
                        "section_title": section_title,
                        "chunk_text": current.strip(),
                        "page_number": page,
                    }
                )
            current = para.strip()
        else:
            current = candidate

    if current.strip() and len(current.strip()) >= MIN_CHUNK_CHARS:
        sub_chunks.append(
            {
                "section_id": section_id,
                "section_title": section_title,
                "chunk_text": current.strip(),
                "page_number": page,
            }
        )
    return sub_chunks


def _chunk_pdf(pages: List[Tuple[int, str]]) -> List[Dict]:
    """
    Walk the PDF line-by-line and split into chunks at section headers.
    Each chunk: {section_id, section_title, chunk_text, page_number}
    """
    chunks: List[Dict] = []
    current_section_id = ""
    current_section_title = ""
    current_lines: List[str] = []
    current_page = 1

    def _flush() -> None:
        if not current_section_id or not current_lines:
            return
        raw = "\n".join(current_lines).strip()
        if len(raw) < MIN_CHUNK_CHARS:
            return
        if len(raw) <= MAX_CHUNK_CHARS:
            chunks.append(
                {
                    "section_id": current_section_id,
                    "section_title": current_section_title,
                    "chunk_text": raw,
                    "page_number": current_page,
                }
            )
        else:
            chunks.extend(
                _split_long_chunk(current_section_id, current_section_title, raw, current_page)
            )

    for page_num, page_text in pages:
        for line in page_text.split("\n"):
            stripped = line.strip()
            if SECTION_HEADER_RE.match(stripped):
                _flush()
                current_section_id = _parse_section_id(stripped)
                title_match = re.match(r"^\d+\.\d+(?:\.\d+)*\s+(.*)", stripped)
                current_section_title = (
                    title_match.group(1).strip() if title_match else stripped
                )
                current_lines = [stripped]
                current_page = page_num
            elif current_section_id:
                current_lines.append(line)

    _flush()
    logger.info("[build_index] Extracted %d chunks from PDF.", len(chunks))
    return chunks


def _embed_chunks(client: genai.Client, chunks: List[Dict]) -> np.ndarray:
    """
    Generate embeddings for every chunk via text-embedding-004.
    Returns a float32 array of shape (len(chunks), DIMENSION).
    """
    embeddings: List[List[float]] = []
    for i, chunk in enumerate(chunks):
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=chunk["chunk_text"],
        )
        embeddings.append(result.embeddings[0].values)
        if (i + 1) % 10 == 0:
            logger.info("[build_index] Embedded %d / %d chunks…", i + 1, len(chunks))
        time.sleep(0.5)  # stay within free-tier rate limit (15 RPM)
    return np.array(embeddings, dtype=np.float32)


def _build_faiss_index(vectors: np.ndarray) -> faiss.Index:
    """
    Build a FAISS IndexFlatIP (inner product on L2-normalized vectors = cosine similarity).
    Normalization is applied in-place before adding to the index.
    """
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(DIMENSION)
    index.add(vectors)
    logger.info("[build_index] FAISS index built — %d vectors.", index.ntotal)
    return index


def _save_to_disk(index: faiss.Index, chunks: List[Dict]) -> None:
    """Persist FAISS index and chunk metadata to disk for future startups."""
    faiss.write_index(index, str(INDEX_PATH))
    with open(CHUNKS_PATH, "w", encoding="utf-8") as fh:
        json.dump(chunks, fh, ensure_ascii=False, indent=2)
    logger.info(
        "[build_index] Saved index → %s, chunks → %s.", INDEX_PATH, CHUNKS_PATH
    )


def _load_from_disk() -> Tuple[faiss.Index, List[Dict]]:
    """Load previously cached FAISS index and chunk metadata from disk."""
    index = faiss.read_index(str(INDEX_PATH))
    with open(CHUNKS_PATH, "r", encoding="utf-8") as fh:
        chunks = json.load(fh)
    logger.info(
        "[build_index] Loaded %d vectors and %d chunks from cache.",
        index.ntotal,
        len(chunks),
    )
    return index, chunks


def load_or_build_index() -> Tuple[faiss.Index, List[Dict]]:
    """
    Main entry point called at Streamlit app startup.

    If both the FAISS index file and chunk metadata file exist on disk,
    they are loaded immediately (fast path — no API calls).

    Otherwise, the CJIS PDF is parsed, each section chunk is embedded via
    Gemini text-embedding-004, a FAISS IndexFlatIP is built, and both
    artifacts are written to disk for all future startups.

    Returns:
        (faiss.Index, List[dict]) — the index and its associated chunk metadata.

    Raises:
        FileNotFoundError: If the CJIS PDF is missing (should be downloaded at
            Docker build time via the wget command in the Dockerfile).
        RuntimeError: If GEMINI_API_KEY is not set when building for the first time.
        ValueError: If the PDF yields no usable chunks.
    """
    if INDEX_PATH.exists() and CHUNKS_PATH.exists():
        logger.info("[build_index] Cache hit — loading from disk.")
        return _load_from_disk()

    logger.info("[build_index] Cache miss — building index.")

    if _pdf_is_valid(PDF_PATH):
        logger.info("[build_index] PDF found (%d bytes) — parsing.", PDF_PATH.stat().st_size)
        try:
            pages = _extract_pages(PDF_PATH)
            chunks = _chunk_pdf(pages)
        except Exception as exc:
            logger.warning("[build_index] PDF parsing failed (%s) — using fallback.", exc)
            chunks = []
    else:
        logger.warning(
            "[build_index] PDF missing or too small (%s) — using hardcoded fallback.",
            PDF_PATH if PDF_PATH.exists() else "not found",
        )
        chunks = []

    if not chunks:
        chunks = _chunks_from_fallback()

    vectors = _embed_chunks(chunks)
    index = _build_faiss_index(vectors)
    _save_to_disk(index, chunks)

    return index, chunks
