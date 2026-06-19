# ═══════════════════════════════════════════════════════════════════
# EDM v2 — Backend Dockerfile
# ═══════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system deps for psycopg2, pdfplumber, Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-ell \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime system deps (only what's needed at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    tesseract-ocr \
    tesseract-ocr-ell \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY backend/ .

# Create uploads directory
RUN mkdir -p /app/uploads

EXPOSE 8887

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8887", "--workers", "2"]
