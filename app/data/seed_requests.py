"""
seed_requests.py
Creates the SQLite database, applies DDL, and seeds 5 pre-built 311 complaints.
Run at Docker build time: RUN python app/data/seed_requests.py
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "gov_intel.db"

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS citizen_requests (
    request_id            TEXT PRIMARY KEY,
    raw_complaint_text    TEXT NOT NULL,
    primary_department    TEXT NOT NULL,
    urgency               TEXT NOT NULL,
    sla_hours             INTEGER NOT NULL,
    work_orders_json      TEXT NOT NULL,
    acknowledgment_letter TEXT NOT NULL,
    confidence            TEXT NOT NULL,
    created_at            DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cjis_queries (
    query_id         TEXT PRIMARY KEY,
    question_text    TEXT NOT NULL,
    answer           TEXT NOT NULL,
    citations_json   TEXT NOT NULL,
    chunks_retrieved INTEGER NOT NULL,
    confidence       TEXT NOT NULL,
    cannot_answer    INTEGER NOT NULL DEFAULT 0,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_requests_dept     ON citizen_requests(primary_department);
CREATE INDEX IF NOT EXISTS idx_requests_urgency  ON citizen_requests(urgency);
CREATE INDEX IF NOT EXISTS idx_queries_confidence ON cjis_queries(confidence);
"""

