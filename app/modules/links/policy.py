"""Pure rules: is this link still usable? No I/O, so the tests are trivial."""
from datetime import datetime


def link_problem(link: dict, now: datetime) -> str | None:
    """Return None when the link is fine, otherwise the reason: revoked | expired | exhausted."""
    if link.get("revoked"):
        return "revoked"
    if link["expires_at"] <= now:
        return "expired"
    maximum = link.get("max_downloads", 0)
    if maximum and link.get("downloads", 0) >= maximum:
        return "exhausted"
    return None


def downloads_remaining(link: dict) -> int | None:
    maximum = link.get("max_downloads", 0)
    if not maximum:
        return None  # unlimited
    return max(0, maximum - link.get("downloads", 0))
