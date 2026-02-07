FROM python:3.11

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libopus0 \
    libsodium23 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

COPY config.py .
COPY pyproject.toml .
COPY src/ ./src/
COPY scripts/ ./scripts/

ENV PYTHONUNBUFFERED=1

COPY start.sh .
RUN chmod +x start.sh
CMD ["bash", "start.sh"]