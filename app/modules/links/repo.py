from datetime import datetime

from app.platform.mongo.errors import translate_mongo_errors


class LinksRepo:
    def __init__(self, db) -> None:
        self._col = db["links"]

    async def insert(self, doc: dict) -> None:
        with translate_mongo_errors("links.insert"):
            await self._col.insert_one(doc)

    async def get(self, slug: str) -> dict | None:
        with translate_mongo_errors("links.get"):
            return await self._col.find_one({"_id": slug})

    async def list_for_file(self, file_id: str) -> list[dict]:
        with translate_mongo_errors("links.list"):
            return await self._col.find({"file_id": file_id}).sort("created_at", -1).to_list(length=200)

    async def increment_downloads(self, slug: str) -> None:
        with translate_mongo_errors("links.increment"):
            await self._col.update_one({"_id": slug}, {"$inc": {"downloads": 1}})

    async def delete(self, slug: str) -> bool:
        with translate_mongo_errors("links.delete"):
            result = await self._col.delete_one({"_id": slug})
            return result.deleted_count == 1

    async def delete_for_file(self, file_id: str) -> int:
        with translate_mongo_errors("links.delete_for_file"):
            result = await self._col.delete_many({"file_id": file_id})
            return result.deleted_count

    async def delete_expired_before(self, cutoff: datetime) -> int:
        with translate_mongo_errors("links.delete_expired"):
            result = await self._col.delete_many({"expires_at": {"$lte": cutoff}})
            return result.deleted_count
