"""Composition root: the ONE place where classes are wired together."""
from dataclasses import dataclass

from app.modules.downloads.service import DownloadsService
from app.modules.events.service import EventsService
from app.modules.files.repo import FilesRepo
from app.modules.files.service import FilesService
from app.modules.links.repo import LinksRepo
from app.modules.links.service import LinksService
from app.platform.infra import Infra


@dataclass
class Container:
    infra: Infra
    files: FilesService
    links: LinksService
    downloads: DownloadsService
    events: EventsService


def build_container(infra: Infra) -> Container:
    files_repo = FilesRepo(infra.db)
    links_repo = LinksRepo(infra.db)
    files = FilesService(infra.settings, files_repo, links_repo, infra.storage, infra.redis)
    return Container(
        infra=infra,
        files=files,
        links=LinksService(infra.settings, links_repo, files),
        downloads=DownloadsService(
            infra.settings, files_repo, links_repo, infra.storage, infra.scripts, infra.limiter
        ),
        events=EventsService(infra.redis, files),
    )
