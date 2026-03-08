# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Semantic knowledge retrieval and memory consolidation system. Telegram/Discord content pipeline for CORTEX intelligence using LLM-based content evaluation and categorization.

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11 (async) |
| Telegram | Telethon (userbot, MTProto) |
| LLM | Ollama (mistral-nemo) |
| Database | SQLite (async, deduplication) |
| Extraction | BeautifulSoup4, trafilatura |
| Packaging | Docker (multi-stage, Python 3.11-slim) |

## Project Structure

```
project-indexer/
├── indexer/
│   ├── telegram_client.py   # Telethon userbot with MTProto async
│   ├── evaluator.py          # LLM-based content categorization (relevance scoring, tagging)
│   └── main.py               # Entry point
├── requirements.txt
├── Dockerfile
└── PROJECT.md                # Roadmap (Reflexion loop, Qdrant, memory consolidation)
```

## Key Commands

```bash
docker build -t project-indexer .
python -m indexer.main              # Run directly
```

## Cross-Repo Relationships

- **cortex** — PIANO architecture integration planned
- **shared-skills** — LLM provider routing
- **OpenClaw-Vault** — Knowledge destination

## Things to Avoid

- Don't hardcode `/home/yish` — use `$HOME` or `/var/home/yish`
- Don't run without Ollama available — evaluator requires local LLM
