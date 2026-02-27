# Use official Python image
FROM python:3.10-slim

# ----------------------------
# Environment variables
# ----------------------------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence_transformers \
    HF_HUB_DISABLE_TELEMETRY=1

# Set workdir
WORKDIR /app

# ----------------------------
# OS dependencies
# ----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------
# Install Python dependencies (best layer caching)
# ----------------------------
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# ----------------------------
# Copy project files
# ----------------------------
COPY . .

# ----------------------------
# Bake embedding model into image (so ECS doesn't need outbound internet)
# ----------------------------
RUN python - <<'PY'
from sentence_transformers import SentenceTransformer
SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
print("✅ Pre-downloaded: sentence-transformers/all-MiniLM-L6-v2")
PY

# Expose port
EXPOSE 8080

# ----------------------------
# Run FastAPI with uvicorn (production)
# ----------------------------
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]

# Run FastAPI with uvicorn
#CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]

#docker start my-doc-portal
#docker build -t document-portal-system .
#docker run -d -p 8093:8080 --name my-doc-portal document-portal-system
#docker stop my-doc-portal
#docker rm my-doc-portal