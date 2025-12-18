import uuid
from datetime import UTC, datetime
from pathlib import Path

import boto3
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select

from src.api.dependencies.aws import get_aws_s3_client
from src.api.dependencies.database import get_db_session
from src.api.routes.files.schemas import (
    CompleteUploadResponse,
    FileResponse,
    StartUploadRequest,
    StartUploadResponse,
)
from src.config import settings
from src.db.models import File
from src.services import aws

router = APIRouter()


@router.post("/start-upload", response_model=StartUploadResponse)
async def start_upload(
    request: StartUploadRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    s3_client: boto3.client = Depends(get_aws_s3_client),  # noqa: B008
):
    file_uuid = uuid.uuid4()
    file_path = Path(request.file_name)
    extension = file_path.suffix.lstrip(".")  # Remove leading dot
    key = f"{file_uuid.hex[:8]}.{extension}"

    async with session.begin():
        file = File(file_name=request.file_name, extension=extension, key=key)
        session.add(file)

        url = aws.generate_put_presigned_url(bucket_name=settings.MINIO_AWS_BUCKET_NAME, key=key, s3_client=s3_client)
        await session.commit()

    await session.refresh(file)
    return StartUploadResponse(url=url, file_id=file.id, key=file.key)


@router.post("/complete-upload/{file_id}", response_model=CompleteUploadResponse)
async def complete_upload(
    file_id: int,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    file = await session.get(File, file_id)
    if not file:
        return Response(status_code=status.HTTP_404_NOT_FOUND, content="File not found")

    if file.uploaded_at is not None:
        return Response(status_code=status.HTTP_400_BAD_REQUEST, content="File already uploaded")

    file.uploaded_at = datetime.now(UTC)
    await session.commit()

    return CompleteUploadResponse(message="Upload completed successfully")


@router.get("/", response_model=list[FileResponse])
async def list_files(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    """List all files."""
    statement = select(File)
    result = await session.scalars(statement)
    files = result.all()

    return [FileResponse.model_validate(file) for file in files]


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: int,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    """Get a file by ID."""
    file = await session.get(File, file_id)
    if not file:
        return Response(status_code=status.HTTP_404_NOT_FOUND, content="File not found")

    return FileResponse.model_validate(file)
