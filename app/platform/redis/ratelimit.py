from app.platform.redis import keys
from app.platform.redis.errors import translate_redis_errors
from app.platform.redis.scripts import Scripts
from app.platform.shared.errors import TooManyRequests


class RateLimiter:
    """Fixed-window limiter. Simple, cheap, good enough to stop casual abuse."""

    def __init__(self, scripts: Scripts) -> None:
        self._scripts = scripts

    async def hit(self, scope: str, ident: str, *, limit: int, window_seconds: int) -> None:
        key = keys.rate_limit(scope, ident)
        with translate_redis_errors(f"ratelimit.{scope}"):
            count = await self._scripts.rate_hit(keys=[key], args=[window_seconds])
        if count > limit:
            raise TooManyRequests(
                f"rate limit '{scope}' exceeded by {ident} ({count}>{limit})",
                headers={"Retry-After": str(window_seconds)},
                scope=scope,
            )
