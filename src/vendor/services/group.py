from __future__ import annotations

import logging

from sqlalchemy import Engine, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.database import get_session
from src.db.models.base import ProcessingStatus
from src.db.models.group import GroupProcessing, GroupProduct
from src.db.models.product import Group, Product
from src.vendor.services import cluster as cluster_service
from src.vendor.services import group as group_service
from src.vendor.services import product as product_service

logger = logging.getLogger(__name__)


async def group_vendor_products(
    *,
    vendor_id: int,
    group_processing_id: int,
    engine: Engine,
):
    async with get_session(engine=engine) as session, session.begin():
        try:
            group_processing = await session.get(GroupProcessing, group_processing_id)
            if group_processing is None:
                logger.error(f"Group processing not found for ID: {group_processing_id}")
                return

            group_processing.status = ProcessingStatus.PROCESSING

            products = await product_service.get_all_products_from_vendor(vendor_id=vendor_id, db_session=session)
            clusters, meta = cluster_service.cluster_products(products=products)

            logger.info("Cluster Finished")
            logger.info(f"Clusters Noise Ratio: {meta.noise_ratio}")

            for cluster in clusters:
                logger.info(f"Creating group for cluster ID: {cluster.cluster_id}")
                group = await group_service.create_group(
                    group_processing_id=group_processing_id,
                    vendor_id=vendor_id,
                    db_session=session,
                )

                logger.info(f"Updating all products in cluster ID: {cluster.cluster_id} to group ID: {group.id}")
                statement = (
                    update(Product).where(Product.id.in_([item.product.id for item in cluster.items])).values(group_id=group.id)
                )

                for p in cluster.items:
                    group_product = GroupProduct(group_id=group.id, product_id=p.product.id)
                    session.add(group_product)

                await session.execute(statement)

            logger.info(f"Updating group processing status to completed for ID: {group_processing_id}")
            group_processing.status = ProcessingStatus.COMPLETED

        except Exception as e:
            logger.error(f"Error processing group for ID: {group_processing_id}", exc_info=e)
            group_processing.status = ProcessingStatus.FAILED
            raise e


async def create_group(
    *,
    group_processing_id: int,
    vendor_id: int,
    db_session: AsyncSession,
) -> Group:
    group = Group(group_processing_id=group_processing_id, vendor_id=vendor_id)
    db_session.add(group)

    await db_session.flush()
    await db_session.refresh(group)

    return group


async def get_groups(
    group_processing_id: int,
    *,
    db_session: AsyncSession,
):
    statement = (
        select(Group)
        .where(Group.group_processing_id == group_processing_id)
        .options(
            selectinload(Group.group_products).selectinload(GroupProduct.product).selectinload(Product.brand),
            selectinload(Group.group_products).selectinload(GroupProduct.product).selectinload(Product.category),
        )
    )

    groups = (await db_session.scalars(statement)).all()
    return groups
