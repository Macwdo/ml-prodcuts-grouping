import logging
from contextlib import asynccontextmanager

from pydantic import PostgresDsn
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.engine import AsyncEngine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_engine(
    *,
    postgres_uri: PostgresDsn,
    pool_pre_ping: bool = True,
    pool_size: int = 10,
    pool_timeout: int = 30,
    pool_recycle: int = 1800,
) -> AsyncEngine:
    engine = create_async_engine(
        url=str(postgres_uri),
        pool_pre_ping=pool_pre_ping,
        pool_size=pool_size,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
    )
    try:
        logger.info("Engine Created")
        yield engine

    finally:
        await engine.dispose()
        logger.info("Engine Disposed")


@asynccontextmanager
async def get_session(*, engine: AsyncEngine, expire_on_commit: bool = False):
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=expire_on_commit,
    )
    async with session_factory() as session:
        try:
            logger.debug("Session Opened")
            yield session

        finally:
            logger.debug("Session Closed")
