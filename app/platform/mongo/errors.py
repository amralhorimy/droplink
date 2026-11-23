"""Mongo-specific failures, translated into our own error vocabulary."""
from contextlib import contextmanager

from pymongo.errors import DuplicateKeyError, PyMongoError

from app.platform.shared.errors import AppError, Conflict, ServiceUnavailable


class MongoUnavailable(ServiceUnavailable):
    code = "database_unavailable"


class MongoConflict(Conflict):
    code = "duplicate_record"
    public_message = "This record already exists."


@contextmanager
def translate_mongo_errors(operation: str):
    """Wrap every driver call: `with translate_mongo_errors("files.insert"): ...`"""
    try:
        yield
    except AppError:
        raise
    except DuplicateKeyError as exc:
        raise MongoConflict(f"duplicate key during {operation}: {exc}", operation=operation) from exc
    except PyMongoError as exc:
        raise MongoUnavailable(
            f"mongo failure during {operation}: {type(exc).__name__}: {exc}", operation=operation
        ) from exc
