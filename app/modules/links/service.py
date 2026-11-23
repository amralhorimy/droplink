import asyncio
import logging
from datetime import timedelta

from app.modules.files import domain
from app.modules.files.errors import FileNotFound
from app.modules.files.service import FilesService
from app.modules.links import policy
from app.modules.links.errors import PROBLEMS, FileUnavailable, LinkNotFound
from app.modules.links.repo import LinksRepo
from app.modules.links.schemas import CreateLinkRequest, LinkCreated, LinkInfo, LinkView
from app.platform.mongo.errors import MongoConflict
from app.platform.shared.clock import utcnow
from app.platform.shared.config import Settings
from app.platform.shared.security import hash_password, new_slug

log = logging.getLogger("droplink.links")


class LinksService:
    def __init__(self, settings: Settings, repo: LinksRepo, files: FilesService) -> None:
        self._s = settings
        self._repo = repo
        self._files = files

    async def create(self, file_id: str, token: str, body: CreateLinkRequest) -> LinkCreated:
        file = await self._files.get_authorized(file_id, token)
        if file["status"] in (domain.FAILED, domain.DELETED):
            raise FileUnavailable(f"cannot link file {file_id} in status {file['status']}", file_id=file_id)

        now = utcnow()
        # A link can never outlive its file.
        expires_at = min(now + timedelta(seconds=body.expires_in_seconds), file["expires_at"])
        password_hash = await asyncio.to_thread(hash_password, body.password) if body.password else None

        for _ in range(3):  # slug collisions are astronomically rare, but handle them anyway
            doc = {
                "_id": new_slug(),
                "file_id": file_id,
                "expires_at": expires_at,
                "max_downloads": body.max_downloads,
                "downloads": 0,
                "password_hash": password_hash,
                "revoked": False,
                "created_at": now,
            }
            try:
                await self._repo.insert(doc)
                break
            except MongoConflict:
                continue
        else:
            raise MongoConflict("could not allocate a unique slug after 3 tries")

        return LinkCreated(
            slug=doc["_id"],
            url=f"{self._s.public_base_url}/d/{doc['_id']}",
            expires_at=expires_at,
            max_downloads=body.max_downloads,
            password_protected=password_hash is not None,
        )

    async def list_for_file(self, file_id: str, token: str) -> list[LinkView]:
        await self._files.get_authorized(file_id, token)
        return [
            LinkView(
                slug=d["_id"],
                expires_at=d["expires_at"],
                max_downloads=d["max_downloads"],
                downloads=d["downloads"],
                password_protected=d["password_hash"] is not None,
            )
            for d in await self._repo.list_for_file(file_id)
        ]

    async def info(self, slug: str) -> LinkInfo:
        link = await self._repo.get(slug)
        if link is None:
            raise LinkNotFound(f"link {slug} not found", slug=slug)
        if problem := policy.link_problem(link, utcnow()):
            raise PROBLEMS[problem](f"link {slug} is {problem}", slug=slug)
        file = await self._files.repo.get(link["file_id"])
        if file is None or file["status"] == domain.DELETED:
            raise FileNotFound(f"file behind link {slug} is gone", slug=slug)
        return LinkInfo(
            slug=slug,
            filename=file["filename"],
            size=file.get("size"),
            expires_at=link["expires_at"],
            password_required=link["password_hash"] is not None,
            downloads_remaining=policy.downloads_remaining(link),
            ready=file["status"] == domain.READY,
        )

    async def revoke(self, slug: str, token: str) -> None:
        link = await self._repo.get(slug)
        if link is None:
            raise LinkNotFound(f"link {slug} not found", slug=slug)
        await self._files.get_authorized(link["file_id"], token)  # proves ownership
        await self._repo.delete(slug)
