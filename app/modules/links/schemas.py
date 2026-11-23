from datetime import datetime

from pydantic import BaseModel, Field


class CreateLinkRequest(BaseModel):
    expires_in_seconds: int = Field(default=3600, ge=60, le=60 * 60 * 24 * 30)
    max_downloads: int = Field(default=0, ge=0, le=10_000, description="0 = unlimited. 1 = 'burn after reading'.")
    password: str | None = Field(default=None, min_length=4, max_length=128)


class LinkCreated(BaseModel):
    slug: str
    url: str
    expires_at: datetime
    max_downloads: int
    password_protected: bool


class LinkView(BaseModel):
    slug: str
    expires_at: datetime
    max_downloads: int
    downloads: int
    password_protected: bool


class LinkInfo(BaseModel):
    """Public information shown on the 'download page'. Never includes secrets."""

    slug: str
    filename: str
    size: int | None
    expires_at: datetime
    password_required: bool
    downloads_remaining: int | None
    ready: bool
