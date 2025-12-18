from __future__ import annotations

import logging

import boto3
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import selectinload

from src.db import database as db
from src.db.models.base import ProcessingStatus
from src.db.models.file import File
from src.db.models.product import Product, ProductBrand, ProductCategory, ProductProcessing
from src.services import file as file_service
from src.vendor.services import csv_processing as csv_processing_service
from src.vendor.services.csv_processing import StructureCsvHeaderResponseSchema

logger = logging.getLogger(__name__)


async def import_products_from_csv(
    *,
    product_processing_id: int,
    file_id: int,
    vendor_id: int,
    engine: AsyncEngine,
    s3_client: boto3.client,
    embedding_client: OpenAIEmbeddings,
    llm_client: ChatOpenAI,
):

    async with db.get_session(engine=engine) as db_session, db_session.begin():
        product_processing = await db_session.get(ProductProcessing, product_processing_id)
        if product_processing is None:
            logger.error(f"Product processing not found for ID: {product_processing_id}")
            return

        product_processing.status = ProcessingStatus.PROCESSING

        file = await db_session.get(File, file_id)
        if file is None:
            logger.error(f"File not found for ID: {file_id}")
            return

        csv_path = await file_service.download_file(file_id=file.id, s3_client=s3_client, db_session=db_session)
        products_in_csv = await csv_processing_service.get_products_from_csv(csv_path=csv_path, llm_client=llm_client)

        products_to_be_created = await _get_products_to_be_created(products_in_csv=products_in_csv, db_session=db_session)

        products_created = []
        for product_data in products_to_be_created:
            product = await create_product(
                sku=product_data.sku,
                name=product_data.name,
                price=product_data.price,
                description=product_data.description,
                brand=product_data.brand,
                category=product_data.category,
                vendor_id=vendor_id,
                db_session=db_session,
                embedding_client=embedding_client,
            )
            logger.info(f"Product created - {product}")
            products_created.append(product)

        product_processing.status = ProcessingStatus.COMPLETED

    return products_created


async def _get_products_to_be_created(
    *,
    products_in_csv: list[StructureCsvHeaderResponseSchema],
    db_session: AsyncSession,
) -> list[StructureCsvHeaderResponseSchema]:
    """
    Get products to be created from CSV.
    If the product is already in the database, it will not be created.
    """

    skus_in_csv = [product.sku for product in products_in_csv]
    products_query = await db_session.execute(select(Product).where(Product.sku.in_(skus_in_csv)))
    products = products_query.scalars().all()

    products_in_db_dict = {product.sku: product for product in products}
    products_in_csv_dict = {product.sku: product for product in products_in_csv}

    products_to_be_grouped: list[StructureCsvHeaderResponseSchema] = []
    for sku, product in products_in_csv_dict.items():
        if sku not in products_in_db_dict:
            products_to_be_grouped.append(product)

    return products_to_be_grouped


async def create_product(
    *,
    sku: str,
    name: str,
    price: float,
    description: str | None = None,
    brand: str | None = None,
    category: str | None = None,
    vendor_id: int,
    db_session: AsyncSession,
    embedding_client: OpenAIEmbeddings,
) -> Product:
    brand_query = await db_session.execute(select(ProductBrand).where(ProductBrand.name == brand))
    product_brand = brand_query.scalar_one_or_none()

    if product_brand is None and brand is not None:
        normalized_brand = _normalize_name(name=brand)
        product_brand = ProductBrand(name=brand, normalized_name=normalized_brand)
        db_session.add(product_brand)

        await db_session.flush()
        await db_session.refresh(product_brand)

    category_query = await db_session.execute(select(ProductCategory).where(ProductCategory.name == category))
    product_category = category_query.scalar_one_or_none()
    if product_category is None and category is not None:
        normalized_category = _normalize_name(name=category)
        product_category = ProductCategory(name=category, normalized_name=normalized_category)
        db_session.add(product_category)

        await db_session.flush()
        await db_session.refresh(product_category)

    product = Product(
        sku=sku,
        name=name,
        description=description,
        price=float(price),
        brand_id=product_brand.id if product_brand is not None else None,
        category_id=product_category.id if product_category is not None else None,
        vendor_id=vendor_id,
    )
    db_session.add(product)

    embedding = await _generate_embedding(product=product, embedding_client=embedding_client)
    product.embedding = embedding

    await db_session.flush()
    await db_session.refresh(product)

    return product


def _normalize_name(*, name: str) -> str:
    return name.lower().replace(" ", "_")


async def _generate_embedding(*, product: Product, embedding_client: OpenAIEmbeddings) -> Product:
    text = f"Product: {product.name}"
    if product.description is not None:
        text += f"\nDescription: {product.description}"

    embedding = await embedding_client.aembed_query(text=text)
    return embedding


async def get_all_products_from_vendor(*, vendor_id: int, db_session: AsyncSession):
    products_query = await db_session.execute(
        select(Product)
        .where(Product.vendor_id == vendor_id)
        .options(
            selectinload(Product.brand),
            selectinload(Product.category),
        )
    )
    products = products_query.scalars().all()
    return products
