"""
INDEXER — LLM Content Evaluator

Uses Ollama/mistral-nemo to evaluate and categorize incoming content
using the prompts defined in docs/indexer/llm_prompts.md
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

log = logging.getLogger("indexer.evaluator")

# ---------------------------------------------------------------------------
# Prompts (inline for portability; source of truth in docs/indexer/llm_prompts.md)
# ---------------------------------------------------------------------------

RELEVANCE_SYSTEM = """You are a content evaluator for the CORTEX intelligence system.
Given a piece of content, return a JSON object with EXACTLY this schema:
{
  "relevance_score": <float 0.0-1.0>,
  "category": <string>,
  "subcategory": <string>,
  "priority": <"P1"|"P2"|"P3"|"SKIP">,
  "tags": [<string>],
  "summary": <string, max 80 chars>,
  "action_required": <boolean>,
  "reason": <string>
}

Category options: "ai_ml", "security", "gaming", "news", "research",
"personal", "tech", "finance", "entertainment", "spam", "unknown"

Priority rules:
- P1: Time-sensitive, security alerts, major AI releases, urgent tasks
- P2: Interesting research, project updates, valuable links
- P3: Background info, general news, entertainment
- SKIP: Spam, irrelevant, already processed

Respond ONLY with valid JSON. No preamble."""

LINK_ENRICHER_SYSTEM = """You are a research assistant enriching URL metadata.
Given a URL and optional page title/description, return JSON:
{
  "content_type": <"paper"|"article"|"repo"|"tool"|"video"|"forum"|"other">,
  "estimated_quality": <float 0.0-1.0>,
  "topics": [<string>],
  "suggested_collection": <string>,
  "tldr": <string, max 120 chars>,
  "save_to_library": <boolean>
}
Be conservative with estimated_quality (0.3-0.7 for most content, 0.9+ for landmarks).
Respond ONLY with valid JSON."""


# ---------------------------------------------------------------------------
# Ollama Client
# ---------------------------------------------------------------------------

class OllamaClient:
    """Minimal Ollama HTTP client for content evaluation."""

    def __init__(self, host: str = "http://localhost:11434", model: str = "mistral-nemo") -> None:
        self.host = host.rstrip("/")
        self.model = model

    def generate(self, system: str, user: str, temperature: float = 0.1) -> str:
        """Generate a response from Ollama. Low temperature for reliable JSON output."""
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n",
            "stream": False,
            "options": {"temperature": temperature, "num_predict": 512},
        }
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["response"]

    def generate_json(self, system: str, user: str) -> dict[str, Any]:
        """Generate and parse JSON response. Returns {} on parse failure."""
        raw = self.generate(system, user)
        try:
            # Strip markdown code blocks if present
            clean = raw.strip()
            if clean.startswith("```"):
                clean = "\n".join(clean.split("\n")[1:-1])
            return json.loads(clean)
        except json.JSONDecodeError as e:
            log.warning(f"JSON parse failed: {e} | raw: {raw[:200]}")
            return {}


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

class ContentEvaluator:
    """Evaluates and categorizes incoming content using LLM."""

    def __init__(self, ollama_host: str = "http://localhost:11434", model: str = "mistral-nemo") -> None:
        self._llm = OllamaClient(host=ollama_host, model=model)

    def evaluate(self, content: str, max_chars: int = 2000) -> dict[str, Any]:
        """
        Evaluate content relevance and category.

        Returns a dict matching the RELEVANCE schema.
        """
        truncated = content[:max_chars]
        user = f"Content to evaluate:\n{truncated}"
        result = self._llm.generate_json(RELEVANCE_SYSTEM, user)

        # Validate and set defaults
        defaults = {
            "relevance_score": 0.5,
            "category": "unknown",
            "subcategory": "",
            "priority": "P3",
            "tags": [],
            "summary": truncated[:80],
            "action_required": False,
            "reason": "Parse error — defaults applied",
        }
        return {**defaults, **result}

    def enrich_link(self, url: str, title: str = "", description: str = "") -> dict[str, Any]:
        """
        Enrich a URL with metadata.

        Returns a dict matching the LINK_ENRICHER schema.
        """
        user = f"URL: {url}\nTitle: {title}\nDescription: {description}"
        result = self._llm.generate_json(LINK_ENRICHER_SYSTEM, user)

        defaults = {
            "content_type": "other",
            "estimated_quality": 0.5,
            "topics": [],
            "suggested_collection": "general",
            "tldr": title[:120] if title else url,
            "save_to_library": False,
        }
        return {**defaults, **result}

    def should_skip(self, evaluation: dict[str, Any]) -> bool:
        """Returns True if content should be discarded."""
        return evaluation.get("priority") == "SKIP" or evaluation.get("relevance_score", 0) < 0.2


# ---------------------------------------------------------------------------
# CLI Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    evaluator = ContentEvaluator(
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        model=os.getenv("OLLAMA_MODEL", "mistral-nemo"),
    )

    test_content = """
    Anthropic releases Claude 4 with 1M context window and real-time web browsing.
    The model significantly outperforms GPT-5 on coding benchmarks.
    Available now on Claude.ai.
    """

    print("Evaluating test content...")
    result = evaluator.evaluate(test_content)
    print(json.dumps(result, indent=2))

    print("\nEnriching test URL...")
    link = evaluator.enrich_link(
        "https://arxiv.org/abs/2501.12345",
        title="Scaling Laws for LLM Agents",
        description="We study how agent performance scales with compute...",
    )
    print(json.dumps(link, indent=2))
