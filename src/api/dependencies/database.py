from fastapi import Request

from src.db.database import get_session


async def get_db_session(*, request: Request):
    engine = request.app.state.engine
    async with get_session(engine=engine) as session:
        yield session
