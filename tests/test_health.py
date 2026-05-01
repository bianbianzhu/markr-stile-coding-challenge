import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from markr.api.exception_handlers import register_exception_handlers
from markr.api.ops import build_ops_router


@pytest.mark.asyncio
async def test_health_ok() -> None:
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
        engine = create_async_engine(pg.get_connection_url())
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(build_ops_router(engine))

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://t"
        ) as c:
            r = await c.get("/health")

        assert r.status_code == 200
        assert r.json() == {"status": "ok"}
        await engine.dispose()


@pytest.mark.asyncio
async def test_health_db_down_503() -> None:
    engine = create_async_engine("postgresql+asyncpg://nope:nope@127.0.0.1:1/none")
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(build_ops_router(engine))

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/health")

    assert r.status_code == 503
    assert r.json()["error"] == "service_unavailable"
    assert r.json()["details"] == {"status": "degraded"}
    await engine.dispose()
