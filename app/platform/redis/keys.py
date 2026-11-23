"""Every Redis key name in one file, so nothing is a magic string elsewhere."""

PREFIX = "droplink"


def download_counter(slug: str) -> str:
    return f"{PREFIX}:dl:{slug}"


def rate_limit(scope: str, ident: str) -> str:
    return f"{PREFIX}:rl:{scope}:{ident}"


def events_channel(file_id: str) -> str:
    return f"{PREFIX}:events:{file_id}"


def processing_list(queue: str, worker_id: str) -> str:
    return f"{queue}:processing:{worker_id}"


def janitor_lock() -> str:
    return f"{PREFIX}:lock:janitor"
