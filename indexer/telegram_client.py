"""
INDEXER — Telethon Telegram Client

Research notes and implementation skeleton for Telegram userbot automation.
Telethon chosen over Pyrogram for Phase 1 (better async, more stable MTProto impl).

## Telethon vs Pyrogram Decision

| Factor | Telethon | Pyrogram |
|--------|----------|----------|
| MTProto impl | Pure Python, battle-tested | C extension (faster) |
| Async support | Native asyncio | Native asyncio |
| Community | Larger, more examples | Smaller |
| Documentation | Excellent | Good |
| Stability | More conservative | More experimental |
| Plugin system | Manual | Built-in filters |

**Decision: Telethon for Phase 1** — stability and documentation win.
Switch to Pyrogram if performance becomes an issue.

## ⚠️ Legal & ToS Notes

- Telegram allows userbots under their ToS as long as you:
  - Don't spam or mass-message
  - Don't scrape public channels for commercial resale
  - Use the account you own
- Risk: Telegram can ban the phone number if unusual activity is detected
- Mitigation: Rate limiting, human-like delays, dedicated secondary account
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Callable

log = logging.getLogger("indexer.telegram")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class TelegramConfig:
    """Telegram API credentials. Load from environment."""

    def __init__(self) -> None:
        self.api_id: int = int(os.getenv("TELEGRAM_API_ID", "0"))
        self.api_hash: str = os.getenv("TELEGRAM_API_HASH", "")
        self.session_name: str = os.getenv("TELEGRAM_SESSION", "indexer")
        self.session_dir: Path = Path(os.getenv("TELEGRAM_SESSION_DIR", "/app/data/sessions"))

    def validate(self) -> None:
        if not self.api_id or not self.api_hash:
            raise ValueError(
                "TELEGRAM_API_ID and TELEGRAM_API_HASH must be set.\n"
                "Get them at: https://my.telegram.org/apps"
            )

    @property
    def session_path(self) -> str:
        return str(self.session_dir / self.session_name)


# ---------------------------------------------------------------------------
# Telegram Indexer (Telethon wrapper)
# ---------------------------------------------------------------------------

class TelegramIndexer:
    """
    Telethon-based Telegram userbot for content indexing.

    Usage:
        indexer = TelegramIndexer(config, evaluator)
        await indexer.start()
        await indexer.monitor_channel("@channel_name", callback=my_callback)
        await indexer.idle()
    """

    def __init__(self, config: TelegramConfig, evaluator: Any | None = None) -> None:
        self._config = config
        self._evaluator = evaluator
        self._client = None  # Telethon TelegramClient (lazy import)

    async def start(self) -> None:
        """Initialize and connect the Telethon client."""
        try:
            from telethon import TelegramClient
        except ImportError:
            raise ImportError("Install telethon: pip install telethon cryptg")

        self._config.validate()
        self._config.session_dir.mkdir(parents=True, exist_ok=True)

        self._client = TelegramClient(
            self._config.session_path,
            self._config.api_id,
            self._config.api_hash,
        )
        await self._client.start()
        me = await self._client.get_me()
        log.info(f"Connected as: {me.username or me.phone}")

    async def stop(self) -> None:
        if self._client:
            await self._client.disconnect()

    async def monitor_channel(
        self,
        channel: str,
        callback: Callable | None = None,
    ) -> None:
        """
        Register a handler for new messages in a channel.

        Args:
            channel: Channel username or ID (e.g. "@ai_papers")
            callback: async function(message) -> None
        """
        if not self._client:
            raise RuntimeError("Call start() first")

        from telethon import events

        @self._client.on(events.NewMessage(chats=channel))
        async def handler(event):
            msg = event.message
            text = msg.text or ""
            if not text.strip():
                return

            log.debug(f"New message in {channel}: {text[:60]}")

            if self._evaluator:
                eval_result = self._evaluator.evaluate(text)
                if self._evaluator.should_skip(eval_result):
                    log.debug("Skipping (low relevance)")
                    return
                log.info(f"[{eval_result['priority']}] {eval_result['summary']}")

            if callback:
                await callback(msg, eval_result if self._evaluator else {})

    async def get_recent_messages(
        self,
        channel: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch recent messages from a channel for batch evaluation."""
        if not self._client:
            raise RuntimeError("Call start() first")

        messages = []
        async for msg in self._client.iter_messages(channel, limit=limit):
            if msg.text:
                messages.append({
                    "id": msg.id,
                    "date": msg.date.isoformat() if msg.date else None,
                    "text": msg.text,
                    "sender_id": msg.sender_id,
                })
        return messages

    async def idle(self) -> None:
        """Block until disconnected."""
        if self._client:
            await self._client.run_until_disconnected()

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "TelegramIndexer":
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.stop()


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

async def _test():
    config = TelegramConfig()
    try:
        config.validate()
    except ValueError as e:
        print(f"Config error: {e}")
        print("\nTo use the Telegram indexer:")
        print("  1. Go to https://my.telegram.org/apps")
        print("  2. Create an app and get API_ID + API_HASH")
        print("  3. Set env vars: TELEGRAM_API_ID, TELEGRAM_API_HASH")
        return

    async with TelegramIndexer(config) as indexer:
        print("Connected! Fetching recent messages from @durov (test)...")
        # msgs = await indexer.get_recent_messages("@durov", limit=5)
        # for m in msgs:
        #     print(f"  [{m['date']}] {m['text'][:80]}")
        print("Telegram indexer ready.")


if __name__ == "__main__":
    asyncio.run(_test())
