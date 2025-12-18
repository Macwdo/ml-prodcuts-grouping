from datetime import datetime

from pydantic import BaseModel


class FileResponse(BaseModel):
    """Schema for file responses (GET endpoints)."""

    id: int
    key: str
    uploaded_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class StartUploadRequest(BaseModel):
    file_name: str


class StartUploadResponse(BaseModel):
    url: str
    file_id: int
    key: str


class GetPresignedUrlResponse(BaseModel):
    url: str
    file_id: int
    key: str


class CompleteUploadResponse(BaseModel):
    message: str