# 5 pre-built complaints for demo dropdown
SEED_REQUESTS = [
    {
        "request_id": "REQ-001",
        "raw_complaint_text": (
            "There's a massive pothole on the corner of 5th and Elm that's been there for weeks. "
            "I almost blew out my tire this morning driving to work. It's about 2 feet wide and "
            "several inches deep. Can someone please fix this before it causes an accident?"
        ),
        "primary_department": "Public Works",
        "urgency": "MEDIUM",
        "sla_hours": 72,
        "work_orders_json": json.dumps([{
            "department": "Public Works",
            "urgency": "MEDIUM",
            "sla_hours": 72,
            "action_type": "Maintenance Crew Dispatch",
            "issue_description": "Large pothole approximately 2 feet wide at the intersection of 5th and Elm Street requires immediate patching.",
        }]),
        "acknowledgment_letter": (
            "Dear Resident,\n\nThank you for reporting the pothole at 5th and Elm Street. "
            "We have assigned this request to our Public Works department, who will dispatch "
            "a maintenance crew within 72 hours to assess and repair the road surface. "
            "We appreciate your patience and your commitment to keeping our streets safe."
        ),
        "confidence": "HIGH",
    },
    {
        "request_id": "REQ-002",
        "raw_complaint_text": (
            "A large oak tree fell across Maple Avenue last night during the storm and it's blocking "
            "one full lane of traffic. On top of that, the streetlight at that intersection is completely "
            "dark — looks like the tree may have knocked the power line loose when it fell. "
            "Cars are having to squeeze through a single lane and it's causing backups."
        ),
        "primary_department": "Public Works",
        "urgency": "HIGH",
        "sla_hours": 24,
        "work_orders_json": json.dumps([
            {
                "department": "Public Works",
                "urgency": "HIGH",
                "sla_hours": 24,
                "action_type": "Maintenance Crew Dispatch",
                "issue_description": "Fallen oak tree blocking one lane of Maple Avenue must be removed to restore full traffic flow.",
            },
            {
                "department": "Transportation",
                "urgency": "HIGH",
                "sla_hours": 24,
                "action_type": "Field Inspection",
                "issue_description": "Streetlight at Maple Avenue intersection is non-functional; possible power line damage from fallen tree requires inspection.",
            },
        ]),
        "acknowledgment_letter": (
            "Dear Resident,\n\nThank you for reporting the fallen tree and streetlight outage on Maple Avenue. "
            "We have assigned this as a high-priority request — Public Works will dispatch a crew to remove "
            "the tree within 24 hours, and Transportation will inspect and restore the damaged streetlight. "
            "We apologize for the inconvenience and are working to resolve both issues promptly."
        ),
        "confidence": "HIGH",
    },
    {
        "request_id": "REQ-003",
        "raw_complaint_text": (
            "URGENT — there is water gushing out of the ground at the intersection of Oak and 3rd Street. "
            "It looks like a water main has burst. The water is flooding the road and starting to flow "
            "into nearby businesses. It's been going on for about 20 minutes and the flooding is getting "
            "worse. This needs someone out here immediately."
        ),
        "primary_department": "Utilities",
        "urgency": "CRITICAL",
        "sla_hours": 2,
        "work_orders_json": json.dumps([{
            "department": "Utilities",
            "urgency": "CRITICAL",
            "sla_hours": 2,
            "action_type": "Maintenance Crew Dispatch",
            "issue_description": "Suspected water main burst at Oak and 3rd Street causing active flooding of roadway and adjacent businesses; emergency repair required immediately.",
        }]),
        "acknowledgment_letter": (
            "Dear Resident,\n\nWe have received your urgent report of a water main break at Oak and 3rd Street "
            "and have immediately escalated this to our Utilities emergency response team. "
            "A crew has been dispatched and will arrive within 2 hours to shut off the water and begin repairs. "
            "If you are in the immediate area, please keep a safe distance from the flooding. Thank you for alerting us."
        ),
        "confidence": "HIGH",
    },
    {
        "request_id": "REQ-004",
        "raw_complaint_text": (
            "There's an abandoned car that's been parked on Birch Street for at least two weeks — "
            "no license plates, flat tires, looks like it was just left there. Also, the wall on "
            "the side of the building at 420 Birch has been tagged with graffiti. It's an eyesore "
            "and I'd like both taken care of when someone has time."
        ),
        "primary_department": "Transportation",
        "urgency": "LOW",
        "sla_hours": 168,
        "work_orders_json": json.dumps([
            {
                "department": "Transportation",
                "urgency": "LOW",
                "sla_hours": 168,
                "action_type": "Investigation",
                "issue_description": "Abandoned vehicle with no plates and flat tires on Birch Street requires investigation and towing.",
            },
            {
                "department": "Building and Safety",
                "urgency": "LOW",
                "sla_hours": 168,
                "action_type": "Field Inspection",
                "issue_description": "Graffiti on exterior wall of 420 Birch Street requires inspection and abatement notice to property owner.",
            },
        ]),
        "acknowledgment_letter": (
            "Dear Resident,\n\nThank you for reporting the abandoned vehicle and graffiti on Birch Street. "
            "We have logged both issues — Transportation will investigate the abandoned vehicle within 7 days, "
            "and Building and Safety will inspect the graffiti and issue an abatement notice to the property owner. "
            "We appreciate you helping us keep our neighborhood clean and safe."
        ),
        "confidence": "HIGH",
    },
    {
        "request_id": "REQ-005",
        "raw_complaint_text": (
            "I'm writing to report several problems on my block that have all gotten out of hand at once. "
            "First, there are multiple potholes on Cedar Lane between 10th and 12th that are destroying cars. "
            "Second, two of the streetlights on that stretch have been out for weeks. "
            "Third, someone has been dumping old furniture and trash bags in the empty lot on the corner — "
            "it's a real eyesore and probably a health hazard. "
            "Finally, the storm drain at the corner is completely clogged and every time it rains even a little, "
            "the street floods. Please send whoever you need to fix all of this."
        ),
        "primary_department": "Public Works",
        "urgency": "HIGH",
        "sla_hours": 24,
        "work_orders_json": json.dumps([
            {
                "department": "Public Works",
                "urgency": "HIGH",
                "sla_hours": 24,
                "action_type": "Maintenance Crew Dispatch",
                "issue_description": "Multiple potholes on Cedar Lane between 10th and 12th Streets require patching.",
            },
            {
                "department": "Transportation",
                "urgency": "MEDIUM",
                "sla_hours": 72,
                "action_type": "Maintenance Crew Dispatch",
                "issue_description": "Two non-functional streetlights on Cedar Lane between 10th and 12th Streets require inspection and bulb/fixture replacement.",
            },
            {
                "department": "Environmental Services",
                "urgency": "MEDIUM",
                "sla_hours": 72,
                "action_type": "Field Inspection",
                "issue_description": "Illegal dumping of furniture and trash in vacant lot on Cedar Lane requires cleanup and potential citation.",
            },
            {
                "department": "Public Works",
                "urgency": "HIGH",
                "sla_hours": 24,
                "action_type": "Maintenance Crew Dispatch",
                "issue_description": "Clogged storm drain at Cedar Lane corner causing street flooding must be cleared.",
            },
        ]),
        "acknowledgment_letter": (
            "Dear Resident,\n\nThank you for your detailed report of multiple issues on Cedar Lane. "
            "We have created work orders for all four concerns: Public Works will address the potholes and clogged "
            "storm drain within 24 hours, Transportation will restore the streetlights within 72 hours, and "
            "Environmental Services will investigate the illegal dumping within 72 hours. "
            "We appreciate your thoroughness in helping us identify and prioritize these issues."
        ),
        "confidence": "HIGH",
    },
]


def seed_database() -> None:
    """Create tables and insert pre-built 311 requests into SQLite."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript(DDL)

    for req in SEED_REQUESTS:
        cursor.execute(
            """
            INSERT OR IGNORE INTO citizen_requests
                (request_id, raw_complaint_text, primary_department, urgency,
                 sla_hours, work_orders_json, acknowledgment_letter, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                req["request_id"],
                req["raw_complaint_text"],
                req["primary_department"],
                req["urgency"],
                req["sla_hours"],
                req["work_orders_json"],
                req["acknowledgment_letter"],
                req["confidence"],
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    conn.commit()
    conn.close()
    print(f"[seed_requests] Database seeded at {DB_PATH}")


if __name__ == "__main__":
    seed_database()
