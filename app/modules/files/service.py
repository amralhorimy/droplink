"""Business rules for files. Talks to repo/storage/redis, never to HTTP."""
import logging
from datetime import timedelta

from app.modules.files import domain
from app.modules.files.errors import (
    FileNotFound,
    FileTooLarge,
    InvalidFileState,
    InvalidManageToken,
    NoThumbnail,
    UploadMissing,
)
from app.modules.files.lifecycle import destroy_file, thumbnail_key
from app.modules.files.repo import FilesRepo
from app.modules.files.schemas import CreateFileRequest, FileCreated, FileView, UploadTarget, to_view
from app.modules.links.repo import LinksRepo
from app.platform.minio.client import Storage
from app.platform.minio.errors import ObjectNotFound
from app.platform.redis.events import publish_status
from app.platform.redis.jobs import enqueue_job
from app.platform.shared.clock import utcnow
from app.platform.shared.config import Settings
from app.platform.shared.errors import AppError
from app.platform.shared.security import hash_token, new_id, new_token, verify_token
from app.platform.shared.text import sanitize_filename

log = logging.getLogger("droplink.files")


class FilesService:
    def __init__(self, settings: Settings, repo: FilesRepo, links: LinksRepo, storage: Storage, redis) -> None:
        self._s = settings
        self._repo = repo
        self._links = links
        self._storage = storage
        self._redis = redis

    @property
    def repo(self) -> FilesRepo:
        return self._repo

    # ---- create ---------------------------------------------------------------------
    async def create(self, body: CreateFileRequest) -> FileCreated:
        limit = self._s.max_file_size_mb * 1024 * 1024
        if body.size > limit:
            raise FileTooLarge(
                f"declared size {body.size} exceeds {limit}",
                public_message=f"Files are limited to {self._s.max_file_size_mb} MB.",
            )
        now = utcnow()
        file_id, token = new_id(), new_token()
        doc = {
            "_id": file_id,
            "filename": sanitize_filename(body.filename),
            "content_type": body.content_type,
            "declared_size": body.size,
            "size": None,
            "status": domain.PENDING,
            "object_key": f"files/{file_id}",
            "manage_token_hash": hash_token(token),
            "created_at": now,
            "expires_at": now + timedelta(hours=self._s.file_ttl_hours),
            "processing": None,
        }
        await self._repo.insert(doc)
        url, fields = await self._storage.presign_post(
            doc["object_key"], max_bytes=body.size, ttl_seconds=self._s.upload_url_ttl_seconds
        )
        return FileCreated(
            file_id=file_id,
            manage_token=token,
            upload=UploadTarget(url=url, fields=fields, expires_at=now + timedelta(seconds=self._s.upload_url_ttl_seconds)),
            expires_at=doc["expires_at"],
        )

    # ---- authorization (used by every endpoint that needs the manage token) -----------
    async def get_authorized(self, file_id: str, token: str) -> dict:
        doc = await self._repo.get(file_id)
        if doc is None or doc["status"] == domain.DELETED:
            raise FileNotFound(f"file {file_id} not found", file_id=file_id)
        if not verify_token(token, doc["manage_token_hash"]):
            raise InvalidManageToken(f"bad manage token for file {file_id}", file_id=file_id)
        return doc

    async def get_view(self, file_id: str, token: str) -> FileView:
        return to_view(await self.get_authorized(file_id, token))

    # ---- complete the upload ----------------------------------------------------------
    async def complete(self, file_id: str, token: str) -> FileView:
        doc = await self.get_authorized(file_id, token)
        if doc["status"] != domain.PENDING:
            raise InvalidFileState(f"complete called while status={doc['status']}", file_id=file_id)
        try:
            size = await self._storage.stat_size(doc["object_key"])
        except ObjectNotFound as exc:
            raise UploadMissing(f"no object for file {file_id}", file_id=file_id) from exc

        updated = await self._repo.transition(
            file_id, domain.allowed_from(domain.UPLOADED), domain.UPLOADED, size=size, uploaded_at=utcnow()
        )
        if updated is None:  # a concurrent complete won the race
            raise InvalidFileState("lost the race on complete", file_id=file_id)

        # If this enqueue fails the file stays 'uploaded' and the janitor re-queues it later.
        await enqueue_job(self._redis, self._s.job_queue, {"file_id": file_id, "attempt": 0})
        try:
            await publish_status(self._redis, file_id, domain.UPLOADED)
        except AppError as exc:
            log.warning("could not publish upload event: %s", exc.log_message)
        return to_view(updated)

    # ---- delete / thumbnail --------------------------------------------------------------
    async def remove(self, file_id: str, token: str) -> None:
        doc = await self.get_authorized(file_id, token)
        await destroy_file(
            files=self._repo,
            links=self._links,
            storage=self._storage,
            redis=self._redis,
            doc=doc,
            retention_hours=self._s.purge_retention_hours,
        )

    async def thumbnail_url(self, file_id: str, token: str) -> str:
        doc = await self.get_authorized(file_id, token)
        if not (doc.get("processing") or {}).get("has_thumbnail"):
            raise NoThumbnail(f"file {file_id} has no thumbnail", file_id=file_id)
        return await self._storage.presign_get(
            thumbnail_key(file_id), ttl_seconds=self._s.download_url_ttl_seconds, filename="thumbnail.png"
        )
