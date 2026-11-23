"""Live status over Server-Sent Events, fed by Redis pub/sub."""
import asyncio
import json
import logging
from contextlib import suppress

from app.modules.files import domain
from app.modules.files.service import FilesService
from app.platform.redis import keys
from app.platform.redis.errors import translate_redis_errors
from app.platform.shared.clock import utcnow
from app.platform.shared.errors import AppError

log = logging.getLogger("droplink.events")
MAX_STREAM_SECONDS = 120


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


class EventStream:
    def __init__(self, pubsub, channel: str, snapshot: dict) -> None:
        self._pubsub = pubsub
        self._channel = channel
        self._snapshot = snapshot

    async def iterate(self, request):
        try:
            yield sse("status", self._snapshot)
            if self._snapshot["status"] in domain.TERMINAL:
                return
            loop = asyncio.get_running_loop()
            deadline = loop.time() + MAX_STREAM_SECONDS
            while loop.time() < deadline:
                if await request.is_disconnected():
                    return
                try:
                    with translate_redis_errors("events.read"):
                        message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=10)
                except AppError as exc:
                    log.warning("event stream interrupted: %s", exc.log_message)
                    yield sse("error", {"code": "stream_interrupted"})
                    return
                if message is None:
                    yield ": keep-alive\n\n"  # keeps proxies from closing an idle connection
                    continue
                data = json.loads(message["data"])
                yield sse("status", data)
                if data.get("status") in domain.TERMINAL:
                    return
            yield sse("timeout", {"message": "stream time limit reached, reconnect to continue"})
        finally:
            with suppress(Exception):
                await self._pubsub.unsubscribe(self._channel)
            with suppress(Exception):
                await self._pubsub.aclose()


class EventsService:
    def __init__(self, redis, files: FilesService) -> None:
        self._redis = redis
        self._files = files

    async def open(self, file_id: str, token: str) -> EventStream:
        await self._files.get_authorized(file_id, token)
        channel = keys.events_channel(file_id)
        pubsub = self._redis.pubsub()
        try:
            with translate_redis_errors("events.subscribe"):
                await pubsub.subscribe(channel)
            # Snapshot AFTER subscribing: nothing that happens in between can be missed.
            doc = await self._files.get_authorized(file_id, token)
        except BaseException:
            with suppress(Exception):
                await pubsub.aclose()
            raise
        snapshot = {"type": "status", "file_id": file_id, "status": doc["status"], "at": utcnow().isoformat()}
        return EventStream(pubsub, channel, snapshot)
