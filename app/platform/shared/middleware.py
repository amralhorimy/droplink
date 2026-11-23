"""Pure-ASGI middleware: request id + access log.

Written as raw ASGI (not BaseHTTPMiddleware) so it never interferes with
streaming responses such as Server-Sent Events.
"""
import logging
import re
import time
import uuid

from app.platform.shared.logging import request_id_var

log = logging.getLogger("droplink.access")
_SAFE_ID = re.compile(r"[^A-Za-z0-9_-]")


class RequestContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope["headers"]).get(b"x-request-id", b"").decode("latin-1")
        request_id = _SAFE_ID.sub("", incoming)[:64] or uuid.uuid4().hex[:16]
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status = {"code": 500}

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            log.info(
                "%s %s -> %s",
                scope["method"],
                scope["path"],
                status["code"],
                extra={"ctx": {"ms": round(elapsed_ms, 1)}},
            )
            request_id_var.reset(token)
