from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_db_session
from src.api.routes.groups.schemas import (
    GroupCheckStatusResponse,
    GroupedProductsItemResponse,
    GroupedProductsResponse,
    GroupProductStartRequest,
    GroupProductStartResponse,
    ProductResponse,
)
from src.db.models.base import ProcessingStatus
from src.db.models.group import GroupProcessing
from src.vendor.services import group as group_service

router = APIRouter()


@router.post("/group", response_model=GroupProductStartResponse)
async def group_vendor_products(
    request: GroupProductStartRequest,
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    from src.tasks import group_vendor_products_task

    group_processing = GroupProcessing(status=ProcessingStatus.PENDING)

    db_session.add(group_processing)
    await db_session.flush()
    await db_session.refresh(group_processing)

    await db_session.commit()

    group_vendor_products_task.delay(vendor_id=request.vendor_id, group_processing_id=group_processing.id)
    return GroupProductStartResponse(group_processing_id=group_processing.id, status=group_processing.status)


@router.get("/processing/{group_processing_id}", response_model=GroupCheckStatusResponse)
async def get_group_processing(
    group_processing_id: int,
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    group_processing = await db_session.get(GroupProcessing, group_processing_id)
    if not group_processing:
        raise Response(status_code=status.HTTP_404_NOT_FOUND, detail="Group processing not found")

    return GroupCheckStatusResponse(status=group_processing.status)


@router.get("/", response_model=GroupedProductsResponse)
async def get_groups(
    group_processing_id: int,
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    groups = await group_service.get_groups(group_processing_id=group_processing_id, db_session=db_session)
    count = len(groups)

    return GroupedProductsResponse(
        count=count,
        group_processing_id=group_processing_id,
        items=[
            GroupedProductsItemResponse(
                group_id=group.id,
                products=[
                    ProductResponse(
                        id=p.product.id,
                        sku=p.product.sku,
                        name=p.product.name,
                        price=p.product.price,
                        description=p.product.description,
                        brand=p.product.brand.name if p.product.brand else None,
                        category=p.product.category.name if p.product.category else None,
                    )
                    for p in group.group_products
                ],
            )
            for group in groups
        ],
    )
