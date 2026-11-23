from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CreateFileRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255, examples=["report.pdf"])
    size: int = Field(gt=0, description="Exact size in bytes. The upload is capped to it.", examples=[48213])
    content_type: str = Field(default="application/octet-stream", max_length=127)


class UploadTarget(BaseModel):
    url: str
    method: Literal["POST"] = "POST"
    fields: dict[str, str] = Field(description="Send ALL of these as form fields, then the file as the LAST field named 'file'.")
    expires_at: datetime


class FileCreated(BaseModel):
    file_id: str
    manage_token: str = Field(description="Shown ONCE. Send it as the X-Manage-Token header to manage this file.")
    upload: UploadTarget
    expires_at: datetime


class ProcessingInfo(BaseModel):
    sha256: str | None = None
    detected_type: str | None = None
    type_mismatch: bool = False
    has_thumbnail: bool = False
    error: str | None = None


class FileView(BaseModel):
    file_id: str
    filename: str
    content_type: str
    size: int | None
    status: str
    created_at: datetime
    expires_at: datetime
    processing: ProcessingInfo | None = None


def to_view(doc: dict) -> FileView:
    return FileView(
        file_id=doc["_id"],
        filename=doc["filename"],
        content_type=doc["content_type"],
        size=doc.get("size"),
        status=doc["status"],
        created_at=doc["created_at"],
        expires_at=doc["expires_at"],
        processing=ProcessingInfo.model_validate(doc["processing"]) if doc.get("processing") else None,
    )
