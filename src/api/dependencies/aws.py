import boto3

from src.services.aws import get_s3_client_kwargs, get_sqs_client_kwargs


def get_aws_s3_client():
    return boto3.client("s3", **get_s3_client_kwargs())


def get_aws_sqs_client():
    return boto3.client("sqs", **get_sqs_client_kwargs())
