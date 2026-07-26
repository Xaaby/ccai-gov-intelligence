"""
sample_queries.py
5 pre-built CJIS Security Policy questions used in the Mode 2 demo dropdown.
Imported directly by streamlit_app.py — not a runnable script.
"""

SAMPLE_CJIS_QUERIES = [
    {
        "query_id": "Q-001",
        "question": "What encryption standard does CJIS require for data at rest on mobile devices?",
        "label": "Q-001 — Mobile device encryption standard",
    },
    {
        "query_id": "Q-002",
        "question": "How often must agencies conduct security awareness training under CJIS?",
        "label": "Q-002 — Security awareness training frequency",
    },
    {
        "query_id": "Q-003",
        "question": "What are the CJIS requirements for multi-factor authentication?",
        "label": "Q-003 — Multi-factor authentication (MFA) requirements",
    },
    {
        "query_id": "Q-004",
        "question": "Can cloud service providers store Criminal Justice Information, and what must they comply with?",
        "label": "Q-004 — Cloud provider data storage rules",
    },
    {
        "query_id": "Q-005",
        "question": "What does CJIS require for incident response planning and reporting?",
        "label": "Q-005 — Incident response planning requirements",
    },
]
