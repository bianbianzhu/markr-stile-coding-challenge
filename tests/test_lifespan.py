import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from markr.config import Settings
from markr.main import create_app


@pytest.mark.asyncio
async def test_lifespan_creates_table(monkeypatch: pytest.MonkeyPatch) -> None:
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        monkeypatch.setenv("DATABASE_URL", url)
        app = create_app(Settings())

        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://t"
            ) as c:
                r = await c.get("/health")

        assert r.status_code == 200

        verify = create_async_engine(url)
        async with verify.connect() as conn:
            res = await conn.execute(text("SELECT to_regclass('test_results')"))
            assert res.scalar() == "test_results"
        await verify.dispose()
