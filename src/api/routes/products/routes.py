from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_db_session
from src.api.routes.products.schemas import ImportProductsFromCsvRequest, ImportProductsFromCsvResponse, ProductProcessingResponse
from src.db.models.base import ProcessingStatus
from src.db.models.file import File
from src.db.models.product import ProductProcessing

router = APIRouter()


@router.post("/import-from-csv", response_model=ImportProductsFromCsvResponse)
async def import_products_from_csv(
    request: ImportProductsFromCsvRequest,
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    from src.tasks import import_products_from_csv_task

    file = await db_session.get(File, request.file_id)
    if not file:
        raise Response(status_code=404, detail="File not found")

    product_processing = ProductProcessing(status=ProcessingStatus.PENDING)
    db_session.add(product_processing)

    await db_session.flush()
    await db_session.refresh(product_processing)

    await db_session.commit()

    import_products_from_csv_task.delay(
        product_processing_id=product_processing.id,
        file_id=file.id,
        vendor_id=request.vendor_id,
    )

    return ImportProductsFromCsvResponse(
        status=product_processing.status,
        product_processing_id=product_processing.id,
    )


@router.get("/processing/{product_processing_id}", response_model=ProductProcessingResponse)
async def get_product_processing(
    product_processing_id: int,
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    product_processing = await db_session.get(ProductProcessing, product_processing_id)
    if not product_processing:
        return Response(status_code=status.HTTP_404_NOT_FOUND, content="Product processing not found")

    return ProductProcessingResponse(status=product_processing.status, product_processing_id=product_processing.id)
