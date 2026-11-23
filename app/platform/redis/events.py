"""Status events: workers/services PUBLISH, the SSE endpoint SUBSCRIBES."""
import json

from app.platform.redis import keys
from app.platform.redis.errors import translate_redis_errors
from app.platform.shared.clock import utcnow


async def publish_status(redis, file_id: str, status: str, **extra) -> None:
    payload = {"type": "status", "file_id": file_id, "status": status, "at": utcnow().isoformat(), **extra}
    with translate_redis_errors("events.publish"):
        await redis.publish(keys.events_channel(file_id), json.dumps(payload))
