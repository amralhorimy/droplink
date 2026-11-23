"""Boilerplate every worker needs: logging, graceful shutdown on SIGTERM/SIGINT."""
import asyncio
import signal

from app.platform.shared.config import get_settings
from app.platform.shared.logging import setup_logging


def bootstrap() -> asyncio.Event:
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_json)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)  # `docker stop` => finish current job, then exit
    return stop
