"""Data access only. No business rules here, just Mongo."""
from datetime import datetime
from typing import Iterable

from pymongo import ReturnDocument

from app.platform.mongo.errors import translate_mongo_errors
from app.modules.files import domain
from app.platform.shared.clock import utcnow


class FilesRepo:
    def __init__(self, db) -> None:
        self._col = db["files"]

    async def insert(self, doc: dict) -> None:
        with translate_mongo_errors("files.insert"):
            await self._col.insert_one(doc)

    async def get(self, file_id: str) -> dict | None:
        with translate_mongo_errors("files.get"):
            return await self._col.find_one({"_id": file_id})

    async def transition(self, file_id: str, allowed_from: Iterable[str], to: str, **fields) -> dict | None:
        """Atomic compare-and-set: moves the status ONLY if it is currently in `allowed_from`.

        Returns the updated document, or None when someone else got there first.
        This is what makes double "complete" calls or duplicate jobs harmless.
        """
        with translate_mongo_errors("files.transition"):
            return await self._col.find_one_and_update(
                {"_id": file_id, "status": {"$in": list(allowed_from)}},
                {"$set": {"status": to, **fields}},
                return_document=ReturnDocument.AFTER,
            )

    async def mark_deleted(self, file_id: str, purge_at: datetime) -> None:
        with translate_mongo_errors("files.mark_deleted"):
            await self._col.update_one(
                {"_id": file_id},
                {
                    "$set": {"status": domain.DELETED, "deleted_at": utcnow(), "purge_at": purge_at},
                    "$unset": {"manage_token_hash": ""},
                },
            )

    # ---- queries used by the janitor ------------------------------------------------
    async def find_expired(self, now: datetime, limit: int) -> list[dict]:
        query = {"status": {"$ne": domain.DELETED}, "expires_at": {"$lte": now}}
        with translate_mongo_errors("files.find_expired"):
            return await self._col.find(query).limit(limit).to_list(length=limit)

    async def find_stale_pending(self, cutoff: datetime, limit: int) -> list[dict]:
        query = {"status": domain.PENDING, "created_at": {"$lte": cutoff}}
        with translate_mongo_errors("files.find_stale_pending"):
            return await self._col.find(query).limit(limit).to_list(length=limit)

    async def find_stuck_uploaded(self, cutoff: datetime, limit: int) -> list[dict]:
        query = {"status": domain.UPLOADED, "uploaded_at": {"$lte": cutoff}}
        with translate_mongo_errors("files.find_stuck_uploaded"):
            return await self._col.find(query).limit(limit).to_list(length=limit)
