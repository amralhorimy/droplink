"""A small reliable queue on Redis lists.

producer : LPUSH queue job
consumer : BLMOVE queue -> processing:<worker>   (job is never "in flight" without a copy)
ack      : LREM processing:<worker> job
crash    : on start-up the worker re-queues whatever is left in its own processing list
"""
import json

from app.platform.redis import keys
from app.platform.redis.errors import translate_redis_errors


async def enqueue_job(redis, queue: str, payload: dict) -> None:
    with translate_redis_errors("jobs.enqueue"):
        await redis.lpush(queue, json.dumps(payload))


async def fetch_job(redis, queue: str, worker_id: str, timeout: int = 5) -> str | None:
    with translate_redis_errors("jobs.fetch"):
        return await redis.blmove(queue, keys.processing_list(queue, worker_id), timeout, src="RIGHT", dest="LEFT")


async def ack_job(redis, queue: str, worker_id: str, raw: str) -> None:
    with translate_redis_errors("jobs.ack"):
        await redis.lrem(keys.processing_list(queue, worker_id), 1, raw)


async def recover_jobs(redis, queue: str, worker_id: str) -> int:
    """Put jobs this worker was holding when it died back on the queue."""
    proc = keys.processing_list(queue, worker_id)
    with translate_redis_errors("jobs.recover"):
        leftovers = await redis.lrange(proc, 0, -1)
        for raw in leftovers:
            await redis.lpush(queue, raw)
            await redis.lrem(proc, 1, raw)
    return len(leftovers)
