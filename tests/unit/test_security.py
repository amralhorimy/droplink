from app.platform.shared.security import (
    hash_password,
    hash_token,
    new_slug,
    new_token,
    verify_password,
    verify_token,
)


def test_token_roundtrip_and_uniqueness():
    token = new_token()
    assert verify_token(token, hash_token(token))
    assert not verify_token(token + "x", hash_token(token))
    assert new_token() != token


def test_slug_is_short_and_url_safe():
    slug = new_slug()
    assert 6 <= len(slug) <= 12
    assert all(c.isalnum() or c in "-_" for c in slug)


def test_password_hash_verifies_and_is_salted():
    stored = hash_password("correct horse")
    assert stored.startswith("scrypt$")
    assert verify_password("correct horse", stored)
    assert not verify_password("wrong", stored)
    assert hash_password("correct horse") != stored  # random salt


def test_malformed_stored_hash_never_verifies():
    assert not verify_password("x", "garbage")
    assert not verify_password("x", "md5$1$2$3$4$5")
