FROM python:3.12-slim

# Install system dependencies including Tesseract OCR and development libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency requirements
COPY requirements.txt .

# Install dependencies and spaCy language model
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm

# Create evidence vault storage directory
RUN mkdir -p /app/data/evidence_vault

# Copy backend application code
COPY app/ ./app/

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    TESSERACT_CMD=/usr/bin/tesseract \
    EVIDENCE_VAULT_DIR=/app/data/evidence_vault

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
