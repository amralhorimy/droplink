from motor.motor_asyncio import AsyncIOMotorClient

from app.platform.shared.config import Settings


def create_mongo(settings: Settings) -> AsyncIOMotorClient:
    # tz_aware=True -> datetimes come back as aware UTC, matching utcnow().
    return AsyncIOMotorClient(
        settings.mongo_url, tz_aware=True, serverSelectionTimeoutMS=3000, appname="droplink"
    )
