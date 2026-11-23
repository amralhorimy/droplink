"""Tiny retry helper used at start-up, while containers are still booting."""
import asyncio
import logging

from app.platform.shared.errors import ServiceUnavailable

log = logging.getLogger("droplink.retry")


async def retry_async(fn, *, attempts: int, delay: float, what: str, retry_on=(ServiceUnavailable,)):
    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except retry_on as exc:
            if attempt == attempts:
                raise
            log.warning("%s not ready (%d/%d): %s", what, attempt, attempts, getattr(exc, "log_message", exc))
            await asyncio.sleep(delay)
