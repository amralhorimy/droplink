"""FastAPI dependencies shared by all routers."""
from typing import Annotated

from fastapi import Depends, Header, Request

from app.container import Container
from app.platform.shared.errors import Unauthorized


def get_container(request: Request) -> Container:
    return request.app.state.container


Deps = Annotated[Container, Depends(get_container)]


def client_ip(request: Request) -> str:
    # uvicorn runs with --proxy-headers behind nginx, so this is the real client address.
    return request.client.host if request.client else "unknown"


def manage_token(x_manage_token: Annotated[str | None, Header()] = None) -> str:
    if not x_manage_token:
        raise Unauthorized(
            "missing X-Manage-Token header", public_message="Send your management token in the X-Manage-Token header."
        )
    return x_manage_token


ManageToken = Annotated[str, Depends(manage_token)]


def rate_limited(scope: str, setting_name: str):
    """Build a dependency that limits calls per client IP per minute."""

    async def dependency(request: Request, c: Deps) -> None:
        await c.infra.limiter.hit(
            scope, client_ip(request), limit=getattr(c.infra.settings, setting_name), window_seconds=60
        )

    return Depends(dependency)
