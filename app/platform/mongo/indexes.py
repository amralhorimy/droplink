"""Indexes are code too: they are created (idempotently) at every start-up."""
from app.platform.mongo.errors import translate_mongo_errors


async def ensure_indexes(db) -> None:
    with translate_mongo_errors("indexes"):
        # janitor: "which files are past their expiry?"
        await db.files.create_index([("status", 1), ("expires_at", 1)], name="status_expires")
        # janitor: "which uploads were never completed / got stuck?"
        await db.files.create_index([("status", 1), ("created_at", 1)], name="status_created")
        # Mongo itself removes a deleted file's record once `purge_at` passes (TTL index).
        await db.files.create_index("purge_at", expireAfterSeconds=0, name="ttl_purge_at")
        await db.links.create_index("file_id", name="file_id")
        await db.links.create_index("expires_at", name="expires_at")
