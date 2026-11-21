# ==============================================================================
# DarkShield AI - Production Backend Dockerfile
# Optimized for Python 3.12, FastAPI, Scikit-learn & Playwright Headless Chromium
# ==============================================================================

FROM python:3.12-slim-bookworm

# Set container environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PORT=8000 \
    HOST=0.0.0.0 \
    SCAN_HEADLESS=true

WORKDIR /app

# Install system dependencies required for curl health checks and Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser and its Linux OS shared libraries
RUN playwright install --with-deps chromium

# Copy application source code and models
COPY backend/ ./backend/
COPY main.py .

# Ensure data persistence directories exist inside container
RUN mkdir -p /app/backend/data/scans \
             /app/backend/data/website_scans \
             /app/backend/data/website_snapshots

# Cloud platforms assign a dynamic PORT at runtime
EXPOSE 8000

# Docker healthcheck checking the FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-8000}/health || exit 1

# Start Uvicorn bound to 0.0.0.0 and dynamic $PORT with 1 worker (optimal for free-tier memory)
CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
