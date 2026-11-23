"""Detect a file's real type from its first bytes (never trust the declared Content-Type). Pure."""

_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"%PDF-", "application/pdf"),
    (b"PK\x03\x04", "application/zip"),
    (b"\x1f\x8b", "application/gzip"),
]
IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}


def sniff_type(head: bytes) -> str:
    for magic, mime in _SIGNATURES:
        if head.startswith(magic):
            return mime
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head and b"\x00" not in head:
        try:
            head.decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            # the 4 KB cut may split a multi-byte character; retry without the last 3 bytes
            try:
                head[:-3].decode("utf-8")
                return "text/plain"
            except UnicodeDecodeError:
                pass
    return "application/octet-stream"


def type_mismatch(declared: str, detected: str) -> bool:
    """True when the uploader's claim and the real content disagree in an interesting way."""
    declared = declared.split(";")[0].strip().lower()
    if declared in ("", "application/octet-stream") or detected == "application/octet-stream":
        return False  # "unknown" never counts as a lie
    if detected == "text/plain" and declared.startswith("text/"):
        return False  # text/csv, text/markdown ... are all just text
    return declared != detected
