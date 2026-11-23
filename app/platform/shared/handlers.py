"""Central error handling: ONE place decides what we log and what the client sees."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.platform.shared.errors import AppError

log = logging.getLogger("droplink.errors")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _envelope(code: str, message: str, request_id: str, details: list | None = None) -> dict:
    body: dict = {"error": {"code": code, "message": message, "request_id": request_id}}
    if details:
        body["error"]["details"] = details
    return body


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        rid = _request_id(request)
        # --- path 1: OUR side (logs) -------------------------------------------------
        ctx = {"code": exc.code, "status": exc.status_code, "path": request.url.path, **exc.context}
        if exc.status_code >= 500:
            log.error(exc.log_message, extra={"ctx": ctx}, exc_info=(type(exc), exc, exc.__traceback__))
        else:
            log.warning(exc.log_message, extra={"ctx": ctx})
        # --- path 2: the CLIENT (safe JSON) ------------------------------------------
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.public_message, rid),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(p) for p in err["loc"] if p not in ("body", "query", "path")), "message": err["msg"]}
            for err in exc.errors()
        ]
        log.info("validation failed", extra={"ctx": {"path": request.url.path, "fields": [d["field"] for d in details]}})
        return JSONResponse(
            status_code=422,
            content=_envelope("validation_error", "Some fields are invalid.", _request_id(request), details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(f"http_{exc.status_code}", message, _request_id(request)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        log.error(
            "unhandled exception",
            extra={"ctx": {"path": request.url.path, "type": type(exc).__name__}},
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return JSONResponse(
            status_code=500,
            content=_envelope("internal_error", AppError.public_message, _request_id(request)),
        )
