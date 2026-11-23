import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.container import build_container
from app.modules.downloads.routes import router as downloads_router
from app.modules.events.routes import router as events_router
from app.modules.files.routes import router as files_router
from app.modules.health.routes import router as health_router
from app.modules.links.routes import router as links_router
from app.platform.infra import Infra
from app.platform.shared.config import get_settings
from app.platform.shared.handlers import register_error_handlers
from app.platform.shared.logging import setup_logging
from app.platform.shared.middleware import RequestContextMiddleware

log = logging.getLogger("droplink.api")

DESCRIPTION = """
**DropLink** - temporary, secure file sharing. A learning-friendly FastAPI backend.

Flow: `POST /v1/files` -> upload to the signed form -> `POST /v1/files/{id}/complete`
-> watch `GET /v1/files/{id}/events` -> `POST /v1/files/{id}/links` -> share `/d/{slug}`.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    infra = await Infra.connect(settings)
    app.state.container = build_container(infra)
    log.info("api started (env=%s)", settings.env)
    try:
        yield
    finally:
        await infra.close()
        log.info("api stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_json)
    app = FastAPI(
        title="DropLink",
        version="1.0.0",
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url=None if settings.env == "prod" else "/docs",
        redoc_url=None,
        openapi_url=None if settings.env == "prod" else "/openapi.json",
    )
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)
    for router in (health_router, files_router, links_router, events_router, downloads_router):
        app.include_router(router)
    return app


app = create_app()
