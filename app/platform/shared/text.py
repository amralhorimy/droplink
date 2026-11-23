"""Pure text helpers: filename hygiene and a safe Content-Disposition header."""
import re
import unicodedata
from urllib.parse import quote

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_filename(name: str, max_len: int = 255) -> str:
    """Keep only the last path component, drop control characters, cap the length."""
    name = name.replace("\\", "/").split("/")[-1]
    name = unicodedata.normalize("NFC", _CONTROL.sub("", name)).strip()
    if name in ("", ".", ".."):
        return "file"
    if len(name) > max_len:
        stem, dot, ext = name.rpartition(".")
        if dot and 0 < len(ext) <= 16:
            name = stem[: max_len - len(ext) - 1] + "." + ext
        else:
            name = name[:max_len]
    return name


def content_disposition(filename: str) -> str:
    """ASCII fallback + RFC 5987 UTF-8 name, so Arabic (or any) filenames download correctly."""
    ascii_name = re.sub(r"[^A-Za-z0-9._ -]", "_", filename)
    if not re.search(r"[A-Za-z0-9]", ascii_name):
        ascii_name = "download"
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename, safe='')}"
