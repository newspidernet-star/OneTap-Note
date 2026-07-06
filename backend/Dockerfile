FROM node:20-bookworm-slim AS frontend

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# cloudflared quick tunnel for remote ASR callbacks when no public IP is available.
ARG CLOUDFLARED_VERSION=2024.12.2
RUN arch=$(uname -m) && \
    case "$arch" in x86_64) cf_arch=amd64 ;; aarch64) cf_arch=arm64 ;; *) echo "unsupported arch $arch" && exit 1 ;; esac && \
    curl -fsSL -o /usr/local/bin/cloudflared \
      "https://github.com/cloudflare/cloudflared/releases/download/${CLOUDFLARED_VERSION}/cloudflared-linux-${cf_arch}" && \
    chmod +x /usr/local/bin/cloudflared

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

COPY backend/ .
COPY --from=frontend /frontend/dist /app/frontend/dist

ENV SMART_SCRIBE_FRONTEND_DIST_DIR=/app/frontend/dist

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
