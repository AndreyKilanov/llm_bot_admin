FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libopus0 \
    libsodium23 \
    && rm -rf /var/lib/apt/lists/*

RUN uv sync --frozen --no-dev

COPY config.py .
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY start.sh .
RUN chmod +x start.sh
CMD ["./start.sh"]