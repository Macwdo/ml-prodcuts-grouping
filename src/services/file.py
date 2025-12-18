import logging
import tempfile
from pathlib import Path

import boto3
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.models import File
from src.services import aws, http

logger = logging.getLogger(__name__)


async def download_file(
    *,
    file_id: int,
    s3_client: boto3.client,
    db_session: AsyncSession,
) -> Path:
    file = await db_session.get(File, file_id)
    if not file:
        raise FileNotFoundError(f"File with ID {file_id} not found")

    logger.info(f"Downloading file for ID: {file_id}")
    path = await _download_file_to_disk(
        file=file,
        s3_client=s3_client,
    )

    logger.info(f"File downloaded for ID: {file_id}")
    return Path(path)


async def _download_file_to_disk(
    *,
    file: File,
    s3_client: boto3.client,
) -> Path:
    """Download file from S3 and stream directly to disk."""
    url = aws.generate_get_presigned_url(
        bucket_name=settings.MINIO_AWS_BUCKET_NAME,
        key=file.key,
        s3_client=s3_client,
    )

    http_client = http.aget_http_client()

    with tempfile.NamedTemporaryFile(suffix=f".{file.extension}", delete=False) as temp_file:
        async with http_client.stream("GET", url) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                temp_file.write(chunk)

        temp_file.flush()
        temp_path = Path(temp_file.name)

    return temp_path
