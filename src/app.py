import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from src.api.routes.files.routes import router as files_router
from src.api.routes.groups.routes import router as groups_router
from src.api.routes.health import router as health_router
from src.api.routes.products.routes import router as products_router
from src.api.routes.vendor.routes import router as vendor_router
from src.config import settings
from src.db.database import get_engine
from src.logging import configure_logging

configure_logging()

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application")

    async with get_engine(postgres_uri=settings.POSTGRES_URI) as engine:
        app.state.engine = engine
        yield

    logger.info("Shutting down application")


app = FastAPI(lifespan=lifespan)

app.include_router(router=health_router, prefix="/health", tags=["Health"])
app.include_router(router=files_router, prefix="/files", tags=["Files"])
app.include_router(router=groups_router, prefix="/groups", tags=["Groups"])
app.include_router(router=vendor_router, prefix="/vendors", tags=["Vendors"])
app.include_router(router=products_router, prefix="/products", tags=["Products"])
