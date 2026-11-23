from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse

from app.deps import Deps, ManageToken, rate_limited
from app.modules.files.schemas import CreateFileRequest, FileCreated, FileView

router = APIRouter(prefix="/v1/files", tags=["files"])


@router.post(
    "",
    status_code=201,
    response_model=FileCreated,
    summary="Step 1 - register a file and get a signed upload form",
    dependencies=[rate_limited("create", "rate_limit_create_per_minute")],
)
async def create_file(body: CreateFileRequest, c: Deps) -> FileCreated:
    return await c.files.create(body)


@router.post(
    "/{file_id}/complete",
    status_code=202,
    response_model=FileView,
    summary="Step 2 - tell us the upload finished; processing starts in the background",
)
async def complete_upload(file_id: str, token: ManageToken, c: Deps) -> FileView:
    return await c.files.complete(file_id, token)


@router.get("/{file_id}", response_model=FileView, summary="Current state of a file")
async def get_file(file_id: str, token: ManageToken, c: Deps) -> FileView:
    return await c.files.get_view(file_id, token)


@router.delete("/{file_id}", status_code=204, summary="Delete the file and all its links now")
async def delete_file(file_id: str, token: ManageToken, c: Deps) -> Response:
    await c.files.remove(file_id, token)
    return Response(status_code=204)


@router.get("/{file_id}/thumbnail", status_code=302, summary="Redirect to the generated thumbnail (images only)")
async def get_thumbnail(file_id: str, token: ManageToken, c: Deps) -> RedirectResponse:
    url = await c.files.thumbnail_url(file_id, token)
    return RedirectResponse(url, status_code=302, headers={"Cache-Control": "no-store"})
