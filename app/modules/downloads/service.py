"""The hot path: validate -> rate limit -> check password -> atomically claim -> redirect."""
import asyncio
import logging

from app.modules.files import domain
from app.modules.files.repo import FilesRepo
from app.modules.links import policy
from app.modules.links.errors import (
    PROBLEMS,
    FileNotReady,
    FileUnavailable,
    LinkNotFound,
    LinkExhausted,
    PasswordRequired,
    WrongPassword,
)
from app.modules.links.repo import LinksRepo
from app.platform.minio.client import Storage
from app.platform.redis import keys
from app.platform.redis.errors import translate_redis_errors
from app.platform.redis.ratelimit import RateLimiter
from app.platform.redis.scripts import Scripts
from app.platform.shared.clock import utcnow
from app.platform.shared.config import Settings
from app.platform.shared.errors import AppError
from app.platform.shared.security import verify_password

log = logging.getLogger("droplink.downloads")


class DownloadsService:
    def __init__(
        self, settings: Settings, files: FilesRepo, links: LinksRepo, storage: Storage, scripts: Scripts, limiter: RateLimiter
    ) -> None:
        self._s = settings
        self._files = files
        self._links = links
        self._storage = storage
        self._scripts = scripts
        self._limiter = limiter

    async def resolve(self, slug: str, *, password: str | None, client_ip: str) -> str:
        """Returns a short-lived signed URL, or raises an AppError explaining why not."""
        await self._limiter.hit("download", client_ip, limit=self._s.rate_limit_download_per_minute, window_seconds=60)

        link = await self._links.get(slug)
        if link is None:
            raise LinkNotFound(f"link {slug} not found", slug=slug)
        now = utcnow()
        if problem := policy.link_problem(link, now):
            raise PROBLEMS[problem](f"link {slug} is {problem}", slug=slug)

        if link["password_hash"]:
            await self._limiter.hit(
                "password", f"{slug}:{client_ip}", limit=self._s.password_attempts_per_10_min, window_seconds=600
            )
            if not password:
                raise PasswordRequired(f"no password supplied for {slug}", slug=slug)
            ok = await asyncio.to_thread(verify_password, password, link["password_hash"])
            if not ok:
                raise WrongPassword(f"wrong password for {slug} from {client_ip}", slug=slug)

        file = await self._files.get(link["file_id"])
        if file is None or file["status"] in (domain.DELETED, domain.FAILED):
            raise FileUnavailable(f"file behind {slug} unavailable", slug=slug)
        if file["status"] != domain.READY:
            raise FileNotReady(f"file {file['_id']} status={file['status']}", slug=slug)

        # The atomic step: only this many callers can ever pass, however many arrive at once.
        ttl = max(1, int((link["expires_at"] - now).total_seconds())) + 3600
        with translate_redis_errors("downloads.claim"):
            claimed = await self._scripts.claim_download(
                keys=[keys.download_counter(slug)],
                args=[link["max_downloads"], ttl, link.get("downloads", 0)],
            )
        if claimed == -1:
            raise LinkExhausted(f"link {slug} exhausted (atomic claim refused)", slug=slug)

        try:  # durable copy of the count; Redis stays the source of truth on the hot path
            await self._links.increment_downloads(slug)
        except AppError as exc:
            log.warning("could not persist download count for %s: %s", slug, exc.log_message)

        return await self._storage.presign_get(
            file["object_key"], ttl_seconds=self._s.download_url_ttl_seconds, filename=file["filename"]
        )
