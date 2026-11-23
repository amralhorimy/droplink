from workers.processor.sniff import sniff_type, type_mismatch


def test_known_signatures():
    assert sniff_type(b"\x89PNG\r\n\x1a\n....") == "image/png"
    assert sniff_type(b"\xff\xd8\xff\xe0....") == "image/jpeg"
    assert sniff_type(b"GIF89a....") == "image/gif"
    assert sniff_type(b"%PDF-1.7") == "application/pdf"
    assert sniff_type(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"


def test_text_including_arabic():
    assert sniff_type("hello".encode()) == "text/plain"
    assert sniff_type("مرحبا بالعالم".encode("utf-8")) == "text/plain"


def test_split_multibyte_char_at_the_cut_is_still_text():
    data = ("م" * 3000).encode("utf-8")[:4095]  # cut in the middle of a character
    assert sniff_type(data) == "text/plain"


def test_binary_and_empty_fall_back():
    assert sniff_type(b"\x00\x01\x02\x03") == "application/octet-stream"
    assert sniff_type(b"") == "application/octet-stream"


def test_mismatch_logic():
    assert type_mismatch("image/png", "application/pdf")
    assert not type_mismatch("image/png", "image/png")
    assert not type_mismatch("text/csv", "text/plain")
    assert not type_mismatch("application/octet-stream", "image/png")  # unknown is not a lie
    assert not type_mismatch("image/png; charset=binary", "image/png")
