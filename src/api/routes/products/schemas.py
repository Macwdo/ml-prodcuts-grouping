from pydantic import BaseModel

from src.db.models.base import ProcessingStatus


class ImportProductsFromCsvRequest(BaseModel):
    vendor_id: int
    file_id: int


class ImportProductsFromCsvResponse(BaseModel):
    status: ProcessingStatus
    product_processing_id: int


class ProductProcessingResponse(BaseModel):
    status: ProcessingStatus
    product_processing_id: int
