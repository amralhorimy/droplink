from app.modules.links.errors import LinkExpired, PasswordRequired
from app.platform.shared.errors import AppError, NotFound, ServiceUnavailable


def test_defaults_come_from_the_class():
    err = NotFound("row 42 missing in files")
    assert err.status_code == 404
    assert err.log_message == "row 42 missing in files"
    assert err.public_message == "Resource not found."  # the client never sees the log message


def test_public_message_can_be_overridden_per_raise():
    err = AppError("db exploded: password=hunter2", public_message="Try again later.")
    assert err.public_message == "Try again later."
    assert "hunter2" not in err.public_message


def test_context_and_headers_are_kept():
    err = ServiceUnavailable("x", headers={"Retry-After": "5"}, operation="files.insert")
    assert err.context == {"operation": "files.insert"}
    assert err.headers["Retry-After"] == "5"


def test_domain_errors_have_stable_codes():
    assert LinkExpired().code == "link_expired" and LinkExpired().status_code == 410
    assert PasswordRequired().status_code == 401
