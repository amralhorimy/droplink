"""One place for "now", so every timestamp in the system is timezone-aware UTC."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
