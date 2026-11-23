from contextlib import contextmanager

from minio.error import S3Error
from urllib3.exceptions import HTTPError as Urllib3Error

from app.platform.shared.errors import AppError, NotFound, ServiceUnavailable


class StorageUnavailable(ServiceUnavailable):
    code = "storage_unavailable"


class ObjectNotFound(NotFound):
    code = "object_not_found"
    public_message = "The stored object was not found."


_MISSING = {"NoSuchKey", "NoSuchObject"}


@contextmanager
def translate_minio_errors(operation: str):
    try:
        yield
    except AppError:
        raise
    except S3Error as exc:
        if exc.code in _MISSING:
            raise ObjectNotFound(f"{operation}: {exc.code}", operation=operation) from exc
        raise StorageUnavailable(f"minio error during {operation}: {exc.code}: {exc}", operation=operation) from exc
    except (Urllib3Error, OSError) as exc:
        raise StorageUnavailable(
            f"minio unreachable during {operation}: {type(exc).__name__}: {exc}", operation=operation
        ) from exc
