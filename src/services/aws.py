import mimetypes

import boto3

from src.config import settings


def get_s3_client_kwargs() -> dict:
    return {
        "aws_access_key_id": settings.MINIO_ACCESS_KEY,
        "aws_secret_access_key": settings.MINIO_SECRET_KEY,
        "region_name": settings.MINIO_AWS_REGION,
        "endpoint_url": settings.MINIO_ENDPOINT_URL,
    }


def get_sqs_client_kwargs() -> dict:
    return {
        "aws_access_key_id": settings.LOCALSTACK_AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.LOCALSTACK_AWS_SECRET_ACCESS_KEY,
        "region_name": settings.LOCALSTACK_AWS_REGION,
        "endpoint_url": settings.LOCALSTACK_AWS_ENDPOINT_URL,
    }


def generate_get_presigned_url(
    *,
    bucket_name: str,
    key: str,
    s3_client: boto3.client,
    expires_in: int = 3600,
) -> str:
    return s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": bucket_name,
            "Key": key,
        },
        ExpiresIn=expires_in,
    )


def generate_put_presigned_url(
    *,
    bucket_name: str,
    key: str,
    s3_client: boto3.client,
    expires_in: int = 3600,
) -> str:
    content_type = mimetypes.guess_type(key)[0]
    if content_type is None:
        content_type = "application/octet-stream"

    return s3_client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": bucket_name,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
    )
