"""Everything that talks to the outside world, created once and shared.

The API and both workers call `Infra.connect(settings)`: one codebase, one image,
three roles. Services receive pieces of Infra through their constructors.
"""
from dataclasses import dataclass

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.platform.minio.client import Storage
from app.platform.mongo.client import create_mongo
from app.platform.mongo.indexes import ensure_indexes
from app.platform.redis.client import create_redis
from app.platform.redis.errors import translate_redis_errors
from app.platform.redis.ratelimit import RateLimiter
from app.platform.redis.scripts import Scripts
from app.platform.shared.config import Settings
from app.platform.shared.retry import retry_async


@dataclass
class Infra:
    settings: Settings
    mongo_client: AsyncIOMotorClient
    db: AsyncIOMotorDatabase
    redis: Redis
    scripts: Scripts
    limiter: RateLimiter
    storage: Storage

    @classmethod
    async def connect(cls, settings: Settings) -> "Infra":
        mongo_client = create_mongo(settings)
        redis = create_redis(settings)
        scripts = Scripts(redis)
        infra = cls(
            settings=settings,
            mongo_client=mongo_client,
            db=mongo_client[settings.mongo_db],
            redis=redis,
            scripts=scripts,
            limiter=RateLimiter(scripts),
            storage=Storage(settings),
        )
        await retry_async(infra._bootstrap, attempts=30, delay=2.0, what="infrastructure")
        return infra

    async def _bootstrap(self) -> None:
        await ensure_indexes(self.db)
        with translate_redis_errors("ping"):
            await self.redis.ping()
        await self.storage.ensure_bucket()

    async def close(self) -> None:
        self.mongo_client.close()
        await self.redis.aclose()
