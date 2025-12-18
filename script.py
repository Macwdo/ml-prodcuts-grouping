import time
from os import getenv

import boto3
import httpx
from dotenv import load_dotenv

load_dotenv()

SQS_CLIENT_KWARGS = {
    "aws_access_key_id": getenv("LOCALSTACK_AWS_ACCESS_KEY_ID"),
    "aws_secret_access_key": getenv("LOCALSTACK_AWS_SECRET_ACCESS_KEY"),
    "region_name": getenv("LOCALSTACK_AWS_REGION"),
    "endpoint_url": getenv("LOCALSTACK_AWS_ENDPOINT_URL"),
}
SQS_QUEUE_NAME = getenv("SQS_QUEUE_NAME")


HEALTH_URL = f"{getenv('LOCALSTACK_AWS_ENDPOINT_URL')}/_localstack/health"
VALID_STATUSES = ["available", "running"]


def check_localstack_availability(timeout=30):
    print("🔍 Checking LocalStack availability...")

    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            print("❌ Timed out waiting for LocalStack to be ready.")
            raise TimeoutError("LocalStack was not ready in time.")

        try:
            response = httpx.get(HEALTH_URL, timeout=3.0)
            response.raise_for_status()
            data = response.json()

            services = data.get("services", {})
            sqs_status = services.get("sqs")

            print(f"🔁 Service statuses → SQS: {sqs_status}")

            if sqs_status in VALID_STATUSES:
                print("✅ LocalStack services are ready!")
                return

        except Exception as e:
            print(f"⏳ Waiting for LocalStack: {e.__class__.__name__} - {e}")

        time.sleep(1)


def create_queue():
    sqs_client = boto3.client("sqs", **SQS_CLIENT_KWARGS)
    response = sqs_client.create_queue(QueueName=SQS_QUEUE_NAME)
    print(f"Queue created: {response['QueueUrl']}")


def check_if_queue_exists():
    sqs_client = boto3.client("sqs", **SQS_CLIENT_KWARGS)
    response = sqs_client.get_queue_url(QueueName=SQS_QUEUE_NAME)
    return response["QueueUrl"] is not None


if __name__ == "__main__":
    check_localstack_availability()
    create_queue()
