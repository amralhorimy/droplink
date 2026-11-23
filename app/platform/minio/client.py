"""Async-friendly wrapper around the (blocking) MinIO SDK.

Two SDK clients on purpose:
  * internal : used by our containers (minio:9000 inside the docker network)
  * public   : only used to SIGN urls, with the hostname the end user can reach.
A presigned URL embeds the host in its signature, so it must be signed for the public one.
Both pass `region`, which makes signing fully offline (no network call).
"""
import asyncio
import io
from datetime import timedelta

from minio import Minio
from minio.datatypes import PostPolicy
from minio.error import S3Error

from app.platform.minio.errors import translate_minio_errors
from app.platform.shared.clock import utcnow
from app.platform.shared.config import Settings
from app.platform.shared.text import content_disposition


class Storage:
    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.minio_bucket
        self._public_endpoint = settings.minio_public_endpoint
        self._public_secure = settings.minio_public_secure
        creds = dict(access_key=settings.minio_access_key, secret_key=settings.minio_secret_key, region=settings.minio_region)
        self._internal = Minio(settings.minio_endpoint, secure=settings.minio_secure, **creds)
        self._public = Minio(settings.minio_public_endpoint, secure=settings.minio_public_secure, **creds)

    # ---- bootstrap / health -------------------------------------------------------
    async def ensure_bucket(self) -> None:
        await asyncio.to_thread(self._ensure_bucket)

    def _ensure_bucket(self) -> None:
        with translate_minio_errors("ensure_bucket"):
            if self._internal.bucket_exists(self._bucket):
                return
            try:
                self._internal.make_bucket(self._bucket)
            except S3Error as exc:  # another container created it first: fine
                if exc.code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                    raise

    async def ping(self) -> None:
        def _ping() -> None:
            with translate_minio_errors("ping"):
                self._internal.bucket_exists(self._bucket)

        await asyncio.to_thread(_ping)

    # ---- signed urls (offline computation, no I/O) --------------------------------
    async def presign_post(self, key: str, *, max_bytes: int, ttl_seconds: int) -> tuple[str, dict[str, str]]:
        """Browser/form upload that MinIO itself limits to `max_bytes` (a plain presigned PUT cannot)."""
        return await asyncio.to_thread(self._presign_post, key, max_bytes, ttl_seconds)

    def _presign_post(self, key: str, max_bytes: int, ttl_seconds: int) -> tuple[str, dict[str, str]]:
        with translate_minio_errors("presign_post"):
            policy = PostPolicy(self._bucket, utcnow() + timedelta(seconds=ttl_seconds))
            policy.add_equals_condition("key", key)
            policy.add_content_length_range_condition(1, max_bytes)
            result = self._public.presigned_post_policy(policy)
        if isinstance(result, tuple):  # older SDK versions return (url, fields)
            url, fields = result
        else:
            fields = result
            scheme = "https" if self._public_secure else "http"
            url = f"{scheme}://{self._public_endpoint}/{self._bucket}"
        fields = dict(fields)
        fields["key"] = key
        return url, fields

    async def presign_get(self, key: str, *, ttl_seconds: int, filename: str) -> str:
        def _sign() -> str:
            with translate_minio_errors("presign_get"):
                return self._public.presigned_get_object(
                    self._bucket,
                    key,
                    expires=timedelta(seconds=ttl_seconds),
                    response_headers={
                        "response-content-disposition": content_disposition(filename),
                        "response-content-type": "application/octet-stream",  # always download, never render
                    },
                )

        return await asyncio.to_thread(_sign)

    # ---- object operations ---------------------------------------------------------
    async def stat_size(self, key: str) -> int:
        def _stat() -> int:
            with translate_minio_errors("stat"):
                return self._internal.stat_object(self._bucket, key).size

        return await asyncio.to_thread(_stat)

    async def download_to(self, key: str, path: str) -> None:
        def _download() -> None:
            with translate_minio_errors("download"):
                self._internal.fget_object(self._bucket, key, path)

        await asyncio.to_thread(_download)

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        def _put() -> None:
            with translate_minio_errors("put"):
                self._internal.put_object(self._bucket, key, io.BytesIO(data), length=len(data), content_type=content_type)

        await asyncio.to_thread(_put)

    async def remove_many(self, keys: list[str]) -> None:
        def _remove() -> None:
            with translate_minio_errors("remove"):
                for key in keys:
                    self._internal.remove_object(self._bucket, key)  # no error if already gone

        await asyncio.to_thread(_remove)
