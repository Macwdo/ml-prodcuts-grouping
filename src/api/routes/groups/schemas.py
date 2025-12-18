from __future__ import annotations

from pydantic import BaseModel

from src.db.models.base import ProcessingStatus


class GroupProductStartRequest(BaseModel):
    file_id: int
    vendor_id: int


class GroupProductStartResponse(BaseModel):
    group_processing_id: int
    status: ProcessingStatus


class GroupCheckStatusResponse(BaseModel):
    status: ProcessingStatus


class ProductResponse(BaseModel):
    id: int
    name: str
    price: float
    description: str | None
    brand: str | None
    category: str | None
    sku: str

    model_config = {
        "from_attributes": True,
    }


class GroupedProductsItemResponse(BaseModel):
    group_id: int
    products: list[ProductResponse]


class GroupedProductsResponse(BaseModel):
    count: int
    group_processing_id: int
    items: list[GroupedProductsItemResponse]
