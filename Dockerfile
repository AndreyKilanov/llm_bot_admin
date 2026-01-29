FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py .
COPY pyproject.toml .
COPY src/ ./src/
COPY scripts/ ./scripts/

ENV PYTHONUNBUFFERED=1

COPY start.sh .
RUN chmod +x start.sh
CMD ["./start.sh"]