import redis.asyncio as aioredis

from app.platform.shared.config import Settings


def create_redis(settings: Settings) -> aioredis.Redis:
    return aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=15,  # blocking calls below use shorter timeouts (<= 10s)
        health_check_interval=30,
    )
