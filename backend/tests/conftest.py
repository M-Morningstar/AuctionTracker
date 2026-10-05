from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.db import async_session_factory
from app.models import Base

TEST_DATABASE_URL = "postgresql+asyncpg://auction:auction@localhost:5433/auction_test"

@pytest.fixture(scope="session", autouse=True)
async def _prepare_test_database() -> AsyncGenerator[None, None]:
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async_session_factory.configure(bind=engine)
    yield
    await engine.dispose()