from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from api.config import settings
from api.database import get_async_session
from api.internal.main import app
from api.internal.orm_models.dao import Base

TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.TEST_POSTGRES_DB}"
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)

_TRUNCATE_SQL = text("TRUNCATE task_status_history, tasks, project_members, projects, users RESTART IDENTITY CASCADE")


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    admin_url = (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/postgres"
    )
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        exists = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": settings.TEST_POSTGRES_DB},
        )
        if not exists.fetchone():
            await conn.execute(text(f'CREATE DATABASE "{settings.TEST_POSTGRES_DB}"'))
    await admin_engine.dispose()

    async with test_engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_database):
    session = AsyncSession(test_engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        async with AsyncSession(test_engine) as cleanup:
            await cleanup.execute(_TRUNCATE_SQL)
            await cleanup.commit()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
