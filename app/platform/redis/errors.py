from contextlib import contextmanager

from redis.exceptions import RedisError

from app.platform.shared.errors import AppError, ServiceUnavailable


class RedisUnavailable(ServiceUnavailable):
    code = "cache_unavailable"


@contextmanager
def translate_redis_errors(operation: str):
    try:
        yield
    except AppError:
        raise
    except RedisError as exc:
        raise RedisUnavailable(
            f"redis failure during {operation}: {type(exc).__name__}: {exc}", operation=operation
        ) from exc
