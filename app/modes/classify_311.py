"""
classify_311.py

Mode 1: 311 Citizen Request Classifier.

Classifies a free-text citizen complaint using Gemini 2.5 Flash structured output.
Returns a ClassificationResult with department routing, urgency, SLA, per-department
work orders, and a personalized acknowledgment letter.
Writes every result to the citizen_requests SQLite table.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from google import genai
from google.genai import types

from app.schemas import ClassificationResult

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "gov_intel.db"

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


def _get_client() -> genai.Client:
    """Return an authenticated Gemini client."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
    return genai.Client(api_key=api_key)


def _write_to_db(result: ClassificationResult, complaint_text: str) -> None:
    """Persist a ClassificationResult to the citizen_requests SQLite table."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO citizen_requests
                (request_id, raw_complaint_text, primary_department, urgency,
                 sla_hours, work_orders_json, acknowledgment_letter, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.request_id,
                complaint_text,
                result.primary_department.value,
                result.urgency.value,
                result.sla_hours,
                json.dumps(
                    [wo.model_dump() for wo in result.work_orders], default=str
                ),
                result.acknowledgment_letter,
                result.classification_confidence,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        logger.info("[classify_311] Saved %s to SQLite.", result.request_id)
    finally:
        conn.close()


def classify_311_request(
    request_id: str, complaint_text: str
) -> ClassificationResult:
    """
    Classify a citizen complaint using Gemini 2.5 Flash structured output.

    All output fields are enum-constrained via response_schema — no free-form
    department names or urgency values can be returned. Multi-issue complaints
    produce one WorkOrder per department involved.

    After classification the result is written to the citizen_requests SQLite table.

    Args:
        request_id: Caller-assigned unique ID (e.g., "REQ-007").
        complaint_text: Raw citizen complaint text in plain English.

    Returns:
        ClassificationResult populated by Gemini, with request_id set.

    Raises:
        RuntimeError: If GEMINI_API_KEY is not set.
        ValueError: If Gemini returns a response that cannot be parsed into
            ClassificationResult.
    """
    client = _get_client()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Classify this citizen complaint:\n\n{complaint_text}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=ClassificationResult,
            temperature=0,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )

    result = ClassificationResult.model_validate_json(response.text)
    result.request_id = request_id

    logger.info(
        "[classify_311] %s → %s | %s | %d work order(s)",
        request_id,
        result.primary_department,
        result.urgency,
        len(result.work_orders),
    )

    _write_to_db(result, complaint_text)
    return result
