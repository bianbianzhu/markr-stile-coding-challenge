from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.resources import files

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from markr.api.body_cap import BodyCapMiddleware
from markr.api.exception_handlers import register_exception_handlers
from markr.api.ops import build_ops_router
from markr.config import Settings
from markr.db.engines import build_read_engine, build_write_engine

SCHEMA_LOCK_KEY = 0x4D41524B


def _read_schema_sql() -> str:
    return (files("markr.db") / "schema.sql").read_text(encoding="utf-8")


async def _wait_for_db(engine: AsyncEngine, max_wait_s: float = 30.0) -> None:
    delay = 0.5
    waited = 0.0
    while True:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return
        except Exception:
            if waited >= max_wait_s:
                raise
            await asyncio.sleep(delay)
            waited += delay
            delay = min(delay * 2, 5.0)


async def _bootstrap_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SCHEMA_LOCK_KEY})
        await conn.execute(text(_read_schema_sql()))


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()  # type: ignore[call-arg]
    logging.basicConfig(level=os.getenv("LOG_LEVEL", settings.LOG_LEVEL).upper())

    write_engine = build_write_engine(settings)
    read_engine = build_read_engine(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            await _wait_for_db(write_engine)
            await _bootstrap_schema(write_engine)
            yield
        finally:
            await write_engine.dispose()
            await read_engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(BodyCapMiddleware)
    register_exception_handlers(app)
    app.include_router(build_ops_router(read_engine))
    app.state.write_engine = write_engine
    app.state.read_engine = read_engine
    return app
