from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.deps import Deps, ManageToken

router = APIRouter(prefix="/v1/files", tags=["events"])


@router.get("/{file_id}/events", summary="Live status (Server-Sent Events) until the file is ready")
async def file_events(file_id: str, request: Request, token: ManageToken, c: Deps) -> StreamingResponse:
    # Errors (bad token, redis down) are raised HERE, before streaming starts,
    # so the normal JSON error handling still works.
    stream = await c.events.open(file_id, token)
    return StreamingResponse(
        stream.iterate(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
