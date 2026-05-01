from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from importlib.resources import files

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def db_url() -> Iterator[str]:
    env_url = os.getenv("TEST_DATABASE_URL")
    if env_url:
        yield env_url
        return

    os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
        yield pg.get_connection_url()


@pytest_asyncio.fixture()
async def engine(db_url: str) -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(db_url)
    schema_sql = (files("markr.db") / "schema.sql").read_text(encoding="utf-8")
    async with eng.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS test_results"))
        await conn.execute(text(schema_sql))
    yield eng
    await eng.dispose()
