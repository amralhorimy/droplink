"""Janitor worker:  python -m workers.janitor

Wakes up every N seconds, takes a Redis lock (so only ONE janitor works at a time
even if you run several), and cleans expired data.
"""
import asyncio
import logging

from app.platform.infra import Infra
from app.platform.redis import keys
from app.platform.shared.config import get_settings
from app.platform.shared.errors import AppError
from workers.janitor.sweeper import sweep_once
from workers.runtime import bootstrap

log = logging.getLogger("droplink.janitor")


async def main() -> None:
    stop = bootstrap()
    s = get_settings()
    infra = await Infra.connect(s)
    log.info("janitor %s started (every %ss)", s.worker_id, s.janitor_interval_seconds)
    try:
        while not stop.is_set():
            try:
                # SET NX EX = "whoever sets it first owns this round"; it expires by itself.
                got_lock = await infra.redis.set(
                    keys.janitor_lock(), s.worker_id, nx=True, ex=max(5, s.janitor_interval_seconds - 1)
                )
                if got_lock:
                    stats = await sweep_once(infra)
                    if any(vars(stats).values()):
                        log.info("sweep done: %s", stats)
            except AppError as exc:
                log.error("sweep failed: %s", exc.log_message)
            except Exception:  # noqa: BLE001
                log.exception("unexpected janitor error")
            try:
                await asyncio.wait_for(stop.wait(), timeout=s.janitor_interval_seconds)
            except asyncio.TimeoutError:
                pass
    finally:
        await infra.close()
        log.info("janitor stopped")


if __name__ == "__main__":
    asyncio.run(main())
