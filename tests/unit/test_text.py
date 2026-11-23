from app.platform.shared.text import content_disposition, sanitize_filename


def test_path_components_are_dropped():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("C:\\Users\\me\\a.txt") == "a.txt"


def test_control_chars_and_empty_names():
    assert sanitize_filename("a\x00b\n.txt") == "ab.txt"
    assert sanitize_filename("..") == "file"
    assert sanitize_filename("   ") == "file"


def test_long_names_keep_their_extension():
    name = sanitize_filename("x" * 400 + ".pdf")
    assert len(name) == 255 and name.endswith(".pdf")


def test_arabic_filename_is_preserved():
    assert sanitize_filename("تقرير.pdf") == "تقرير.pdf"


def test_content_disposition_has_ascii_fallback_and_utf8_name():
    header = content_disposition("تقرير.pdf")
    assert header.startswith("attachment;")
    assert "filename*=UTF-8''" in header
    assert 'filename="' in header
    assert all(ord(c) < 128 for c in header)  # header itself must be pure ASCII


def test_quotes_cannot_break_the_header():
    header = content_disposition('a"b.txt')
    assert header.count('"') == 2
