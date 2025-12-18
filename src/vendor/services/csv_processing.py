from __future__ import annotations

import csv
import logging
from pathlib import Path

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from src.app import BASE_DIR
from src.services import csv as csv_service
from src.vendor.ai import utils as ai_utils

logger = logging.getLogger(__name__)


class StructureCsvHeaderResponseSchema(BaseModel):
    """Schema for mapping CSV headers to standardized field names."""

    name: str | None = None
    description: str | None = None
    price: str | None = None
    brand: str | None = None
    category: str | None = None
    sku: str | None = None


async def get_products_from_csv(
    *,
    csv_path: Path,
    llm_client: ChatOpenAI,
) -> list[StructureCsvHeaderResponseSchema]:
    headers = csv_service.get_header(path=csv_path)

    sanitized_headers = _sanitize_header(headers)
    sample_rows = _get_sample_rows(path=csv_path, num_rows=3)

    # Get header mapping from LLM
    logger.info(f"Getting header mapping from LLM for ID: {csv_path}")
    structured_header = await structure_csv_header_response_schema(
        headers=sanitized_headers,
        sample_rows=sample_rows,
        llm_client=llm_client,
    )
    structured_header_dict = structured_header.model_dump()

    # Map CSV rows to standardized schema
    csv_dict = csv_service.to_dict(path=csv_path)
    mapped_dict = []
    for row in csv_dict:
        mapped_row = {}
        for key, value in structured_header_dict.items():
            if value and value in row:
                mapped_row[key] = row[value]
            else:
                mapped_row[key] = None

        mapped_dict.append(mapped_row)

    return [StructureCsvHeaderResponseSchema(**mapped_row) for mapped_row in mapped_dict]


def _sanitize_header(headers: list[str]) -> list[str]:
    sanitized_headers = []
    for header in headers:
        header = header.strip()
        header = header.split(" ")
        header = [word.lower() for word in header]
        header = " ".join(header)

        sanitized_headers.append(header)

    return sanitized_headers


def _get_sample_rows(*, path: Path, num_rows: int = 3) -> list[str]:
    rows = []
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for i, row in enumerate(reader):
            if i >= num_rows:
                break
            rows.append(",".join(row))

    return rows


async def structure_csv_header_response_schema(
    *,
    headers: list[str],
    sample_rows: list[str],
    llm_client: ChatOpenAI,
) -> StructureCsvHeaderResponseSchema:
    prompt_template = _get_prompt_template()

    # Format the prompt with actual CSV data
    header_str = ",".join(headers)
    rows_str = "\n".join(sample_rows) if sample_rows else "(no sample rows available)"

    # Replace placeholders with actual data
    formatted_prompt = prompt_template.format(header=header_str, rows=rows_str)

    # Use structured output with ChatOpenAI
    structured_llm = llm_client.with_structured_output(StructureCsvHeaderResponseSchema)
    response = await structured_llm.ainvoke(formatted_prompt)
    return response


def _get_prompt_template() -> str:
    return ai_utils.read_prompt(path=Path(BASE_DIR, "vendor", "ai", "prompt.txt"))
