import asyncio
import logging

import boto3
from celery import shared_task

from src.config import settings
from src.db import database as db
from src.services.aws import get_s3_client_kwargs
from src.vendor.ai import llm as llm_ai
from src.vendor.services import group as group_service
from src.vendor.services import product as product_service

logger = logging.getLogger(__name__)


@shared_task
def group_vendor_products_task(vendor_id: int, group_processing_id: int):
    async def run():
        async with db.get_engine(postgres_uri=settings.POSTGRES_URI) as engine:
            await group_service.group_vendor_products(vendor_id=vendor_id, group_processing_id=group_processing_id, engine=engine)

    asyncio.run(run())


@shared_task
def import_products_from_csv_task(
    product_processing_id: int,
    file_id: int,
    vendor_id: int,
):
    async def run():
        s3_client = boto3.client("s3", **get_s3_client_kwargs())
        embedding_client = llm_ai.get_embedding_client()
        llm_client = llm_ai.get_llm_client()

        async with db.get_engine(postgres_uri=settings.POSTGRES_URI) as engine:
            await product_service.import_products_from_csv(
                product_processing_id=product_processing_id,
                file_id=file_id,
                vendor_id=vendor_id,
                engine=engine,
                s3_client=s3_client,
                embedding_client=embedding_client,
                llm_client=llm_client,
            )

    asyncio.run(run())
