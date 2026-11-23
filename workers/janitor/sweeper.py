"""One cleaning pass. Separate from the loop so it can be tested/run on demand."""
import logging
from dataclasses import dataclass
from datetime import timedelta

from app.modules.files.lifecycle import destroy_file
from app.modules.files.repo import FilesRepo
from app.modules.links.repo import LinksRepo
from app.platform.infra import Infra
from app.platform.redis.jobs import enqueue_job
from app.platform.shared.clock import utcnow
from app.platform.shared.errors import AppError

log = logging.getLogger("droplink.janitor")
BATCH = 100


@dataclass
class SweepStats:
    expired_files: int = 0
    stale_uploads: int = 0
    requeued: int = 0
    old_links: int = 0


async def sweep_once(infra: Infra) -> SweepStats:
    s = infra.settings
    files, links = FilesRepo(infra.db), LinksRepo(infra.db)
    now = utcnow()
    stats = SweepStats()

    async def destroy(doc: dict) -> bool:
        try:
            await destroy_file(
                files=files, links=links, storage=infra.storage, redis=infra.redis, doc=doc, retention_hours=s.purge_retention_hours
            )
            return True
        except AppError as exc:  # one broken file must not stop the sweep; we retry next round
            log.warning("could not delete %s: %s", doc["_id"], exc.log_message)
            return False

    for doc in await files.find_expired(now, BATCH):
        stats.expired_files += await destroy(doc)

    cutoff = now - timedelta(seconds=s.pending_upload_ttl_seconds)
    for doc in await files.find_stale_pending(cutoff, BATCH):
        stats.stale_uploads += await destroy(doc)

    # Upload finished but the job never reached the queue (Redis blip)? Queue it again.
    stuck_cutoff = now - timedelta(seconds=s.stuck_upload_seconds)
    for doc in await files.find_stuck_uploaded(stuck_cutoff, BATCH):
        await enqueue_job(infra.redis, s.job_queue, {"file_id": doc["_id"], "attempt": 0})
        stats.requeued += 1

    # Expired links stay a while so people get "expired" instead of "not found".
    stats.old_links = await links.delete_expired_before(now - timedelta(hours=24))
    return stats
