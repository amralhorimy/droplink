from typing import Annotated

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import RedirectResponse

from app.deps import Deps, client_ip

router = APIRouter(tags=["downloads"])


@router.get("/d/{slug}", status_code=302, summary="Download: redirects to a 60-second signed URL")
async def download(
    slug: str,
    request: Request,
    c: Deps,
    password: Annotated[str | None, Query(max_length=128)] = None,
    x_link_password: Annotated[str | None, Header()] = None,
) -> RedirectResponse:
    url = await c.downloads.resolve(slug, password=x_link_password or password, client_ip=client_ip(request))
    return RedirectResponse(url, status_code=302, headers={"Cache-Control": "no-store"})
