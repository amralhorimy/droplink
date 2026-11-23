"""CPU-bound work for one downloaded file. Runs in a thread (see handler.py)."""
import hashlib
import io
from dataclasses import dataclass

from PIL import Image

from workers.processor.sniff import IMAGE_TYPES, sniff_type

Image.MAX_IMAGE_PIXELS = 50_000_000  # refuse "decompression bombs"
HEAD_BYTES = 4096


@dataclass
class Analysis:
    sha256: str
    size: int
    detected_type: str
    thumbnail_png: bytes | None


def analyze_file(path: str, thumbnail_px: int) -> Analysis:
    digest = hashlib.sha256()
    size = 0
    head = b""
    with open(path, "rb") as fh:
        while chunk := fh.read(1024 * 1024):  # constant memory, whatever the file size
            if not head:
                head = chunk[:HEAD_BYTES]
            digest.update(chunk)
            size += len(chunk)

    detected = sniff_type(head)
    thumb = _make_thumbnail(path, thumbnail_px) if detected in IMAGE_TYPES else None
    return Analysis(digest.hexdigest(), size, detected, thumb)


def _make_thumbnail(path: str, px: int) -> bytes | None:
    try:
        with Image.open(path) as img:
            img.thumbnail((px, px))
            out = io.BytesIO()
            img.convert("RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB").save(out, format="PNG")
            return out.getvalue()
    except Exception:  # a corrupt image must not fail the whole file
        return None
