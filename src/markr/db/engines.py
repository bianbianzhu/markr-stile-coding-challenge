from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from markr.config import Settings


def build_write_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.WRITE_POOL_SIZE,
        max_overflow=settings.WRITE_POOL_OVERFLOW,
        pool_pre_ping=True,
    )


def build_read_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.READ_POOL_SIZE,
        max_overflow=settings.READ_POOL_OVERFLOW,
        pool_pre_ping=True,
    )
