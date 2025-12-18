from dotenv import load_dotenv
from pydantic import PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    POSTGRES_URI: PostgresDsn

    # AWS - LocalStack
    LOCALSTACK_AWS_ACCESS_KEY_ID: str
    LOCALSTACK_AWS_SECRET_ACCESS_KEY: str
    LOCALSTACK_AWS_REGION: str
    LOCALSTACK_AWS_ENDPOINT_URL: str

    # AWS S3 - Minio
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_ENDPOINT_URL: str
    MINIO_AWS_BUCKET_NAME: str
    MINIO_AWS_REGION: str

    # Celery
    SQS_QUEUE_NAME: str
    SQS_QUEUE_URL: str
    CELERY_BROKER_URL: str

    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    AI_MODEL: str = "gpt-4o-mini"

    model_config = {
        "env_file": ".env",
        "extra": "forbid",
    }


load_dotenv()
settings = Settings()
