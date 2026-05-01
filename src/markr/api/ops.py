from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from markr.api.errors import MarkrHTTPException


def build_ops_router(read_engine: AsyncEngine) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health() -> dict[str, str]:
        try:
            async with read_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as exc:
            raise MarkrHTTPException(
                status_code=503,
                error="service_unavailable",
                message="database unreachable",
                details={"status": "degraded"},
            ) from exc

        return {"status": "ok"}

    return router
