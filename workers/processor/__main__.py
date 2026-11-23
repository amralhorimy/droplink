"""Processor worker:  python -m workers.processor

Loop: take a job from the Redis queue -> process -> ack.
Failures are retried with a growing delay, then the file is marked 'failed'.
"""
import asyncio
import json
import logging

from app.modules.files.repo import FilesRepo
from app.platform.infra import Infra
from app.platform.redis.jobs import ack_job, enqueue_job, fetch_job, recover_jobs
from app.platform.shared.config import get_settings
from app.platform.shared.errors import AppError
from workers.processor.handler import mark_failed, process_file
from workers.runtime import bootstrap

log = logging.getLogger("droplink.processor")


async def main() -> None:
    stop = bootstrap()
    s = get_settings()
    infra = await Infra.connect(s)
    repo = FilesRepo(infra.db)

    recovered = await recover_jobs(infra.redis, s.job_queue, s.worker_id)
    log.info("processor %s started (recovered %d unfinished jobs)", s.worker_id, recovered)

    try:
        while not stop.is_set():
            try:
                raw = await fetch_job(infra.redis, s.job_queue, s.worker_id, timeout=5)
            except AppError as exc:
                log.error("queue unavailable: %s", exc.log_message)
                await asyncio.sleep(2)
                continue
            if raw is None:
                continue

            job = json.loads(raw)
            file_id, attempt = job["file_id"], job.get("attempt", 0)
            try:
                await process_file(infra, repo, file_id)
            except Exception as exc:  # noqa: BLE001 - a worker must survive any single bad job
                log.exception("job failed for %s (attempt %d)", file_id, attempt + 1)
                if attempt + 1 < s.processor_max_attempts:
                    await asyncio.sleep(min(2**attempt, 10))
                    await enqueue_job(infra.redis, s.job_queue, {"file_id": file_id, "attempt": attempt + 1})
                else:
                    await mark_failed(infra, repo, file_id, f"{type(exc).__name__}: {exc}")
            finally:
                await ack_job(infra.redis, s.job_queue, s.worker_id, raw)
    finally:
        await infra.close()
        log.info("processor stopped")


if __name__ == "__main__":
    asyncio.run(main())
