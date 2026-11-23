"""Deleting a file is shared by the API (user asks) and the janitor (time's up)."""
import logging
from datetime import timedelta

from app.modules.files import domain
from app.platform.redis.events import publish_status
from app.platform.shared.clock import utcnow
from app.platform.shared.errors import AppError

log = logging.getLogger("droplink.lifecycle")


def thumbnail_key(file_id: str) -> str:
    return f"thumbs/{file_id}.png"


async def destroy_file(*, files, links, storage, redis, doc: dict, retention_hours: int) -> None:
    """Idempotent: safe to run again if a previous attempt died half-way."""
    keys = [doc["object_key"]]
    if (doc.get("processing") or {}).get("has_thumbnail"):
        keys.append(thumbnail_key(doc["_id"]))
    await storage.remove_many(keys)
    await links.delete_for_file(doc["_id"])
    await files.mark_deleted(doc["_id"], purge_at=utcnow() + timedelta(hours=retention_hours))
    try:
        await publish_status(redis, doc["_id"], domain.DELETED)
    except AppError as exc:  # live notification is a nice-to-have, never a reason to fail
        log.warning("could not publish delete event: %s", exc.log_message)
