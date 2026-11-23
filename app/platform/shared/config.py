"""All configuration lives here and comes from environment variables.

Every variable is prefixed with DROPLINK_ (e.g. DROPLINK_MONGO_URL).
Defaults are safe for local development with docker compose, never for production.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DROPLINK_", extra="ignore")

    # --- runtime ---
    env: str = "dev"  # dev | prod  (prod hides /docs)
    log_level: str = "INFO"
    log_json: bool = False
    public_base_url: str = "http://localhost:8080"

    # --- mongo ---
    mongo_url: str = "mongodb://mongo:27017"
    mongo_db: str = "droplink"

    # --- redis ---
    redis_url: str = "redis://redis:6379/0"
    job_queue: str = "droplink:jobs:process"

    # --- minio / s3 ---
    minio_endpoint: str = "minio:9000"  # what the server uses (inside docker network)
    minio_secure: bool = False
    minio_public_endpoint: str = "localhost:9000"  # what browsers/clients use in signed URLs
    minio_public_secure: bool = False
    minio_access_key: str = "droplink"
    minio_secret_key: str = "droplink-dev-secret"
    minio_bucket: str = "droplink"
    minio_region: str = "us-east-1"

    # --- business rules ---
    max_file_size_mb: int = 100
    file_ttl_hours: int = 168  # a file lives at most 7 days, whatever its links say
    upload_url_ttl_seconds: int = 900
    download_url_ttl_seconds: int = 60
    pending_upload_ttl_seconds: int = 3600
    purge_retention_hours: int = 24  # deleted file records are kept this long, then Mongo TTL removes them

    # --- abuse protection ---
    rate_limit_create_per_minute: int = 20
    rate_limit_download_per_minute: int = 30
    password_attempts_per_10_min: int = 10

    # --- workers ---
    worker_id: str = "worker-1"
    processor_max_attempts: int = 3
    thumbnail_max_px: int = 256
    janitor_interval_seconds: int = 30
    stuck_upload_seconds: int = 120


@lru_cache
def get_settings() -> Settings:
    return Settings()
