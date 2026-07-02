FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# cloudflared quick tunnel: 无公网 IP 时自动为阿里云 ASR 回拉音频建立临时隧道
ARG CLOUDFLARED_VERSION=2024.12.2
RUN arch=$(uname -m) && \
    case "$arch" in x86_64) cf_arch=amd64 ;; aarch64) cf_arch=arm64 ;; *) echo "unsupported arch $arch" && exit 1 ;; esac && \
    curl -fsSL -o /usr/local/bin/cloudflared \
      "https://github.com/cloudflare/cloudflared/releases/download/${CLOUDFLARED_VERSION}/cloudflared-linux-${cf_arch}" && \
    chmod +x /usr/local/bin/cloudflared

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]