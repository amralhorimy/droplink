from app.platform.shared.errors import Conflict, Forbidden, NotFound, PayloadTooLarge


class FileNotFound(NotFound):
    code = "file_not_found"
    public_message = "File not found."


class InvalidManageToken(Forbidden):
    code = "invalid_manage_token"
    public_message = "The management token is missing or wrong."


class FileTooLarge(PayloadTooLarge):
    code = "file_too_large"


class UploadMissing(Conflict):
    code = "upload_missing"
    public_message = "No uploaded data was found for this file. Upload it first, then call complete."


class InvalidFileState(Conflict):
    code = "invalid_file_state"
    public_message = "The file is not in a state that allows this action."


class NoThumbnail(NotFound):
    code = "no_thumbnail"
    public_message = "This file has no thumbnail."
