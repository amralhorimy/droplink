import asyncio
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.deps import Deps

router = APIRouter(tags=["health"])
log = logging.getLogger("droplink.health")


@router.get("/health/live", summary="Process is up (used by docker healthcheck)")
async def live() -> dict:
    return {"status": "ok"}


@router.get("/health/ready", summary="Dependencies are reachable")
async def ready(c: Deps) -> JSONResponse:
    results: dict[str, str] = {}

    async def check(name: str, awaitable) -> None:
        try:
            await asyncio.wait_for(awaitable, timeout=3)
            results[name] = "ok"
        except Exception as exc:  # health checks must never raise
            results[name] = "down"
            log.warning("readiness: %s is down (%s)", name, type(exc).__name__)

    await asyncio.gather(
        check("mongo", c.infra.db.command("ping")),
        check("redis", c.infra.redis.ping()),
        check("storage", c.infra.storage.ping()),
    )
    healthy = all(v == "ok" for v in results.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ready" if healthy else "degraded", "checks": results},
    )
