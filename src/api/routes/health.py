from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_db_session

router = APIRouter()


@router.get("/")
def health_check():
    return {"status": "ok"}


@router.get("/db")
async def health_check_db(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    async with session as s:
        await s.execute(text("SELECT 1"))

    return {"status": "ok"}
