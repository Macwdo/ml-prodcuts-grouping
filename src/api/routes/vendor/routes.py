from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_db_session
from src.db.models.vendor import Vendor

router = APIRouter()


class VendorResponse(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True,
    }


class VendorRequest(BaseModel):
    name: str


@router.post("/", response_model=VendorResponse)
async def create_vendor(
    request: VendorRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    vendor = Vendor(name=request.name)

    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    return VendorResponse.model_validate(vendor)


@router.get("/", response_model=list[VendorResponse])
async def get_vendors(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    vendors = await session.scalars(select(Vendor))
    return [VendorResponse.model_validate(vendor) for vendor in vendors]


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: int,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    vendor = await session.get(Vendor, vendor_id)
    if vendor is None:
        raise Response(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    return VendorResponse.model_validate(vendor)
