FROM python:3.11-slim

WORKDIR /app

# Ensure 'from app.xxx import ...' resolves correctly regardless of how
# Streamlit manipulates sys.path at startup
ENV PYTHONPATH=/app

# System dependencies for FAISS and PDF download
RUN apt-get update && apt-get install -y \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Download CJIS Security Policy PDF at build time (public document).
# Primary URL: FBI CJIS Security Policy v5.9.5 (December 2024).
# Falls back gracefully if unavailable — the index will fail to build at runtime
# with a clear error message rather than silently using a missing file.
RUN wget -q -O app/rag/cjis_policy.pdf \
    "https://le.fbi.gov/cjis-division/cjis-security-policy/resource-center/cjis-security-policy-resource-center/2024/cjis-security-policy-v5-9-5-20241217.pdf" \
    || wget -q -O app/rag/cjis_policy.pdf \
    "https://www.dps.texas.gov/sites/default/files/documents/administration/cjis/cjis-security-policy-v5-9-5-20241217.pdf" \
    || echo "WARNING: CJIS PDF download failed. The FAISS index cannot be built at runtime without the PDF."

# Seed SQLite database with tables and pre-built 311 demo data
RUN python app/data/seed_requests.py

# Single port — Cloud Run requirement
EXPOSE 8080

# Single process — Streamlit is the only listener
CMD ["streamlit", "run", "app/streamlit_app.py", \
     "--server.port=8080", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
