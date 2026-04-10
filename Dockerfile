# ── EarthPulse Backend — Docker image ────────────────────────────────────────
# Used for: Render, Fly.io, Railway, or any Docker-capable host.
# Build context: repo root (docker build -t earthpulse-api .)
# Runtime: uvicorn on port 8000 (or $PORT if set by the platform)

FROM python:3.12-slim

# System deps (httpx needs certifi; nothing exotic needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached layer unless requirements change)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code + static data
COPY backend/ ./backend/
COPY data/    ./data/

# Non-root user for security
RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8000

# $PORT is injected by Render/Fly/Railway; default to 8000 locally.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
