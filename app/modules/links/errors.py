from app.platform.shared.errors import Conflict, Forbidden, Gone, NotFound, Unauthorized


class LinkNotFound(NotFound):
    code = "link_not_found"
    public_message = "Link not found."


class LinkExpired(Gone):
    code = "link_expired"
    public_message = "This link has expired."


class LinkExhausted(Gone):
    code = "link_exhausted"
    public_message = "This link has reached its download limit."


class LinkRevoked(Gone):
    code = "link_revoked"
    public_message = "This link was revoked by its owner."


class PasswordRequired(Unauthorized):
    code = "password_required"
    public_message = "This link is password protected. Send it in the X-Link-Password header or ?password=."


class WrongPassword(Forbidden):
    code = "wrong_password"
    public_message = "Wrong password."


class FileNotReady(Conflict):
    code = "file_not_ready"
    public_message = "The file is still being processed. Try again in a moment."


class FileUnavailable(Conflict):
    code = "file_unavailable"
    public_message = "This file can no longer be shared."


PROBLEMS = {"expired": LinkExpired, "exhausted": LinkExhausted, "revoked": LinkRevoked}
