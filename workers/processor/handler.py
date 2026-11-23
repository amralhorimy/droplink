"""Process one job. Idempotent: running it twice gives the same result."""
import asyncio
import logging
import tempfile
from pathlib import Path

from app.modules.files import domain
from app.modules.files.lifecycle import thumbnail_key
from app.modules.files.repo import FilesRepo
from app.platform.infra import Infra
from app.platform.redis.events import publish_status
from app.platform.shared.clock import utcnow
from app.platform.shared.errors import AppError
from workers.processor.analyze import analyze_file
from workers.processor.sniff import type_mismatch

log = logging.getLogger("droplink.processor")


async def _notify(infra: Infra, file_id: str, status: str, **extra) -> None:
    try:
        await publish_status(infra.redis, file_id, status, **extra)
    except AppError as exc:
        log.warning("event not published (%s): %s", status, exc.log_message)


async def process_file(infra: Infra, repo: FilesRepo, file_id: str) -> None:
    s = infra.settings
    doc = await repo.transition(file_id, {domain.UPLOADED, domain.PROCESSING}, domain.PROCESSING, processing_started_at=utcnow())
    if doc is None:
        log.info("skip %s: not waiting for processing (already done or deleted)", file_id)
        return
    await _notify(infra, file_id, domain.PROCESSING)

    with tempfile.TemporaryDirectory(prefix="droplink-") as tmp:
        path = str(Path(tmp) / "blob")
        await infra.storage.download_to(doc["object_key"], path)
        result = await asyncio.to_thread(analyze_file, path, s.thumbnail_max_px)  # keep the event loop free

    if result.thumbnail_png:
        await infra.storage.put_bytes(thumbnail_key(file_id), result.thumbnail_png, "image/png")

    info = {
        "sha256": result.sha256,
        "detected_type": result.detected_type,
        "type_mismatch": type_mismatch(doc["content_type"], result.detected_type),
        "has_thumbnail": result.thumbnail_png is not None,
        "error": None,
    }
    done = await repo.transition(file_id, {domain.PROCESSING}, domain.READY, size=result.size, processing=info, ready_at=utcnow())
    if done is None:
        log.info("file %s changed while processing (deleted?); result dropped", file_id)
        return
    await _notify(infra, file_id, domain.READY, sha256=result.sha256, detected_type=result.detected_type)
    log.info("processed %s: %s %s bytes", file_id, result.detected_type, result.size)


async def mark_failed(infra: Infra, repo: FilesRepo, file_id: str, reason: str) -> None:
    info = {"sha256": None, "detected_type": None, "type_mismatch": False, "has_thumbnail": False, "error": reason[:200]}
    updated = await repo.transition(file_id, {domain.UPLOADED, domain.PROCESSING}, domain.FAILED, processing=info)
    if updated is not None:
        await _notify(infra, file_id, domain.FAILED)
