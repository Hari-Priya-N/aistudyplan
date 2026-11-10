# ============================================================
# Single-service image: builds the React app, then serves it
# from the FastAPI backend. One container = the whole project.
# Used by render.yaml (Render.com) and works on any Docker host
# (Railway, Fly.io, Hugging Face Spaces, a college server, ...).
# ============================================================

# ---- 1. Build the frontend ----
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# Empty base URL = call the API on the same origin that served the page.
ENV VITE_API_BASE_URL=""
RUN npm run build

# ---- 2. Backend + built frontend ----
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    STATIC_DIR=/app/static \
    CHROMA_PERSIST_DIR=/data/chroma \
    UPLOAD_DIR=/data/uploads

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=web /web/dist ./static
RUN mkdir -p /data/chroma /data/uploads

EXPOSE 8000
# Most hosts inject $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
