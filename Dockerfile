# Project INDEXER — Containerized Python Environment
# Telethon + Pyrogram userbot + LLM evaluation pipeline

FROM python:3.11-slim

LABEL project="indexer" \
      description="CORTEX Communication Intelligence — Telegram/Discord content pipeline"

# System deps for cryptg (Telethon speedup) and Pyrogram
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create data directory
RUN mkdir -p /app/data/sessions /app/data/logs

# Environment variables (override at runtime)
ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    OLLAMA_HOST=http://host.containers.internal:11434

CMD ["python", "-m", "indexer.main"]
