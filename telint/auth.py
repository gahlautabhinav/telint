"""
Telethon MTProto client wrapper for telint.
"""

import asyncio

from telethon import TelegramClient
from config import settings

_client: TelegramClient | None = None
_lock = asyncio.Lock()


async def get_client() -> TelegramClient:
    """Return authenticated client, creating/starting if needed."""
    global _client
    async with _lock:
        if _client is None or not _client.is_connected():
            _client = TelegramClient(
                settings.session_name,
                settings.api_id,
                settings.api_hash,
            )
            await _client.start(phone=settings.phone)
    return _client


async def stop_client() -> None:
    """Disconnect client if connected."""
    global _client
    if _client is not None and _client.is_connected():
        await _client.disconnect()
