"""
streamlit_app.py

Government Citizen Intelligence Platform — Main Streamlit Application.
Single public process on Cloud Run port 8080.

Tab 1: 311 Citizen Request Classifier (Mode 1)
Tab 2: CJIS Security Policy Q&A Agent (Mode 2)

On startup: loads or builds the CJIS FAISS index and initializes the retriever.
"""

import logging
import os
import sqlite3
import uuid
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st

load_dotenv()  # loads GEMINI_API_KEY from .env for local dev; no-op in Cloud Run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "data" / "gov_intel.db"

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Gov Citizen Intelligence | GCP + Gemini",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
    /* Header */
    .gov-header {
        background: linear-gradient(135deg, #1a3a5c 0%, #0d2137 100%);
        border-radius: 10px;
        padding: 28px 36px 20px;
        margin-bottom: 24px;
        color: #fff;
    }
    .gov-header h1 { margin: 0; font-size: 1.9rem; font-weight: 700; }
    .gov-header p  { margin: 6px 0 0; opacity: 0.78; font-size: 0.95rem; }

    /* Urgency badges */
    .badge-critical { background:#c0392b; color:#fff; padding:4px 12px; border-radius:20px; font-weight:700; font-size:0.82rem; }
    .badge-high     { background:#e67e22; color:#fff; padding:4px 12px; border-radius:20px; font-weight:700; font-size:0.82rem; }
    .badge-medium   { background:#f39c12; color:#fff; padding:4px 12px; border-radius:20px; font-weight:700; font-size:0.82rem; }
    .badge-low      { background:#27ae60; color:#fff; padding:4px 12px; border-radius:20px; font-weight:700; font-size:0.82rem; }

    /* Department pill */
    .dept-pill { background:#2c3e50; color:#ecf0f1; padding:3px 10px; border-radius:12px; font-size:0.80rem; margin:2px; display:inline-block; }

    /* Cards */
    .work-order-card {
        background:#f8f9fa;
        border-left:4px solid #1a3a5c;
        border-radius:6px;
        padding:14px 16px;
        margin-bottom:12px;
    }
    .citation-card {
        background:#eaf4fb;
        border-left:4px solid #2980b9;
        border-radius:6px;
        padding:14px 16px;
        margin-bottom:12px;
    }
    .cannot-answer-box {
        background:#fdf2e9;
        border:2px solid #e67e22;
        border-radius:8px;
        padding:18px 20px;
        margin-top:16px;
    }
    .letter-box {
        background:#fafbfc;
        border:1px solid #dee2e6;
        border-radius:8px;
        padding:18px 20px;
        font-family: Georgia, serif;
        font-size:0.93rem;
        line-height:1.65;
        white-space: pre-wrap;
    }
    .answer-box {
        background:#f0f7ff;
        border-radius:8px;
        padding:18px 20px;
        font-size:0.95rem;
        line-height:1.7;
    }
    .confidence-high   { color:#27ae60; font-weight:700; }
    .confidence-medium { color:#e67e22; font-weight:700; }
    .confidence-low    { color:#c0392b; font-weight:700; }

    /* Metric block */
    .sla-block {
        text-align:center;
        background:#1a3a5c;
        color:#fff;
        border-radius:8px;
        padding:16px 10px;
        margin-bottom:8px;
    }
    .sla-block .sla-num  { font-size:2.2rem; font-weight:800; }
    .sla-block .sla-unit { font-size:0.85rem; opacity:0.8; }

    /* Section label */
    .section-label { font-size:0.78rem; text-transform:uppercase; letter-spacing:0.08em; color:#6c757d; font-weight:600; margin-bottom:6px; }

    /* History row */
    .history-row { border-bottom:1px solid #e9ecef; padding:8px 0; font-size:0.88rem; }
</style>
""",
    unsafe_allow_html=True,
)

# ── FAISS Index — load once, cache for the lifetime of the server ─────────────
@st.cache_resource(show_spinner=False)
def _load_index():
    """Load or build the CJIS FAISS index. Cached across all Streamlit reruns."""
    from app.rag import build_index, retriever as _retriever

    idx, cks = build_index.load_or_build_index()
    _retriever.initialize(idx, cks)
    return idx, cks


with st.spinner("⏳ Loading CJIS Security Policy index…"):
    _faiss_index, _cjis_chunks = _load_index()

# Import modes AFTER the index is ready (retriever.initialize already called)
from app.modes.classify_311 import classify_311_request
from app.modes.query_cjis import query_cjis_policy
from app.data.seed_requests import SEED_REQUESTS
from app.data.sample_queries import SAMPLE_CJIS_QUERIES

# ── Helpers ───────────────────────────────────────────────────────────────────

def _urgency_badge(urgency: str) -> str:
    """Return an HTML urgency badge for the given urgency string."""
    cls = f"badge-{urgency.lower()}"
    return f'<span class="{cls}">{urgency}</span>'


def _sla_label(sla_hours: int) -> str:
    """Convert SLA hours to a human-readable string."""
    if sla_hours < 24:
        return f"{sla_hours} hour{'s' if sla_hours != 1 else ''}"
    days = sla_hours // 24
    return f"{days} day{'s' if days != 1 else ''}"


def _confidence_html(conf: str) -> str:
    cls = f"confidence-{conf.lower()}"
    return f'<span class="{cls}">{conf}</span>'


def _get_request_history(limit: int = 10):
    """Fetch the most recent citizen_requests rows from SQLite."""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT request_id, raw_complaint_text, primary_department, urgency,
                   sla_hours, confidence, created_at
            FROM citizen_requests
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return rows


def _get_query_history(limit: int = 10):
    """Fetch the most recent cjis_queries rows from SQLite."""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT query_id, question_text, confidence, cannot_answer, created_at
            FROM cjis_queries
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return rows


def _next_request_id() -> str:
    """Generate a sequential request ID based on the current DB row count."""
    if not DB_PATH.exists():
        return "REQ-006"
    conn = sqlite3.connect(DB_PATH)
    try:
        count = conn.execute("SELECT COUNT(*) FROM citizen_requests").fetchone()[0]
    finally:
        conn.close()
    return f"REQ-{count + 1:03d}"


def _next_query_id() -> str:
    """Generate a sequential query ID based on the current DB row count."""
    if not DB_PATH.exists():
        return "Q-006"
    conn = sqlite3.connect(DB_PATH)
    try:
        count = conn.execute("SELECT COUNT(*) FROM cjis_queries").fetchone()[0]
    finally:
        conn.close()
    return f"Q-{count + 1:03d}"


# ── App Header ────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="gov-header">
  <h1>🏛️ Government Citizen Intelligence Platform</h1>
  <p>GCP-native dual-mode AI · Gemini 2.5 Flash · FAISS RAG · Built for GTS Government Verticals</p>
</div>
""",
    unsafe_allow_html=True,
)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(
    ["🏙️ 311 Citizen Request Classifier", "🔒 CJIS Policy Q&A"]
)

# =============================================================================
# TAB 1 — 311 CITIZEN REQUEST CLASSIFIER
# =============================================================================
with tab1:
    st.markdown("### 311 Citizen Request Classifier")
    st.markdown(
        "Paste any citizen complaint — single issue or multi-department. "
        "The agent classifies it, assigns urgency, decomposes work orders, "
        "and drafts a personalized acknowledgment letter."
    )

    # Build the dropdown labels for the 5 pre-built complaints
    seed_options = {
        f"{r['request_id']} — {r['raw_complaint_text'][:72]}…": r["raw_complaint_text"]
        for r in SEED_REQUESTS
    }
    dropdown_labels_311 = ["✏️ Enter my own complaint…"] + list(seed_options.keys())

    selected_311 = st.selectbox(
        "Select a pre-built complaint or enter your own:",
        options=dropdown_labels_311,
        key="dropdown_311",
    )

    if selected_311 == "✏️ Enter my own complaint…":
        complaint_text = st.text_area(
            "Citizen complaint:",
            height=130,
            placeholder=(
                "Example: There's a large pothole on Oak Street near the school, "
                "and the streetlight there has been broken for two weeks…"
            ),
            key="custom_complaint",
        )
    else:
        complaint_text = seed_options[selected_311]
        st.text_area(
            "Complaint text (pre-filled):",
            value=complaint_text,
            height=130,
            disabled=True,
            key="prefilled_complaint",
        )

    classify_btn = st.button(
        "🔍 Classify Request", type="primary", use_container_width=False, key="btn_classify"
    )

    if classify_btn:
        if not complaint_text or not complaint_text.strip():
            st.warning("Please enter or select a complaint before classifying.")
        else:
            with st.spinner("Classifying with Gemini 2.5 Flash…"):
                try:
                    request_id = _next_request_id()
                    result = classify_311_request(
                        request_id=request_id,
                        complaint_text=complaint_text.strip(),
                    )
                    st.session_state["last_311_result"] = result
                    st.session_state["last_311_complaint"] = complaint_text.strip()
                except Exception as exc:
                    st.error(f"Classification failed: {exc}")
                    logger.exception("[UI] classify_311_request error")

    # ── Results ───────────────────────────────────────────────────────────────
    if "last_311_result" in st.session_state:
        res = st.session_state["last_311_result"]
        st.divider()
        st.markdown("#### Classification Results")

        col_summary, col_orders, col_letter = st.columns([1, 1.4, 1.4])

        with col_summary:
            st.markdown('<div class="section-label">Classification Summary</div>', unsafe_allow_html=True)

            st.markdown(
                f'**Primary Department**<br>'
                f'<span class="dept-pill">{res.primary_department.value}</span>',
                unsafe_allow_html=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown(
                f'**Urgency Level**<br>'
                f'{_urgency_badge(res.urgency.value)}',
                unsafe_allow_html=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown(
                f"""
<div class="sla-block">
  <div class="sla-num">{_sla_label(res.sla_hours)}</div>
  <div class="sla-unit">Response SLA</div>
</div>
""",
                unsafe_allow_html=True,
            )
            st.markdown(
                f'**Confidence:** {_confidence_html(res.classification_confidence)}',
                unsafe_allow_html=True,
            )
            st.markdown(f'**Request ID:** `{res.request_id}`')

        with col_orders:
            st.markdown('<div class="section-label">Work Orders</div>', unsafe_allow_html=True)
            st.markdown(
                f"**{len(res.work_orders)} department{'s' if len(res.work_orders) != 1 else ''} assigned**"
            )
            for wo in res.work_orders:
                st.markdown(
                    f"""
<div class="work-order-card">
  <strong>{wo.department.value}</strong>&nbsp;&nbsp;
  {_urgency_badge(wo.urgency.value)}<br>
  <small>⏱ Respond within {_sla_label(wo.sla_hours)} &nbsp;|&nbsp; {wo.action_type.value}</small><br>
  <span style="font-size:0.9rem;">{wo.issue_description}</span>
</div>
""",
                    unsafe_allow_html=True,
                )

        with col_letter:
            st.markdown('<div class="section-label">Acknowledgment Letter</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="letter-box">{res.acknowledgment_letter}</div>',
                unsafe_allow_html=True,
            )
            st.code(res.acknowledgment_letter, language=None)
            st.caption("👆 Copy the text above to send to the citizen.")

    # ── Request History ───────────────────────────────────────────────────────
    with st.expander("📋 Recent Classification History (last 10)", expanded=False):
        history = _get_request_history(10)
        if not history:
            st.info("No requests classified yet.")
        else:
            for row in history:
                req_id, text, dept, urgency, sla, conf, ts = row
                st.markdown(
                    f'<div class="history-row">'
                    f'<strong>{req_id}</strong> &nbsp;·&nbsp; '
                    f'<span class="dept-pill">{dept}</span> &nbsp;·&nbsp; '
                    f'{_urgency_badge(urgency)} &nbsp;·&nbsp; '
                    f'SLA {_sla_label(sla)} &nbsp;·&nbsp; '
                    f'Confidence {_confidence_html(conf)} &nbsp;·&nbsp; '
                    f'<small>{ts[:19]}</small><br>'
                    f'<small style="color:#6c757d;">{text[:100]}…</small>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

# =============================================================================
# TAB 2 — CJIS POLICY Q&A
# =============================================================================
with tab2:
    st.markdown("### CJIS Security Policy Q&A Agent")
    st.markdown(
        "Ask any question about the FBI CJIS Security Policy. "
        "The agent retrieves the relevant sections from the official policy document "
        "and returns a cited, grounded answer — no hallucination."
    )

    query_options = {q["label"]: q["question"] for q in SAMPLE_CJIS_QUERIES}
    dropdown_labels_cjis = ["✏️ Enter my own question…"] + list(query_options.keys())

    selected_cjis = st.selectbox(
        "Select a pre-built question or enter your own:",
        options=dropdown_labels_cjis,
        key="dropdown_cjis",
    )

    if selected_cjis == "✏️ Enter my own question…":
        cjis_question = st.text_area(
            "Your CJIS policy question:",
            height=100,
            placeholder="Example: What does CJIS require for mobile device management?",
            key="custom_cjis_q",
        )
    else:
        cjis_question = query_options[selected_cjis]
        st.text_area(
            "Question (pre-filled):",
            value=cjis_question,
            height=100,
            disabled=True,
            key="prefilled_cjis_q",
        )

    search_btn = st.button(
        "🔎 Search Policy", type="primary", use_container_width=False, key="btn_search"
    )

    if search_btn:
        if not cjis_question or not cjis_question.strip():
            st.warning("Please enter or select a question before searching.")
        else:
            with st.spinner("Retrieving CJIS policy sections and generating answer…"):
                try:
                    query_id = _next_query_id()
                    cjis_result = query_cjis_policy(
                        query_id=query_id,
                        question=cjis_question.strip(),
                    )
                    st.session_state["last_cjis_result"] = cjis_result
                except Exception as exc:
                    st.error(f"Policy search failed: {exc}")
                    logger.exception("[UI] query_cjis_policy error")

    # ── Results ───────────────────────────────────────────────────────────────
    if "last_cjis_result" in st.session_state:
        cr = st.session_state["last_cjis_result"]
        st.divider()

        if cr.cannot_answer:
            st.markdown(
                """
<div class="cannot-answer-box">
  <strong>⚠️ This question may be outside CJIS scope or the answer requires clarification.</strong><br><br>
  The retrieved policy sections do not contain sufficient information to answer reliably.
  Consult your <strong>CJIS Systems Officer (CSO)</strong> directly for authoritative guidance.
</div>
""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown("#### Policy Answer")
            col_answer, col_citations = st.columns([1.5, 1])

            with col_answer:
                st.markdown('<div class="section-label">Based on CJIS policy:</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="answer-box">{cr.answer}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown("<br>", unsafe_allow_html=True)
                conf_col1, conf_col2 = st.columns(2)
                with conf_col1:
                    st.markdown(
                        f'**Answer Confidence:** {_confidence_html(cr.confidence)}',
                        unsafe_allow_html=True,
                    )
                with conf_col2:
                    st.markdown(f'**Query ID:** `{cr.query_id}`')

            with col_citations:
                st.markdown('<div class="section-label">Policy Citations</div>', unsafe_allow_html=True)
                if cr.citations:
                    for citation in cr.citations:
                        st.markdown(
                            f"""
<div class="citation-card">
  <strong>§ {citation.section_id}</strong> — {citation.section_title}<br>
  <small style="color:#555;">{citation.policy_version}</small><br>
  <span style="font-size:0.88rem;">{citation.relevance}</span>
</div>
""",
                            unsafe_allow_html=True,
                        )
                else:
                    st.info("No citations extracted from retrieved sections.")

    # ── Query History ─────────────────────────────────────────────────────────
    with st.expander("📋 Recent Query History (last 10)", expanded=False):
        q_history = _get_query_history(10)
        if not q_history:
            st.info("No queries submitted yet.")
        else:
            for row in q_history:
                q_id, question, conf, cannot, ts = row
                cannot_tag = (
                    ' &nbsp;<span style="color:#e67e22;font-size:0.8rem;">cannot answer</span>'
                    if cannot
                    else ""
                )
                st.markdown(
                    f'<div class="history-row">'
                    f'<strong>{q_id}</strong> &nbsp;·&nbsp; '
                    f'Confidence {_confidence_html(conf)}{cannot_tag} &nbsp;·&nbsp; '
                    f'<small>{ts[:19]}</small><br>'
                    f'<small style="color:#6c757d;">{question[:110]}…</small>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    """
<div style="text-align:center; color:#6c757d; font-size:0.80rem; padding:8px 0;">
  <strong>CJIS Disclaimer:</strong> This tool answers questions about the publicly available
  FBI CJIS Security Policy document. It does not process, store, or transmit actual
  Criminal Justice Information. &nbsp;|&nbsp;
  Built on GCP · Gemini 2.5 Flash · FAISS · Cloud Run
</div>
""",
    unsafe_allow_html=True,
)
