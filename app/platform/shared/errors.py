"""The error vocabulary of the whole application.

Two audiences, two messages:
  * `log_message` + `context`  -> OUR side (logs). May contain internals.
  * `public_message` + `code`  -> the CLIENT. Safe, stable, never leaks internals.

Raise a subclass anywhere; `handlers.py` turns it into a log line and a JSON response.
"""
from typing import Any


class AppError(Exception):
    status_code: int = 500
    code: str = "internal_error"
    public_message: str = "Something went wrong on our side."

    def __init__(
        self,
        log_message: str | None = None,
        *,
        public_message: str | None = None,
        headers: dict[str, str] | None = None,
        **context: Any,
    ) -> None:
        super().__init__(log_message or self.public_message)
        self.log_message = log_message or self.public_message
        if public_message is not None:
            self.public_message = public_message
        self.headers = headers or {}
        self.context = context


class BadRequest(AppError):
    status_code = 400
    code = "bad_request"
    public_message = "The request is not valid."


class Unauthorized(AppError):
    status_code = 401
    code = "unauthorized"
    public_message = "Authentication is required."


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"
    public_message = "You are not allowed to do this."


class NotFound(AppError):
    status_code = 404
    code = "not_found"
    public_message = "Resource not found."


class Conflict(AppError):
    status_code = 409
    code = "conflict"
    public_message = "The request conflicts with the current state."


class Gone(AppError):
    status_code = 410
    code = "gone"
    public_message = "This resource is no longer available."


class PayloadTooLarge(AppError):
    status_code = 413
    code = "payload_too_large"
    public_message = "The payload is too large."


class TooManyRequests(AppError):
    status_code = 429
    code = "too_many_requests"
    public_message = "Too many requests. Please slow down."


class ServiceUnavailable(AppError):
    status_code = 503
    code = "service_unavailable"
    public_message = "The service is temporarily unavailable. Please try again shortly."
