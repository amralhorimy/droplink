from fastapi import APIRouter, Response

from app.deps import Deps, ManageToken
from app.modules.links.schemas import CreateLinkRequest, LinkCreated, LinkInfo, LinkView

router = APIRouter(prefix="/v1", tags=["links"])


@router.post(
    "/files/{file_id}/links",
    status_code=201,
    response_model=LinkCreated,
    summary="Step 3 - create a share link (expiry, download limit, optional password)",
)
async def create_link(file_id: str, body: CreateLinkRequest, token: ManageToken, c: Deps) -> LinkCreated:
    return await c.links.create(file_id, token, body)


@router.get("/files/{file_id}/links", response_model=list[LinkView], summary="List the links of a file")
async def list_links(file_id: str, token: ManageToken, c: Deps) -> list[LinkView]:
    return await c.links.list_for_file(file_id, token)


@router.get("/links/{slug}", response_model=LinkInfo, summary="Public info for a download page")
async def link_info(slug: str, c: Deps) -> LinkInfo:
    return await c.links.info(slug)


@router.delete("/links/{slug}", status_code=204, summary="Revoke a link")
async def revoke_link(slug: str, token: ManageToken, c: Deps) -> Response:
    await c.links.revoke(slug, token)
    return Response(status_code=204)
