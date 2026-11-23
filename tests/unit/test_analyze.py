import hashlib
import io

from PIL import Image

from workers.processor.analyze import analyze_file


def test_text_file_hash_and_type(tmp_path):
    path = tmp_path / "a.txt"
    path.write_bytes(b"hello\n" * 1000)
    result = analyze_file(str(path), 64)
    assert result.sha256 == hashlib.sha256(b"hello\n" * 1000).hexdigest()
    assert result.size == 6000 and result.detected_type == "text/plain"
    assert result.thumbnail_png is None


def test_image_gets_a_small_png_thumbnail(tmp_path):
    path = tmp_path / "big.png"
    Image.new("RGB", (800, 600), (200, 30, 30)).save(path)
    result = analyze_file(str(path), 64)
    assert result.detected_type == "image/png"
    thumb = Image.open(io.BytesIO(result.thumbnail_png))
    assert max(thumb.size) <= 64


def test_corrupt_image_does_not_crash(tmp_path):
    path = tmp_path / "broken.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"not really a png")
    result = analyze_file(str(path), 64)
    assert result.detected_type == "image/png" and result.thumbnail_png is None
