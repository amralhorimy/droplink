from datetime import datetime, timedelta, timezone

from app.modules.links.policy import downloads_remaining, link_problem

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def link(**over):
    base = {"expires_at": NOW + timedelta(hours=1), "max_downloads": 0, "downloads": 0, "revoked": False}
    return {**base, **over}


def test_fresh_link_is_fine():
    assert link_problem(link(), NOW) is None


def test_expired():
    assert link_problem(link(expires_at=NOW), NOW) == "expired"
    assert link_problem(link(expires_at=NOW - timedelta(seconds=1)), NOW) == "expired"


def test_exhausted_only_when_a_limit_exists():
    assert link_problem(link(max_downloads=3, downloads=3), NOW) == "exhausted"
    assert link_problem(link(max_downloads=3, downloads=2), NOW) is None
    assert link_problem(link(max_downloads=0, downloads=999), NOW) is None  # 0 = unlimited


def test_revoked_wins():
    assert link_problem(link(revoked=True), NOW) == "revoked"


def test_downloads_remaining():
    assert downloads_remaining(link(max_downloads=0)) is None
    assert downloads_remaining(link(max_downloads=5, downloads=2)) == 3
    assert downloads_remaining(link(max_downloads=5, downloads=9)) == 0
