"""Security helpers built only on the standard library (no extra dependencies)."""
import base64
import hashlib
import hmac
import os
import secrets
import uuid

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def new_id() -> str:
    return uuid.uuid4().hex


def new_token() -> str:
    """Secret handed to the uploader once. We only ever store its hash."""
    return secrets.token_urlsafe(24)


def new_slug() -> str:
    """Short public id used in download links (8 URL-safe chars)."""
    return secrets.token_urlsafe(6)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token(token: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_token(token), hashed)


def hash_password(password: str) -> str:
    """scrypt is CPU-heavy on purpose: call it through asyncio.to_thread in async code."""
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32)
    b64 = lambda raw: base64.b64encode(raw).decode()  # noqa: E731
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, digest_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)
